import asyncio
import json
import logging
import re
import time
from threading import Thread
from typing import Any, AsyncGenerator, Callable, List, Optional

import torch
from transformers import AutoModelForCausalLM, AutoTokenizer, StoppingCriteria, StoppingCriteriaList, TextIteratorStreamer

from app.models.schemas import SourceChunk

logger = logging.getLogger(__name__)

LOCAL_LLM_MODEL_NAME = "Qwen/Qwen2.5-0.5B-Instruct"

VAGUE_PATTERNS = [
    r"^\s*what is this\??\s*$",
    r"^\s*summarize\s*$",
    r"^\s*explain\s*$",
    r"^\s*tell me more\s*$",
    r"^\s*i still don['’]?t understand\.?\s*$",
    r"^\s*i don['’]?t understand( this material)?\.?\s*$",
    r"^\s*i do not understand( this material)?\.?\s*$",
    r"^\s*what does this mean\??\s*$",
]

_llm_model = None
_llm_tokenizer = None


def load_models():
    global _llm_model, _llm_tokenizer
    if _llm_model is None:
        logger.info("Loading Qwen weights into RAM...")
        _llm_tokenizer = AutoTokenizer.from_pretrained(LOCAL_LLM_MODEL_NAME)
        _llm_model = AutoModelForCausalLM.from_pretrained(
            LOCAL_LLM_MODEL_NAME,
            device_map="cpu",
            torch_dtype=torch.float32,
        )
    return _llm_model, _llm_tokenizer


def get_ai_response(prompt: str, max_tokens: int = 128) -> str:
    model, tokenizer = load_models()
    inputs = tokenizer(prompt, return_tensors="pt", truncation=True, max_length=1024)
    inputs = {k: v.to(model.device) for k, v in inputs.items()}
    outputs = model.generate(
        **inputs,
        max_new_tokens=max_tokens,
        do_sample=False,
        temperature=0.0,
        pad_token_id=tokenizer.eos_token_id,
    )
    input_len = inputs["input_ids"].shape[1]
    generated_tokens = outputs[0][input_len:]
    return tokenizer.decode(generated_tokens, skip_special_tokens=True).strip()


def _normalize_space(text: str) -> str:
    return re.sub(r"\s+", " ", (text or "")).strip()


def detect_vague_query(question: str) -> bool:
    cleaned = _normalize_space(question).lower()
    if len(cleaned.split()) <= 3:
        return True
    return any(re.match(pattern, cleaned) for pattern in VAGUE_PATTERNS)


def classify_intent(question: str, conversation_summary: str) -> str:
    lowered = _normalize_space(question).lower()
    if re.fullmatch(
        r"(ok|okay|thanks|thank you|thx|ok thanks|okay thanks|got it|understood|cool|nice|no|nope|nah|no thanks|no thank you|nah thanks|that's all|thats all)[!. ]*",
        lowered,
    ):
        return "acknowledgement"
    if re.fullmatch(r"(wtf|what the fuck|fuck|fuck off|fuckoff|ffs|bullshit|bs|ugh|damn)[!. ]*", lowered):
        return "acknowledgement"
    if re.search(r"\b(useless|stupid|idiot|dumb|terrible|awful|sucks)\b", lowered):
        return "acknowledgement"
    if detect_vague_query(question):
        if conversation_summary.strip():
            return "follow_up_question"
        return "vague_query"
    if conversation_summary.strip() and re.search(
        r"\b(each|them|those|that|this|it|these|more|examples?|simpler|clarify|elaborate|why|how)\b",
        lowered,
    ):
        return "follow_up_question"
    if any(token in lowered for token in ["summarize", "summary", "overview"]):
        if any(token in lowered for token in ["section", "part", "chapter", "page", "passage"]):
            return "summarize_section"
        return "summarize_document"
    if any(token in lowered for token in ["compare", "difference", "versus", "vs"]):
        return "compare_documents"
    if any(token in lowered for token in ["method", "methodology", "approach", "experiment", "procedure"]):
        return "methodology_question"
    if any(token in lowered for token in ["result", "finding", "conclusion", "outcome"]):
        return "results_question"
    if re.search(r"\bdefine\b|\bwhat is\b|\bmeaning of\b", lowered):
        return "define_term"
    if re.search(r"\bi don['’]?t understand\b|\bi do not understand\b|\bconfusing\b|\bstill\b|\bagain\b", lowered) and conversation_summary.strip():
        return "follow_up_question"
    return "find_specific_information"


