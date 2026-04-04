import logging
import os
import uuid
from datetime import datetime, timezone
from typing import Any, Dict, Iterable, List, Optional

from sqlalchemy import Select, delete, func, select
from sqlalchemy.orm import joinedload

from app.database import SessionLocal, init_database
from app.models.db_models import (
    ChatMessage,
    Conversation,
    Document,
    DocumentChunk,
    DocumentProcessingStatus,
    EmbeddingStatus,
    IndexingJob,
    IndexingJobStatus,
    Note,
    NotebookLifecycleStatus,
    Notebook,
)

logger = logging.getLogger(__name__)


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


def init_db() -> None:
    init_database()


def _document_to_dict(document: Document) -> Dict[str, Any]:
    latest_job = None
    if getattr(document, "indexing_jobs", None):
        sorted_jobs = sorted(
            document.indexing_jobs,
            key=lambda job: job.created_at or datetime.min.replace(tzinfo=timezone.utc),
            reverse=True,
        )
        if sorted_jobs:
            latest_job = _indexing_job_to_dict(sorted_jobs[0])
    return {
        "id": document.id,
        "notebook_id": document.notebook_id,
        "original_filename": document.original_filename,
        "display_title": document.display_title,
        "storage_path": document.storage_path,
        "mime_type": document.mime_type,
        "file_size": document.file_size,
        "page_count": document.page_count or 0,
        "processing_status": document.processing_status.value if hasattr(document.processing_status, "value") else str(document.processing_status),
        "processing_error": document.processing_error,
        "summary": document.summary or "",
        "created_at": document.created_at.isoformat() if document.created_at else "",
        "updated_at": document.updated_at.isoformat() if document.updated_at else "",
        "latest_indexing_job": latest_job,
    }


def _notebook_to_dict(notebook: Notebook) -> Dict[str, Any]:
    documents = sorted(notebook.documents, key=lambda doc: doc.created_at or datetime.min.replace(tzinfo=timezone.utc), reverse=True)
    indexed_count = sum(1 for doc in documents if doc.processing_status == DocumentProcessingStatus.indexed)
    pending_count = sum(1 for doc in documents if doc.processing_status in {DocumentProcessingStatus.uploaded, DocumentProcessingStatus.processing})
    failed_count = sum(1 for doc in documents if doc.processing_status == DocumentProcessingStatus.failed)
    return {
        "id": notebook.id,
        "title": notebook.title,
        "icon_key": notebook.icon_key,
        "user_id": notebook.user_id,
        "share_id": notebook.share_id,
        "lifecycle_status": notebook.lifecycle_status.value if hasattr(notebook.lifecycle_status, "value") else str(notebook.lifecycle_status),
        "deletion_error": notebook.deletion_error,
        "created_at": notebook.created_at.isoformat() if notebook.created_at else "",
        "updated_at": notebook.updated_at.isoformat() if notebook.updated_at else "",
        "source_count": len(documents),
        "indexed_document_count": indexed_count,
        "pending_document_count": pending_count,
        "failed_document_count": failed_count,
        "ready_for_query": indexed_count > 0,
        "file_ids": [doc.id for doc in documents],
        "filenames": [doc.original_filename for doc in documents],
        "documents": [_document_to_dict(doc) for doc in documents],
    }


def _indexing_job_to_dict(job: IndexingJob) -> Dict[str, Any]:
    return {
        "id": job.id,
        "notebook_id": job.notebook_id,
        "document_id": job.document_id,
        "status": job.status.value if hasattr(job.status, "value") else str(job.status),
        "error_message": job.error_message,
        "queued_at": job.created_at.isoformat() if job.created_at else "",
        "started_at": job.started_at.isoformat() if job.started_at else None,
        "finished_at": job.finished_at.isoformat() if job.finished_at else None,
        "created_at": job.created_at.isoformat() if job.created_at else "",
        "updated_at": job.updated_at.isoformat() if job.updated_at else "",
    }


