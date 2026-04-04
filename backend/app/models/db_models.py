import uuid
from datetime import datetime
from enum import Enum

from sqlalchemy import DateTime, Enum as SqlEnum, ForeignKey, Integer, JSON, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


def _uuid() -> str:
    return str(uuid.uuid4())


class BaseModelMixin:
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )


class DocumentProcessingStatus(str, Enum):
    uploaded = "uploaded"
    processing = "processing"
    indexed = "indexed"
    failed = "failed"
    deleting = "deleting"


class EmbeddingStatus(str, Enum):
    pending = "pending"
    embedded = "embedded"
    failed = "failed"


class NotebookLifecycleStatus(str, Enum):
    active = "active"
    deleting = "deleting"
    delete_failed = "delete_failed"


class IndexingJobStatus(str, Enum):
    queued = "queued"
    processing = "processing"
    indexed = "indexed"
    failed = "failed"


class User(Base, BaseModelMixin):
    __tablename__ = "users"

    email: Mapped[str | None] = mapped_column(String(255), unique=True, nullable=True, index=True)
    display_name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    password_hash: Mapped[str | None] = mapped_column(String(255), nullable=True)
    theme_preference: Mapped[str | None] = mapped_column(String(16), nullable=True)

    notebooks: Mapped[list["Notebook"]] = relationship(back_populates="user")
    conversations: Mapped[list["Conversation"]] = relationship(back_populates="user")
    sessions: Mapped[list["UserSession"]] = relationship(back_populates="user", cascade="all, delete-orphan")


class UserSession(Base, BaseModelMixin):
    __tablename__ = "user_sessions"

    user_id: Mapped[str] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    token_hash: Mapped[str] = mapped_column(String(64), unique=True, nullable=False, index=True)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, index=True)
    last_seen_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    user_agent: Mapped[str | None] = mapped_column(String(512), nullable=True)

    user: Mapped["User"] = relationship(back_populates="sessions")


class Notebook(Base, BaseModelMixin):
    __tablename__ = "notebooks"

    user_id: Mapped[str | None] = mapped_column(ForeignKey("users.id", ondelete="SET NULL"), nullable=True, index=True)
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    icon_key: Mapped[str] = mapped_column(String(64), nullable=False, default="folder")
    share_id: Mapped[str | None] = mapped_column(String(36), unique=True, nullable=True, index=True)
    lifecycle_status: Mapped[NotebookLifecycleStatus] = mapped_column(
        SqlEnum(NotebookLifecycleStatus),
        nullable=False,
        default=NotebookLifecycleStatus.active,
        index=True,
    )
    deletion_error: Mapped[str | None] = mapped_column(Text, nullable=True)

    user: Mapped[User | None] = relationship(back_populates="notebooks")
    documents: Mapped[list["Document"]] = relationship(back_populates="notebook", cascade="all, delete-orphan")
    chunks: Mapped[list["DocumentChunk"]] = relationship(back_populates="notebook", cascade="all, delete-orphan")
    conversations: Mapped[list["Conversation"]] = relationship(back_populates="notebook", cascade="all, delete-orphan")
    indexing_jobs: Mapped[list["IndexingJob"]] = relationship(back_populates="notebook", cascade="all, delete-orphan")
    notes: Mapped[list["Note"]] = relationship(back_populates="notebook", cascade="all, delete-orphan")


class Document(Base, BaseModelMixin):
    __tablename__ = "documents"

    notebook_id: Mapped[str] = mapped_column(ForeignKey("notebooks.id", ondelete="CASCADE"), nullable=False, index=True)
    original_filename: Mapped[str] = mapped_column(String(512), nullable=False)
    display_title: Mapped[str] = mapped_column(String(512), nullable=False)
    storage_path: Mapped[str] = mapped_column(String(1024), nullable=False)
    mime_type: Mapped[str] = mapped_column(String(255), nullable=False)
    file_size: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    page_count: Mapped[int | None] = mapped_column(Integer, nullable=True)
    processing_status: Mapped[DocumentProcessingStatus] = mapped_column(
        SqlEnum(DocumentProcessingStatus),
        nullable=False,
        default=DocumentProcessingStatus.uploaded,
        index=True,
    )
    processing_error: Mapped[str | None] = mapped_column(Text, nullable=True)
    summary: Mapped[str | None] = mapped_column(Text, nullable=True)

    notebook: Mapped[Notebook] = relationship(back_populates="documents")
    chunks: Mapped[list["DocumentChunk"]] = relationship(back_populates="document", cascade="all, delete-orphan")
    indexing_jobs: Mapped[list["IndexingJob"]] = relationship(back_populates="document", cascade="all, delete-orphan")