def rewrite_query(question: str, conversation_summary: str, doc_titles: List[str], intent: str = "") -> str:
    if not question.strip():
        return ""

    cleaned_question = _normalize_space(question)
    title_context = ", ".join(doc_titles[:3]).strip()
    summary_context = _normalize_space(conversation_summary)[:260]

    if intent == "summarize_document":
        if title_context:
            return f"Summarize the main topic, purpose, and key findings of the uploaded document titled {title_context}."
        if summary_context:
            return f"Summarize the uploaded document using this context: {summary_context}"
        return "Summarize the uploaded document, including its main topic, purpose, and key findings."

    if intent == "summarize_section":
        if title_context:
            return f"{cleaned_question} in the uploaded document titled {title_context}."
        return cleaned_question

    if intent in {"follow_up_question", "vague_query"}:
        if cleaned_question.lower() in {"what is this", "summarize", "explain"}:
            if summary_context:
                return f"Explain the main topic and purpose of the uploaded document using this context: {summary_context}"
            if title_context:
                return f"Explain the main topic and purpose of the uploaded document titled {title_context}."
        if re.search(r"\bexamples?\b", cleaned_question.lower()):
            if summary_context:
                return f"Give concrete examples for the concepts being discussed in this document context: {summary_context}"
            if title_context:
                return f"Give concrete examples for the main concepts in the uploaded document titled {title_context}."
        if re.search(r"i still don['’]?t understand|i don['’]?t understand|i do not understand", cleaned_question.lower()):
            if summary_context:
                return f"Explain the material in simpler terms and clarify the user's confusion using this context: {summary_context}"
            if title_context:
                return f"Explain the uploaded document titled {title_context} in simple terms for a confused reader."
            return "Explain the previously discussed material in simpler terms."
        if summary_context:
            return f"{cleaned_question}. Use this prior document context: {summary_context}"
        if title_context:
            return f"{cleaned_question} about the uploaded document titled {title_context}."

    return cleaned_question


def update_conversation_summary(old_summary: str, recent_messages: List[dict], latest_response: str) -> str:
    bits: List[str] = []
    if old_summary:
        bits.append(_normalize_space(old_summary))
    for message in recent_messages[-4:]:
        role = message.get("role", "")
        content = _normalize_space(message.get("content", ""))
        if not content:
            continue
        prefix = "User asked" if role == "user" else "Assistant explained"
        bits.append(f"{prefix}: {content[:180]}")
    if latest_response:
        bits.append(f"Latest answer: {_normalize_space(latest_response)[:220]}")
    return " ".join(bits)[:600].strip()


def generate_document_summary(doc_text: str, title: str = "") -> str:
    cleaned = _normalize_space(doc_text)
    if not cleaned:
        return ""
    sentences = re.split(r"(?<=[.!?])\s+", cleaned)
    extractive = " ".join(sentences[:4]).strip()
    if len(extractive) >= 120:
        return extractive[:700]
    prompt = f"""<|im_start|>system
Create a concise, human-readable document summary in 3 to 5 sentences.
Focus on the main topic, the purpose of the document, and the most important themes or findings.
Document title: {title or "Unknown"}
Document excerpt:
{cleaned[:4000]}
<|im_end|>
<|im_start|>assistant
"""
    return _normalize_space(get_ai_response(prompt, max_tokens=220))


def build_acknowledgement_response(question: str) -> str:
    lowered = _normalize_space(question).lower()
    if re.fullmatch(r"(wtf|what the fuck|fuck|fuck off|fuckoff|ffs|bullshit|bs|ugh|damn)[!. ]*", lowered):
        return "I’m here to help. Ask me to explain the topic again, more simply, or give examples."
    if re.fullmatch(r"(no|nope|nah)[!. ]*", lowered):
        return "Alright. If you change your mind, I can explain it more simply or give examples."
    if re.search(r"\b(useless|stupid|idiot|dumb|terrible|awful|sucks)\b", lowered):
        return "I can still help. Ask me to re-explain the topic, give examples, or summarize the section you need."
    if "thank" in lowered or "thx" in lowered:
        return "You're welcome. If you want, ask me to explain it more simply or summarize a specific section."
    if any(token in lowered for token in ["got it", "understood"]):
        return "Glad that helped. If you want to go deeper, ask about any term, section, or result in the document."
    return "Of course. If you want, I can explain a section more simply or pull out the key points."


def _build_qwen_prompt(
    question: str,
    chunks: List[SourceChunk],
    conversation_summary: str = "",
    intent: str = "",
    fallback_summary: str = "",
) -> str:
    context_text = "\n\n".join(
        [f"[Source {i + 1}] (page {c.page}, score {c.score:.3f})\n{c.text_snippet}" for i, c in enumerate(chunks)]
    )
    return (
        f"<|im_start|>system\n"
        "You are DocuMind AI, a professional research assistant.\n"
        "Base the answer on the retrieved document context first.\n"
        "Do not invent facts, dates, names, measurements, studies, or details that are not in the retrieved context.\n"
        "If the user is confused, explain the material in simpler language.\n"
        "If context is limited, use the document summary fallback and clearly stay high level.\n"
        "Never say there is no information if relevant context or conversation summary was provided.\n"
        "Use short paragraphs and clear language.\n"
        "Cite supported factual claims with [Source X].\n"
        f"Conversation Summary: {conversation_summary or 'None'}\n"
        f"Detected Intent: {intent or 'unknown'}\n"
        f"Document Summary Fallback: {fallback_summary or 'None'}\n"
        f"<|im_end|>\n"
        f"<|im_start|>user\n"
        f"Retrieved Context:\n{context_text or 'No retrieved excerpts available.'}\n\n"
        f"User Request: {question}\n"
        f"<|im_end|>\n"
        f"<|im_start|>assistant\n"
    )


