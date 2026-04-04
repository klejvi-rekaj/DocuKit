"""Create notebook-first storage schema

Revision ID: 20260401_0001
Revises:
Create Date: 2026-04-01 00:00:00
"""

from alembic import op
import sqlalchemy as sa


revision = "20260401_0001"
down_revision = None
branch_labels = None
depends_on = None


document_processing_status = sa.Enum("uploaded", "processing", "indexed", "failed", "deleting", name="documentprocessingstatus")
embedding_status = sa.Enum("pending", "embedded", "failed", name="embeddingstatus")
indexing_job_status = sa.Enum("queued", "processing", "indexed", "failed", name="indexingjobstatus")


def upgrade() -> None:
    op.create_table(
        "users",
        sa.Column("email", sa.String(length=255), nullable=True),
        sa.Column("display_name", sa.String(length=255), nullable=True),
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("email"),
    )
    op.create_index(op.f("ix_users_email"), "users", ["email"], unique=False)

    op.create_table(
        "notebooks",
        sa.Column("user_id", sa.String(length=36), nullable=True),
        sa.Column("title", sa.String(length=255), nullable=False),
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_notebooks_user_id"), "notebooks", ["user_id"], unique=False)

    op.create_table(
        "documents",
        sa.Column("notebook_id", sa.String(length=36), nullable=False),
        sa.Column("original_filename", sa.String(length=512), nullable=False),
        sa.Column("display_title", sa.String(length=512), nullable=False),
        sa.Column("storage_path", sa.String(length=1024), nullable=False),
        sa.Column("mime_type", sa.String(length=255), nullable=False),
        sa.Column("file_size", sa.Integer(), nullable=False),
        sa.Column("page_count", sa.Integer(), nullable=True),
        sa.Column("processing_status", document_processing_status, nullable=False),
        sa.Column("processing_error", sa.Text(), nullable=True),
        sa.Column("summary", sa.Text(), nullable=True),
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
        sa.ForeignKeyConstraint(["notebook_id"], ["notebooks.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_documents_notebook_id"), "documents", ["notebook_id"], unique=False)
    op.create_index(op.f("ix_documents_processing_status"), "documents", ["processing_status"], unique=False)

    op.create_table(
        "conversations",
        sa.Column("notebook_id", sa.String(length=36), nullable=False),
        sa.Column("user_id", sa.String(length=36), nullable=True),
        sa.Column("title", sa.String(length=255), nullable=False),
        sa.Column("rolling_summary", sa.Text(), nullable=False),
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
        sa.ForeignKeyConstraint(["notebook_id"], ["notebooks.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_conversations_notebook_id"), "conversations", ["notebook_id"], unique=False)
    op.create_index(op.f("ix_conversations_user_id"), "conversations", ["user_id"], unique=False)

    op.create_table(
        "document_chunks",
        sa.Column("document_id", sa.String(length=36), nullable=False),
        sa.Column("notebook_id", sa.String(length=36), nullable=False),
        sa.Column("chunk_index", sa.Integer(), nullable=False),
        sa.Column("content", sa.Text(), nullable=False),
        sa.Column("page_number", sa.Integer(), nullable=True),
        sa.Column("token_count", sa.Integer(), nullable=True),
        sa.Column("embedding_status", embedding_status, nullable=False),
        sa.Column("embedding_model", sa.String(length=255), nullable=True),
        sa.Column("embedding_vector", sa.JSON(), nullable=True),
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
        sa.ForeignKeyConstraint(["document_id"], ["documents.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["notebook_id"], ["notebooks.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_document_chunks_document_id"), "document_chunks", ["document_id"], unique=False)
    op.create_index(op.f("ix_document_chunks_embedding_status"), "document_chunks", ["embedding_status"], unique=False)
    op.create_index(op.f("ix_document_chunks_notebook_id"), "document_chunks", ["notebook_id"], unique=False)

    op.create_table(
        "chat_messages",
        sa.Column("conversation_id", sa.String(length=36), nullable=False),
        sa.Column("notebook_id", sa.String(length=36), nullable=False),
        sa.Column("role", sa.String(length=32), nullable=False),
        sa.Column("content", sa.Text(), nullable=False),
        sa.Column("retrieval_metadata", sa.JSON(), nullable=True),
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
        sa.ForeignKeyConstraint(["conversation_id"], ["conversations.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["notebook_id"], ["notebooks.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_chat_messages_conversation_id"), "chat_messages", ["conversation_id"], unique=False)
    op.create_index(op.f("ix_chat_messages_notebook_id"), "chat_messages", ["notebook_id"], unique=False)

    op.create_table(
        "indexing_jobs",
        sa.Column("notebook_id", sa.String(length=36), nullable=False),
        sa.Column("document_id", sa.String(length=36), nullable=False),
        sa.Column("status", indexing_job_status, nullable=False),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("finished_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
        sa.ForeignKeyConstraint(["document_id"], ["documents.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["notebook_id"], ["notebooks.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_indexing_jobs_document_id"), "indexing_jobs", ["document_id"], unique=False)
    op.create_index(op.f("ix_indexing_jobs_notebook_id"), "indexing_jobs", ["notebook_id"], unique=False)
    op.create_index(op.f("ix_indexing_jobs_status"), "indexing_jobs", ["status"], unique=False)


def downgrade() -> None:
    op.drop_index(op.f("ix_indexing_jobs_status"), table_name="indexing_jobs")
    op.drop_index(op.f("ix_indexing_jobs_notebook_id"), table_name="indexing_jobs")
    op.drop_index(op.f("ix_indexing_jobs_document_id"), table_name="indexing_jobs")
    op.drop_table("indexing_jobs")

    op.drop_index(op.f("ix_chat_messages_notebook_id"), table_name="chat_messages")
    op.drop_index(op.f("ix_chat_messages_conversation_id"), table_name="chat_messages")
    op.drop_table("chat_messages")

    op.drop_index(op.f("ix_document_chunks_notebook_id"), table_name="document_chunks")
    op.drop_index(op.f("ix_document_chunks_embedding_status"), table_name="document_chunks")
    op.drop_index(op.f("ix_document_chunks_document_id"), table_name="document_chunks")
    op.drop_table("document_chunks")

    op.drop_index(op.f("ix_conversations_user_id"), table_name="conversations")
    op.drop_index(op.f("ix_conversations_notebook_id"), table_name="conversations")
    op.drop_table("conversations")

    op.drop_index(op.f("ix_documents_processing_status"), table_name="documents")
    op.drop_index(op.f("ix_documents_notebook_id"), table_name="documents")
    op.drop_table("documents")

    op.drop_index(op.f("ix_notebooks_user_id"), table_name="notebooks")
    op.drop_table("notebooks")

    op.drop_index(op.f("ix_users_email"), table_name="users")
    op.drop_table("users")