def _conversation_to_dict(conversation: Conversation) -> Dict[str, Any]:
    messages = sorted(
        conversation.messages,
        key=lambda item: (
            getattr(item, "message_index", 0),
            item.created_at or datetime.min.replace(tzinfo=timezone.utc),
        ),
    )
    return {
        "id": conversation.id,
        "notebook_id": conversation.notebook_id,
        "summary": conversation.rolling_summary or "",
        "messages": [
            {
                "id": message.id,
                "role": message.role,
                "content": message.content,
                "retrieval_metadata": message.retrieval_metadata or {},
            }
            for message in messages
        ],
    }


def _note_to_dict(note: Note) -> Dict[str, Any]:
    return {
        "id": note.id,
        "notebook_id": note.notebook_id,
        "content": note.content,
        "source_message_id": note.source_message_id,
        "created_at": note.created_at.isoformat() if note.created_at else "",
        "updated_at": note.updated_at.isoformat() if note.updated_at else "",
    }


def _apply_notebook_visibility(query: Select[tuple[Notebook]], include_hidden: bool) -> Select[tuple[Notebook]]:
    if include_hidden:
        return query
    return query.where(Notebook.lifecycle_status == NotebookLifecycleStatus.active)


def _apply_notebook_owner_scope(
    query: Select[tuple[Notebook]],
    user_id: Optional[str],
    *,
    include_unowned: bool = True,
) -> Select[tuple[Notebook]]:
    """
    Pre-auth ownership boundary.

    Current behavior:
    - authenticated/future-owned requests can scope to a specific user_id
    - unauthenticated requests can only see legacy/unowned notebooks

    TODO(auth): Once real auth is enabled, make user_id mandatory for protected routes and
    remove broad unauthenticated access to newly owned notebooks.
    """
    if user_id:
        if include_unowned:
            return query.where((Notebook.user_id == user_id) | (Notebook.user_id.is_(None)))
        return query.where(Notebook.user_id == user_id)
    return query.where(Notebook.user_id.is_(None))


def list_notebooks(user_id: Optional[str] = None, *, include_hidden: bool = False) -> List[Dict[str, Any]]:
    with SessionLocal() as session:
        query: Select[tuple[Notebook]] = (
            select(Notebook)
            .options(joinedload(Notebook.documents).joinedload(Document.indexing_jobs))
            .order_by(Notebook.updated_at.desc(), Notebook.created_at.desc())
        )
        query = _apply_notebook_visibility(query, include_hidden)
        query = _apply_notebook_owner_scope(query, user_id)
        notebooks = session.execute(query).unique().scalars().all()
        return [_notebook_to_dict(notebook) for notebook in notebooks]


def create_notebook(title: str, user_id: Optional[str] = None, icon_key: str = "folder") -> Dict[str, Any]:
    with SessionLocal() as session:
        notebook = Notebook(title=title.strip(), user_id=user_id, icon_key=icon_key or "folder")
        session.add(notebook)
        session.flush()
        session.add(Conversation(notebook_id=notebook.id, user_id=user_id, title=title.strip() or "Notebook chat", rolling_summary=""))
        session.commit()
        notebook = session.execute(
            select(Notebook).options(joinedload(Notebook.documents).joinedload(Document.indexing_jobs)).where(Notebook.id == notebook.id)
        ).unique().scalar_one()
        return _notebook_to_dict(notebook)


def get_notebook(notebook_id: str, user_id: Optional[str] = None, *, include_hidden: bool = False) -> Optional[Dict[str, Any]]:
    with SessionLocal() as session:
        query = select(Notebook).options(joinedload(Notebook.documents).joinedload(Document.indexing_jobs)).where(Notebook.id == notebook_id)
        query = _apply_notebook_visibility(query, include_hidden)
        query = _apply_notebook_owner_scope(query, user_id)
        notebook = session.execute(query).unique().scalar_one_or_none()
        return _notebook_to_dict(notebook) if notebook else None