async def stream_rag_response(
    question: str,
    chunks: List[SourceChunk],
    conversation_summary: str = "",
    intent: str = "",
    fallback_summary: str = "",
    should_stop: Optional[Callable[[], bool]] = None,
    on_progress: Optional[Callable[[str], None]] = None,
    on_complete: Optional[Callable[[str], None]] = None,
    on_stopped: Optional[Callable[[str], None]] = None,
    on_error: Optional[Callable[[str], None]] = None,
) -> AsyncGenerator[str, None]:
    model, tokenizer = load_models()
    prompt = _build_qwen_prompt(question, chunks, conversation_summary, intent, fallback_summary)
    streamer = TextIteratorStreamer(tokenizer, skip_prompt=True, skip_special_tokens=True)
    inputs = tokenizer(prompt, return_tensors="pt", truncation=True, max_length=1400)

    class _StopGenerationCriteria(StoppingCriteria):
        def __call__(self, input_ids, scores, **kwargs):  # type: ignore[override]
            return bool(should_stop and should_stop())

    stopping_criteria = StoppingCriteriaList([_StopGenerationCriteria()]) if should_stop else None

    generation_kwargs = dict(
        **inputs,
        streamer=streamer,
        max_new_tokens=320,
        do_sample=True,
        temperature=0.25,
        top_p=0.9,
        repetition_penalty=1.1,
        pad_token_id=tokenizer.eos_token_id,
        stopping_criteria=stopping_criteria,
    )

    generation_thread = Thread(target=model.generate, kwargs=generation_kwargs, daemon=True)
    generation_thread.start()

    queue: asyncio.Queue[Optional[Any]] = asyncio.Queue()
    loop = asyncio.get_running_loop()
    persisted_final = False

    def _run_callback(callback: Optional[Callable[[str], None]], text: str) -> None:
        if not callback or not text:
            return
        try:
            callback(text)
        except Exception:
            logger.exception("Streaming callback failed")

    def _consume_stream() -> None:
        nonlocal persisted_final
        collected_parts: List[str] = []
        last_progress_flush = 0.0
        try:
            for new_text in streamer:
                collected_parts.append(new_text)
                now = time.monotonic()
                current_text = _normalize_space("".join(collected_parts))
                if current_text and on_progress and (now - last_progress_flush >= 0.6):
                    _run_callback(on_progress, current_text)
                    last_progress_flush = now
                loop.call_soon_threadsafe(queue.put_nowait, new_text)

            final_text = _normalize_space("".join(collected_parts))
            if should_stop and should_stop():
                if on_stopped:
                    try:
                        on_stopped(final_text)
                    except Exception:
                        logger.exception("Streaming stop callback failed")
                elif final_text:
                    _run_callback(on_complete, final_text)
                persisted_final = True
            elif final_text:
                _run_callback(on_complete, final_text)
                persisted_final = True
            loop.call_soon_threadsafe(queue.put_nowait, None)
        except Exception as exc:
            logger.exception("Streaming consumer crashed")
            partial_text = _normalize_space("".join(collected_parts))
            if partial_text:
                _run_callback(on_complete, partial_text)
                persisted_final = True
            else:
                _run_callback(on_error, "Communication with AI failed. Please try again.")
            loop.call_soon_threadsafe(queue.put_nowait, exc)

    consumer_thread = Thread(target=_consume_stream, daemon=True)
    consumer_thread.start()

    try:
        yield f"data: {json.dumps({'type': 'sources', 'chunks': [c.model_dump() for c in chunks]})}\n\n"
        await asyncio.sleep(0)

        while True:
            try:
                item = await asyncio.wait_for(queue.get(), timeout=1.0)
            except asyncio.TimeoutError:
                if should_stop and should_stop() and not generation_thread.is_alive() and queue.empty():
                    break
                if generation_thread.is_alive():
                    yield ": keep-alive\n\n"
                    await asyncio.sleep(0)
                    continue
                if queue.empty():
                    break
                continue

            if item is None:
                break

            if isinstance(item, Exception):
                logger.error("Streaming error from consumer thread", exc_info=item)
                yield f"data: {json.dumps({'type': 'error', 'content': 'Inference failed.'})}\n\n"
                break

            if item:
                yield f"data: {json.dumps({'type': 'message', 'content': item})}\n\n"
                await asyncio.sleep(0)

        yield "data: [DONE]\n\n"
    except Exception as exc:
        logger.error(f"Streaming error: {exc}")
        if not persisted_final:
            _run_callback(on_error, "Communication with AI failed. Please try again.")
        yield f"data: {json.dumps({'type': 'error', 'content': 'Inference failed.'})}\n\n"