class DocumentChunk(Base, BaseModelMixin):
    __tablename__ = "document_chunks"

    document_id: Mapped[str] = mapped_column(ForeignKey("documents.id", ondelete="CASCADE"), nullable=False, index=True)
    notebook_id: Mapped[str] = mapped_column(ForeignKey("notebooks.id", ondelete="CASCADE"), nullable=False, index=True)
    chunk_index: Mapped[int] = mapped_column(Integer, nullable=False)
    content: Mapped[str] = mapped_column(Text, nullable=False)
    page_number: Mapped[int | None] = mapped_column(Integer, nullable=True)
    token_count: Mapped[int | None] = mapped_column(Integer, nullable=True)
    embedding_status: Mapped[EmbeddingStatus] = mapped_column(
        SqlEnum(EmbeddingStatus),
        nullable=False,
        default=EmbeddingStatus.pending,
        index=True,
    )
    embedding_model: Mapped[str | None] = mapped_column(String(255), nullable=True)
    embedding_vector: Mapped[list[float] | None] = mapped_column(JSON, nullable=True)

    document: Mapped[Document] = relationship(back_populates="chunks")
    notebook: Mapped[Notebook] = relationship(back_populates="chunks")


class Conversation(Base, BaseModelMixin):
    __tablename__ = "conversations"

    notebook_id: Mapped[str] = mapped_column(ForeignKey("notebooks.id", ondelete="CASCADE"), nullable=False, index=True)
    user_id: Mapped[str | None] = mapped_column(ForeignKey("users.id", ondelete="SET NULL"), nullable=True, index=True)
    title: Mapped[str] = mapped_column(String(255), nullable=False, default="Notebook chat")
    rolling_summary: Mapped[str] = mapped_column(Text, nullable=False, default="")

    notebook: Mapped[Notebook] = relationship(back_populates="conversations")
    user: Mapped[User | None] = relationship(back_populates="conversations")
    messages: Mapped[list["ChatMessage"]] = relationship(back_populates="conversation", cascade="all, delete-orphan")


class ChatMessage(Base, BaseModelMixin):
    __tablename__ = "chat_messages"

    conversation_id: Mapped[str] = mapped_column(ForeignKey("conversations.id", ondelete="CASCADE"), nullable=False, index=True)
    notebook_id: Mapped[str] = mapped_column(ForeignKey("notebooks.id", ondelete="CASCADE"), nullable=False, index=True)
    message_index: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    role: Mapped[str] = mapped_column(String(32), nullable=False)
    content: Mapped[str] = mapped_column(Text, nullable=False)
    retrieval_metadata: Mapped[dict | None] = mapped_column(JSON, nullable=True)

    conversation: Mapped[Conversation] = relationship(back_populates="messages")
    notes: Mapped[list["Note"]] = relationship(back_populates="source_message")


class IndexingJob(Base, BaseModelMixin):
    __tablename__ = "indexing_jobs"

    notebook_id: Mapped[str] = mapped_column(ForeignKey("notebooks.id", ondelete="CASCADE"), nullable=False, index=True)
    document_id: Mapped[str] = mapped_column(ForeignKey("documents.id", ondelete="CASCADE"), nullable=False, index=True)
    status: Mapped[IndexingJobStatus] = mapped_column(
        SqlEnum(IndexingJobStatus),
        nullable=False,
        default=IndexingJobStatus.queued,
        index=True,
    )
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    finished_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    notebook: Mapped[Notebook] = relationship(back_populates="indexing_jobs")
    document: Mapped[Document] = relationship(back_populates="indexing_jobs")


class Note(Base, BaseModelMixin):
    __tablename__ = "notes"

    notebook_id: Mapped[str] = mapped_column(ForeignKey("notebooks.id", ondelete="CASCADE"), nullable=False, index=True)
    content: Mapped[str] = mapped_column(Text, nullable=False)
    source_message_id: Mapped[str | None] = mapped_column(
        ForeignKey("chat_messages.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )

    notebook: Mapped[Notebook] = relationship(back_populates="notes")
    source_message: Mapped[ChatMessage | None] = relationship(back_populates="notes")