def ensure_notebook_share_id(notebook_id: str, user_id: Optional[str] = None) -> Optional[str]:
    with SessionLocal() as session:
        query = select(Notebook).where(Notebook.id == notebook_id)
        query = _apply_notebook_visibility(query, include_hidden=False)
        query = _apply_notebook_owner_scope(query, user_id, include_unowned=False)
        notebook = session.execute(query).scalar_one_or_none()
        if not notebook:
            return None
        if not notebook.share_id:
            notebook.share_id = str(uuid.uuid4())
            session.commit()
            session.refresh(notebook)
        return notebook.share_id


def get_shared_notebook_by_share_id(share_id: str) -> Optional[Dict[str, Any]]:
    with SessionLocal() as session:
        notebook = session.execute(
            select(Notebook)
            .options(joinedload(Notebook.documents))
            .where(Notebook.share_id == share_id, Notebook.lifecycle_status == NotebookLifecycleStatus.active)
        ).unique().scalar_one_or_none()
        if not notebook:
            return None

        documents = sorted(
            notebook.documents,
            key=lambda doc: doc.created_at or datetime.min.replace(tzinfo=timezone.utc),
            reverse=True,
        )
        indexed_documents = [doc for doc in documents if doc.processing_status == DocumentProcessingStatus.indexed]
        return {
            "title": notebook.title,
            "source_count": len(documents),
            "indexed_document_count": len(indexed_documents),
            "created_at": notebook.created_at.isoformat() if notebook.created_at else "",
            "updated_at": notebook.updated_at.isoformat() if notebook.updated_at else "",
            "documents": [
                {
                    "display_title": document.display_title,
                    "page_count": document.page_count or 0,
                    "summary": document.summary or "",
                    "processing_status": document.processing_status.value if hasattr(document.processing_status, "value") else str(document.processing_status),
                }
                for document in documents
            ],
        }


def update_notebook(notebook_id: str, *, title: Optional[str] = None, icon_key: Optional[str] = None, user_id: Optional[str] = None) -> Optional[Dict[str, Any]]:
    with SessionLocal() as session:
        query = select(Notebook).options(joinedload(Notebook.documents).joinedload(Document.indexing_jobs)).where(Notebook.id == notebook_id)
        query = _apply_notebook_visibility(query, include_hidden=False)
        query = _apply_notebook_owner_scope(query, user_id, include_unowned=False)
        notebook = session.execute(query).unique().scalar_one_or_none()
        if not notebook:
            return None
        if title is not None:
            notebook.title = title.strip()
        first_conversation = session.execute(
            select(Conversation).where(Conversation.notebook_id == notebook_id).order_by(Conversation.created_at.asc())
        ).scalars().first()
        if first_conversation and title is not None and title.strip():
            first_conversation.title = title.strip()
        if icon_key is not None:
            notebook.icon_key = icon_key or "folder"
        session.commit()
        session.refresh(notebook)
        return _notebook_to_dict(notebook)


def notebook_exists(notebook_id: str, user_id: Optional[str] = None, *, include_hidden: bool = False) -> bool:
    return get_notebook(notebook_id, user_id=user_id, include_hidden=include_hidden) is not None


def get_notebook_lifecycle_status(notebook_id: str) -> Optional[str]:
    with SessionLocal() as session:
        notebook = session.execute(select(Notebook.lifecycle_status).where(Notebook.id == notebook_id)).scalar_one_or_none()
        if notebook is None:
            return None
        return notebook.value if hasattr(notebook, "value") else str(notebook)


def prepare_notebook_deletion(notebook_id: str, user_id: Optional[str] = None) -> Dict[str, Any]:
    with SessionLocal() as session:
        query = select(Notebook).options(joinedload(Notebook.documents).joinedload(Document.indexing_jobs)).where(Notebook.id == notebook_id)
        query = _apply_notebook_owner_scope(query, user_id, include_unowned=False)
        notebook = session.execute(query).unique().scalar_one_or_none()
        if not notebook:
            return {"deleted": False, "storage_paths": [], "lifecycle_status": None}

        storage_paths = [doc.storage_path for doc in notebook.documents if doc.storage_path]
        notebook.lifecycle_status = NotebookLifecycleStatus.deleting
        notebook.deletion_error = None
        for document in notebook.documents:
            document.processing_status = DocumentProcessingStatus.deleting
        session.commit()
        return {
            "deleted": False,
            "ready_for_cleanup": True,
            "notebook_id": notebook.id,
            "storage_paths": storage_paths,
            "lifecycle_status": notebook.lifecycle_status.value,
        }


