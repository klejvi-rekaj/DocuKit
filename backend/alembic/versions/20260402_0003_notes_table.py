"""Add notes table

Revision ID: 20260402_0003
Revises: 20260401_0002
Create Date: 2026-04-02 00:00:00
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy import inspect


revision = "20260402_0003"
down_revision = "20260401_0002"
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind = op.get_bind()
    inspector = inspect(bind)
    existing_tables = set(inspector.get_table_names())

    if "notes" not in existing_tables:
        op.create_table(
            "notes",
            sa.Column("notebook_id", sa.String(length=36), nullable=False),
            sa.Column("content", sa.Text(), nullable=False),
            sa.Column("source_message_id", sa.String(length=36), nullable=True),
            sa.Column("id", sa.String(length=36), nullable=False),
            sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
            sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
            sa.ForeignKeyConstraint(["notebook_id"], ["notebooks.id"], ondelete="CASCADE"),
            sa.ForeignKeyConstraint(["source_message_id"], ["chat_messages.id"], ondelete="SET NULL"),
            sa.PrimaryKeyConstraint("id"),
        )

    existing_indexes = {index["name"] for index in inspector.get_indexes("notes")} if "notes" in inspector.get_table_names() else set()
    notebook_index = op.f("ix_notes_notebook_id")
    source_index = op.f("ix_notes_source_message_id")
    if notebook_index not in existing_indexes:
        op.create_index(notebook_index, "notes", ["notebook_id"], unique=False)
    if source_index not in existing_indexes:
        op.create_index(source_index, "notes", ["source_message_id"], unique=False)


def downgrade() -> None:
    op.drop_index(op.f("ix_notes_source_message_id"), table_name="notes")
    op.drop_index(op.f("ix_notes_notebook_id"), table_name="notes")
    op.drop_table("notes")
