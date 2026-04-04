import json
import logging
from typing import Dict, List

from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import StreamingResponse

from app import db
from app.auth import RequestUserContext, require_request_user_context, verify_csrf_request
from app.config import settings
from app.models.schemas import ConversationStateResponse, QueryRequest, SourceChunk
from app.services.rate_limit import rate_limiter
from app.services.ai_utils import (
    build_acknowledgement_response,
    classify_intent,
    rewrite_query,
    stream_rag_response,
    update_conversation_summary,
)
from app.services.generation_control import begin_generation, build_generation_key, finish_generation, request_stop
from app.services.rag_utils import (
    build_document_summary_fallback,
    get_document_titles,
    hybrid_search,
    is_low_confidence,
    rerank_chunks,
)

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/query", tags=["query"])


def _build_conversation_id(request: QueryRequest, user_id: str | None = None) -> str:
    if request.notebook_id:
        return request.notebook_id
    inferred = db.get_notebook_for_document_ids(request.file_ids, user_id=user_id)
    if inferred:
        return inferred
    return ""


def _last_assistant_message(messages: List[Dict[str, str]]) -> str:
    for message in reversed(messages):
        if message.get("role") == "assistant" and message.get("content"):
            return message["content"]
    return ""


def _build_readiness_message(documents: List[Dict[str, str]]) -> str:
    if not documents:
        return "This notebook does not have any uploaded documents yet. Upload a PDF first, then I can answer questions grounded in it."

    indexed_docs = [doc for doc in documents if doc.get("processing_status") == "indexed"]
    if indexed_docs:
        return ""

    pending_docs = [doc for doc in documents if doc.get("processing_status") in {"uploaded", "processing"}]
    failed_docs = [doc for doc in documents if doc.get("processing_status") == "failed"]

    if pending_docs:
        titles = ", ".join((doc.get("display_title") or doc.get("original_filename") or "document") for doc in pending_docs[:2])
        suffix = " are" if len(pending_docs) > 1 else " is"
        return f"{titles}{suffix} still being processed. I'll be able to answer once indexing finishes."

    if failed_docs:
        first_error = failed_docs[0].get("processing_error")
        base = "I can't answer from this notebook yet because document indexing failed."
        if first_error:
            return f"{base} Latest error: {first_error}"
        return base

    return "This notebook is not ready for querying yet."


@router.get("/history/{notebook_id}", response_model=ConversationStateResponse)
async def get_conversation_history(
    notebook_id: str,
    user: RequestUserContext = Depends(require_request_user_context),
):
    if not db.notebook_exists(notebook_id, user_id=user.user_id):
        raise HTTPException(status_code=404, detail="Notebook not found.")
    conversation = db.get_conversation(notebook_id, user_id=user.user_id)
    return ConversationStateResponse(
        notebook_id=notebook_id,
        summary=conversation.get("summary", ""),
        messages=conversation.get("messages", []),
    )


@router.post("/stop/{notebook_id}")
async def stop_notebook_generation(
    notebook_id: str,
    user: RequestUserContext = Depends(require_request_user_context),
    _: None = Depends(verify_csrf_request),
):
    if not db.notebook_exists(notebook_id, user_id=user.user_id):
        raise HTTPException(status_code=404, detail="Notebook not found.")

    generation_key = build_generation_key(user_id=user.user_id, notebook_id=notebook_id)
    stopped = request_stop(generation_key)
    return {"stopped": stopped}