def finalize_notebook_deletion(notebook_id: str, user_id: Optional[str] = None) -> Dict[str, Any]:
    with SessionLocal() as session:
        query = select(Notebook).options(joinedload(Notebook.documents)).where(Notebook.id == notebook_id)
        query = _apply_notebook_owner_scope(query, user_id, include_unowned=False)
        notebook = session.execute(query).unique().scalar_one_or_none()
        if not notebook:
            return {"deleted": False, "already_deleted": True}

        session.delete(notebook)
        session.commit()
        return {"deleted": True}


def record_notebook_delete_failure(notebook_id: str, error_message: str, user_id: Optional[str] = None) -> bool:
    with SessionLocal() as session:
        query = select(Notebook).where(Notebook.id == notebook_id)
        query = _apply_notebook_owner_scope(query, user_id, include_unowned=False)
        notebook = session.execute(query).scalar_one_or_none()
        if not notebook:
            return False
        notebook.lifecycle_status = NotebookLifecycleStatus.delete_failed
        notebook.deletion_error = error_message
        session.commit()
        return True


def create_document(
    notebook_id: str,
    original_filename: str,
    display_title: str,
    storage_path: str,
    mime_type: str,
    file_size: int,
    page_count: int = 0,
) -> Dict[str, Any]:
    with SessionLocal() as session:
        document = Document(
            notebook_id=notebook_id,
            original_filename=original_filename,
            display_title=display_title,
            storage_path=storage_path,
            mime_type=mime_type,
            file_size=file_size,
            page_count=page_count,
            processing_status=DocumentProcessingStatus.uploaded,
        )
        session.add(document)
        session.commit()
        session.refresh(document)
        result = _document_to_dict(document)
    return result


def get_document(file_id: str) -> Optional[Dict[str, Any]]:
    with SessionLocal() as session:
        document = session.execute(
            select(Document).options(joinedload(Document.indexing_jobs)).where(Document.id == file_id)
        ).unique().scalar_one_or_none()
        return _document_to_dict(document) if document else None


def delete_document(file_id: str) -> bool:
    with SessionLocal() as session:
        document = session.get(Document, file_id)
        if not document:
            return False
        session.delete(document)
        session.commit()
    return True


def update_document_processing_status(
    file_id: str,
    status: DocumentProcessingStatus,
    *,
    processing_error: Optional[str] = None,
    page_count: Optional[int] = None,
    summary: Optional[str] = None,
    display_title: Optional[str] = None,
) -> Optional[Dict[str, Any]]:
    with SessionLocal() as session:
        document = session.get(Document, file_id)
        if not document:
            return None
        if document.processing_status == DocumentProcessingStatus.deleting and status != DocumentProcessingStatus.deleting:
            session.refresh(document)
            return _document_to_dict(document)
        document.processing_status = status
        document.processing_error = processing_error
        if page_count is not None:
            document.page_count = page_count
        if summary is not None:
            document.summary = summary
        if display_title:
            document.display_title = display_title
        session.commit()
        session.refresh(document)
        return _document_to_dict(document)


def update_document_storage_path(file_id: str, storage_path: str) -> Optional[Dict[str, Any]]:
    with SessionLocal() as session:
        document = session.get(Document, file_id)
        if not document:
            return None
        if document.processing_status == DocumentProcessingStatus.deleting:
            session.refresh(document)
            return _document_to_dict(document)
        document.storage_path = storage_path
        session.commit()
        session.refresh(document)
        return _document_to_dict(document)


def create_indexing_job(notebook_id: str, document_id: str) -> Dict[str, Any]:
    with SessionLocal() as session:
        job = IndexingJob(notebook_id=notebook_id, document_id=document_id, status=IndexingJobStatus.queued)
        session.add(job)
        session.commit()
        session.refresh(job)
        return _indexing_job_to_dict(job)


def update_indexing_job(
    job_id: str,
    *,
    status: IndexingJobStatus,
    error_message: Optional[str] = None,
    started: bool = False,
    finished: bool = False,
) -> Optional[Dict[str, Any]]:
    with SessionLocal() as session:
        job = session.get(IndexingJob, job_id)
        if not job:
            return None
        job.status = status
        job.error_message = error_message
        if started:
            job.started_at = _utcnow()
        if finished:
            job.finished_at = _utcnow()
        session.commit()
        session.refresh(job)
        return _indexing_job_to_dict(job)


def get_document_records(file_ids: List[str], notebook_id: Optional[str] = None) -> List[Dict[str, Any]]:
    if not file_ids:
        return []
    with SessionLocal() as session:
        query = select(Document).options(joinedload(Document.indexing_jobs)).where(Document.id.in_(file_ids))
        if notebook_id:
            query = query.where(Document.notebook_id == notebook_id)
            query = query.join(Notebook, Document.notebook_id == Notebook.id).where(Notebook.lifecycle_status == NotebookLifecycleStatus.active)
        documents = session.execute(query).unique().scalars().all()
        return [_document_to_dict(document) for document in documents]


def get_document_record(file_id: str, notebook_id: Optional[str] = None) -> Optional[Dict[str, Any]]:
    records = get_document_records([file_id], notebook_id=notebook_id)
    return records[0] if records else None


def validate_notebook_documents(notebook_id: str, file_ids: List[str]) -> bool:
    if not file_ids:
        return True
    with SessionLocal() as session:
        count = session.scalar(
            select(func.count(Document.id)).where(Document.id.in_(file_ids), Document.notebook_id == notebook_id)
        )
        return int(count or 0) == len(set(file_ids))


def get_notebook_for_document_ids(file_ids: List[str], user_id: Optional[str] = None) -> Optional[str]:
    if not file_ids:
        return None
    with SessionLocal() as session:
        query = (
            select(Document.notebook_id)
            .join(Notebook, Document.notebook_id == Notebook.id)
            .where(Document.id.in_(file_ids), Notebook.lifecycle_status == NotebookLifecycleStatus.active)
            .distinct()
        )
        query = _apply_notebook_owner_scope(query, user_id)
        notebook_ids = session.execute(query).scalars().all()
        if len(notebook_ids) == 1:
            return notebook_ids[0]
        return None


def list_documents_for_notebook(notebook_id: str) -> List[Dict[str, Any]]:
    with SessionLocal() as session:
        documents = session.execute(
            select(Document)
            .options(joinedload(Document.indexing_jobs))
            .join(Notebook, Document.notebook_id == Notebook.id)
            .where(Document.notebook_id == notebook_id, Notebook.lifecycle_status == NotebookLifecycleStatus.active)
            .order_by(Document.created_at.desc())
        ).unique().scalars().all()
        return [_document_to_dict(doc) for doc in documents]