@router.post("")
async def query_documents(
    http_request: Request,
    request: QueryRequest,
    user: RequestUserContext = Depends(require_request_user_context),
    _: None = Depends(verify_csrf_request),
):
    if not request.question.strip():
        raise HTTPException(status_code=400, detail="Question cannot be empty.")
    if len(request.question) > settings.max_question_length:
        raise HTTPException(status_code=400, detail="Question is too long.")

    client_ip = http_request.client.host if http_request.client else "unknown"
    rate_limiter.hit(
        f"query:{user.user_id}:{client_ip}",
        settings.query_rate_limit_attempts,
        settings.query_rate_limit_window_seconds,
    )

    notebook_id = _build_conversation_id(request, user_id=user.user_id)
    if not notebook_id:
        raise HTTPException(status_code=400, detail="A valid notebook_id is required.")
    if not db.notebook_exists(notebook_id, user_id=user.user_id):
        raise HTTPException(status_code=404, detail="Notebook not found.")
    if request.file_ids and not db.validate_notebook_documents(notebook_id, request.file_ids):
        raise HTTPException(status_code=400, detail="One or more documents do not belong to the notebook.")

    document_scope = db.get_document_records(request.file_ids, notebook_id=notebook_id) if request.file_ids else db.list_documents_for_notebook(notebook_id)
    readiness_message = _build_readiness_message(document_scope)

    top_k = max(request.top_k, 10)
    conversation_id = notebook_id
    generation_key = build_generation_key(user_id=user.user_id, notebook_id=conversation_id)
    conversation = db.get_conversation(conversation_id, user_id=user.user_id)
    conversation_messages: List[Dict[str, str]] = conversation.get("messages", [])
    conversation_summary = conversation.get("summary", "")

    intent = classify_intent(request.question, conversation_summary)
    pending_messages = conversation_messages + [{"role": "user", "content": request.question}]

    if intent == "acknowledgement":
        response_text = build_acknowledgement_response(request.question)
        db.save_conversation(
            conversation_id,
            pending_messages + [{"role": "assistant", "content": response_text}],
            conversation_summary,
            user_id=user.user_id,
        )

        async def acknowledgement_stream():
            yield 'data: {"type": "sources", "chunks": []}\n\n'
            yield f"data: {json.dumps({'type': 'message', 'content': response_text})}\n\n"
            yield "data: [DONE]\n\n"

        return StreamingResponse(acknowledgement_stream(), media_type="text/event-stream")

    if readiness_message:
        db.save_conversation(
            conversation_id,
            pending_messages + [{"role": "assistant", "content": readiness_message}],
            conversation_summary,
            user_id=user.user_id,
        )

        async def readiness_stream():
            yield 'data: {"type": "sources", "chunks": []}\n\n'
            yield f"data: {json.dumps({'type': 'status', 'status': 'not_ready', 'content': readiness_message})}\n\n"
            yield f"data: {json.dumps({'type': 'message', 'content': readiness_message})}\n\n"
            yield "data: [DONE]\n\n"

        return StreamingResponse(readiness_stream(), media_type="text/event-stream")

    doc_titles = get_document_titles(request.file_ids, notebook_id=notebook_id)
    rewritten_query = rewrite_query(request.question, conversation_summary, doc_titles, intent=intent)

    try:
        primary_results = hybrid_search(rewritten_query, notebook_id=notebook_id, file_ids=request.file_ids or None, top_k=top_k)
        alternate_results = []
        if rewritten_query.strip() != request.question.strip():
            alternate_results = hybrid_search(
                request.question,
                notebook_id=notebook_id,
                file_ids=request.file_ids or None,
                top_k=max(6, top_k // 2),
            )

        combined_map = {}
        for chunk in primary_results + alternate_results:
            key = (chunk.file_id, chunk.page, chunk.text_snippet)
            previous = combined_map.get(key)
            if previous is None or chunk.score > previous.score:
                combined_map[key] = chunk

        reranked_results = rerank_chunks(rewritten_query, list(combined_map.values()), top_k=top_k)
    except Exception as exc:
        logger.error(f"Search error: {exc}", exc_info=True)
        raise HTTPException(status_code=500, detail="Search failed.")

    fallback_summary = build_document_summary_fallback(request.file_ids, notebook_id=notebook_id)

    if intent == "follow_up_question":
        previous_answer = _last_assistant_message(conversation_messages)
        if previous_answer:
            reranked_results = [
                SourceChunk(
                    file_id=request.file_ids[0] if request.file_ids else "conversation",
                    page=0,
                    text_snippet=previous_answer,
                    score=1.0,
                )
            ] + reranked_results[:9]

    if is_low_confidence(reranked_results) and fallback_summary:
        reranked_results = []

    if not reranked_results and not fallback_summary:
        fallback_summary = "I could not match a precise passage yet, but the uploaded documents are still available. Try asking for the main topic, a section, or a definition from the document."

    def _persist_assistant_reply(final_answer: str, *, streaming: bool = False):
        assistant_message = {
            "role": "assistant",
            "content": final_answer,
            "retrieval_metadata": {"status": "streaming" if streaming else "complete"},
        }
        updated_messages = pending_messages + [assistant_message]
        next_summary = conversation_summary
        should_refresh_summary = (
            not streaming
            and (
                len(updated_messages) <= 4
                or len(updated_messages) % 4 == 0
                or intent == "follow_up_question"
            )
        )
        if should_refresh_summary:
            try:
                next_summary = update_conversation_summary(conversation_summary, updated_messages, final_answer)
            except Exception as exc:
                logger.warning(f"Summary update failed for {conversation_id}: {exc}")
        db.save_conversation(conversation_id, updated_messages, next_summary, user_id=user.user_id)

    def _persist_streaming_progress(partial_answer: str):
        _persist_assistant_reply(partial_answer, streaming=True)

    def _persist_stopped_reply(partial_answer: str):
        if partial_answer.strip():
            db.save_conversation(
                conversation_id,
                pending_messages + [{"role": "assistant", "content": partial_answer, "retrieval_metadata": {"status": "complete", "finish_reason": "stopped"}}],
                conversation_summary,
                user_id=user.user_id,
            )
            return

        db.save_conversation(conversation_id, pending_messages, conversation_summary, user_id=user.user_id)

    def _persist_streaming_error(error_message: str):
        db.save_conversation(
            conversation_id,
            pending_messages + [{"role": "assistant", "content": error_message, "retrieval_metadata": {"status": "complete"}}],
            conversation_summary,
            user_id=user.user_id,
        )

    def _handle_stream_complete(final_answer: str):
        try:
            _persist_assistant_reply(final_answer, streaming=False)
        finally:
            finish_generation(generation_key, stop_event)

    def _handle_stream_stopped(partial_answer: str):
        try:
            _persist_stopped_reply(partial_answer)
        finally:
            finish_generation(generation_key, stop_event)

    def _handle_stream_error(error_message: str):
        try:
            _persist_streaming_error(error_message)
        finally:
            finish_generation(generation_key, stop_event)

    db.save_conversation(
        conversation_id,
        pending_messages + [{"role": "assistant", "content": "", "retrieval_metadata": {"status": "streaming"}}],
        conversation_summary,
        user_id=user.user_id,
    )

    stop_event = begin_generation(generation_key)

    try:
        return StreamingResponse(
            stream_rag_response(
                request.question,
                reranked_results[:10],
                conversation_summary=conversation_summary,
                intent=intent,
                fallback_summary=fallback_summary,
                should_stop=stop_event.is_set,
                on_progress=_persist_streaming_progress,
                on_complete=_handle_stream_complete,
                on_stopped=_handle_stream_stopped,
                on_error=_handle_stream_error,
            ),
            media_type="text/event-stream",
            headers={
                "X-Accel-Buffering": "no",
                "X-Conversation-Id": conversation_id,
                "X-Intent": intent,
            },
        )
    except Exception as exc:
        logger.error(f"Inference error: {exc}", exc_info=True)
        finish_generation(generation_key, stop_event)

        async def error_stream():
            yield 'data: {"type": "error", "content": "Communication with AI failed. Please try again."}\n\n'
            yield "data: [DONE]\n\n"

        return StreamingResponse(error_stream(), media_type="text/event-stream")
    finally:
        if stop_event.is_set():
            finish_generation(generation_key, stop_event)