def replace_document_chunks(document_id: str, notebook_id: str, chunks: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    with SessionLocal() as session:
        session.execute(delete(DocumentChunk).where(DocumentChunk.document_id == document_id))
        created: List[DocumentChunk] = []
        for chunk in chunks:
            row = DocumentChunk(
                document_id=document_id,
                notebook_id=notebook_id,
                chunk_index=chunk["chunk_index"],
                content=chunk["content"],
                page_number=chunk.get("page_number"),
                token_count=chunk.get("token_count"),
                embedding_status=chunk.get("embedding_status", EmbeddingStatus.pending),
                embedding_model=chunk.get("embedding_model"),
                embedding_vector=chunk.get("embedding_vector"),
            )
            session.add(row)
            created.append(row)
        session.commit()
        for row in created:
            session.refresh(row)
        return [
            {
                "id": row.id,
                "document_id": row.document_id,
                "notebook_id": row.notebook_id,
                "chunk_index": row.chunk_index,
                "content": row.content,
                "page_number": row.page_number,
                "token_count": row.token_count,
                "embedding_status": row.embedding_status.value if hasattr(row.embedding_status, "value") else str(row.embedding_status),
                "embedding_model": row.embedding_model,
                "embedding_vector": row.embedding_vector,
            }
            for row in created
        ]


def list_chunks_with_embeddings() -> List[Dict[str, Any]]:
    with SessionLocal() as session:
        rows = session.execute(
            select(DocumentChunk)
            .join(Notebook, DocumentChunk.notebook_id == Notebook.id)
            .where(
                DocumentChunk.embedding_status == EmbeddingStatus.embedded,
                DocumentChunk.embedding_vector.is_not(None),
                Notebook.lifecycle_status == NotebookLifecycleStatus.active,
            )
        ).scalars().all()
        return [
            {
                "id": row.id,
                "document_id": row.document_id,
                "notebook_id": row.notebook_id,
                "chunk_index": row.chunk_index,
                "content": row.content,
                "page_number": row.page_number,
                "embedding_vector": row.embedding_vector,
            }
            for row in rows
        ]


def list_chunk_search_records(notebook_id: str, file_ids: Optional[List[str]] = None) -> List[Dict[str, Any]]:
    with SessionLocal() as session:
        query = (
            select(DocumentChunk)
            .join(Notebook, DocumentChunk.notebook_id == Notebook.id)
            .where(DocumentChunk.notebook_id == notebook_id, Notebook.lifecycle_status == NotebookLifecycleStatus.active)
        )
        if file_ids:
            query = query.where(DocumentChunk.document_id.in_(file_ids))
        rows = session.execute(query).scalars().all()
        return [
            {
                "id": row.id,
                "document_id": row.document_id,
                "notebook_id": row.notebook_id,
                "chunk_index": row.chunk_index,
                "content": row.content,
                "page_number": row.page_number,
                "token_count": row.token_count,
                "embedding_status": row.embedding_status.value if hasattr(row.embedding_status, "value") else str(row.embedding_status),
                "embedding_model": row.embedding_model,
                "embedding_vector": row.embedding_vector,
            }
            for row in rows
        ]


def get_conversation(notebook_id: str, user_id: Optional[str] = None) -> Dict[str, Any]:
    with SessionLocal() as session:
        query = (
            select(Conversation)
            .options(joinedload(Conversation.messages))
            .join(Notebook, Conversation.notebook_id == Notebook.id)
            .where(Conversation.notebook_id == notebook_id, Notebook.lifecycle_status == NotebookLifecycleStatus.active)
            .order_by(Conversation.created_at.asc())
        )
        query = _apply_notebook_owner_scope(query, user_id)
        conversation = session.execute(query).unique().scalars().first()
        if not conversation:
            return {"messages": [], "summary": ""}
        data = _conversation_to_dict(conversation)
        return {"messages": data["messages"], "summary": data["summary"], "conversation_id": data["id"]}


def save_conversation(notebook_id: str, messages: List[Dict], summary: str, user_id: Optional[str] = None):
    with SessionLocal() as session:
        query = select(Notebook).where(Notebook.id == notebook_id)
        query = _apply_notebook_owner_scope(query, user_id)
        notebook = session.execute(query).scalar_one_or_none()
        if not notebook:
            raise ValueError(f"Notebook {notebook_id} does not exist.")
        if notebook.lifecycle_status != NotebookLifecycleStatus.active:
            raise ValueError(f"Notebook {notebook_id} is not writable.")

        conversation = session.execute(
            select(Conversation).where(Conversation.notebook_id == notebook_id).order_by(Conversation.created_at.asc())
        ).scalars().first()
        if not conversation:
            conversation = Conversation(notebook_id=notebook_id, user_id=notebook.user_id, title=notebook.title, rolling_summary=summary or "")
            session.add(conversation)
            session.flush()

        conversation.rolling_summary = summary or ""
        session.execute(delete(ChatMessage).where(ChatMessage.conversation_id == conversation.id))
        for message_index, message in enumerate(messages):
            session.add(
                ChatMessage(
                    conversation_id=conversation.id,
                    notebook_id=notebook_id,
                    message_index=int(message.get("message_index", message_index)),
                    role=message.get("role", "assistant"),
                    content=message.get("content", ""),
                    retrieval_metadata=message.get("retrieval_metadata"),
                )
            )
        session.commit()


def create_note(
    notebook_id: str,
    content: str,
    *,
    source_message_id: Optional[str] = None,
    user_id: Optional[str] = None,
) -> Dict[str, Any]:
    with SessionLocal() as session:
        notebook_query = select(Notebook).where(Notebook.id == notebook_id)
        notebook_query = _apply_notebook_visibility(notebook_query, include_hidden=False)
        notebook_query = _apply_notebook_owner_scope(notebook_query, user_id)
        notebook = session.execute(notebook_query).scalar_one_or_none()
        if not notebook:
            raise ValueError("Notebook not found.")

        if source_message_id:
            source_message = session.execute(
                select(ChatMessage)
                .join(Conversation, ChatMessage.conversation_id == Conversation.id)
                .where(
                    ChatMessage.id == source_message_id,
                    ChatMessage.notebook_id == notebook_id,
                    Conversation.notebook_id == notebook_id,
                )
            ).scalar_one_or_none()
            if not source_message:
                raise ValueError("Source message does not belong to the notebook.")

        note = Note(
            notebook_id=notebook_id,
            content=content,
            source_message_id=source_message_id,
        )
        session.add(note)
        session.commit()
        session.refresh(note)
        return _note_to_dict(note)


def list_notes_for_notebook(notebook_id: str, *, user_id: Optional[str] = None) -> List[Dict[str, Any]]:
    with SessionLocal() as session:
        notebook_query = select(Notebook.id).where(Notebook.id == notebook_id)
        notebook_query = _apply_notebook_visibility(notebook_query, include_hidden=False)
        notebook_query = _apply_notebook_owner_scope(notebook_query, user_id)
        notebook_exists_for_user = session.execute(notebook_query).scalar_one_or_none()
        if not notebook_exists_for_user:
            return []

        notes = session.execute(
            select(Note).where(Note.notebook_id == notebook_id).order_by(Note.created_at.desc())
        ).scalars().all()
        return [_note_to_dict(note) for note in notes]


def delete_note(note_id: str, notebook_id: str, *, user_id: Optional[str] = None) -> bool:
    with SessionLocal() as session:
        notebook_query = select(Notebook.id).where(Notebook.id == notebook_id)
        notebook_query = _apply_notebook_visibility(notebook_query, include_hidden=False)
        notebook_query = _apply_notebook_owner_scope(notebook_query, user_id)
        notebook_exists_for_user = session.execute(notebook_query).scalar_one_or_none()
        if not notebook_exists_for_user:
            raise ValueError("Notebook not found.")

        note = session.execute(
            select(Note).where(Note.id == note_id, Note.notebook_id == notebook_id)
        ).scalar_one_or_none()
        if not note:
            return False

        session.delete(note)
        session.commit()
        return True


def get_document_summary(file_id: str) -> Optional[str]:
    record = get_document_record(file_id)
    return record["summary"] if record else None


def save_document_summary(file_id: str, summary: str, title: str = "", metadata: Optional[Dict[str, Any]] = None):
    page_count = metadata.get("pages") if metadata else None
    update_document_processing_status(
        file_id,
        DocumentProcessingStatus.indexed,
        processing_error=None,
        page_count=page_count,
        summary=summary,
        display_title=title or None,
    )


def remove_files(paths: Iterable[str]) -> None:
    for path in paths:
        if path and os.path.exists(path):
            try:
                os.remove(path)
            except OSError as exc:
                logger.warning(f"Failed to delete file {path}: {exc}")


def delete_files_strict(paths: Iterable[str]) -> None:
    failures: List[str] = []
    for path in paths:
        if not path or not os.path.exists(path):
            continue
        try:
            os.remove(path)
        except OSError as exc:
            logger.error(f"Failed to delete file {path}: {exc}")
            failures.append(path)
    if failures:
        raise OSError(f"Failed to delete files: {', '.join(failures)}")


init_db()
