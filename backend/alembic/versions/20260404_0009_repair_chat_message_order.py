"""Repair chat message ordering for existing conversations

Revision ID: 20260404_0009
Revises: 20260404_0008
Create Date: 2026-04-04 12:30:00
"""

from alembic import op
import sqlalchemy as sa


revision = "20260404_0009"
down_revision = "20260404_0008"
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind = op.get_bind()
    dialect = bind.dialect.name

    if dialect == "postgresql":
        bind.execute(
            sa.text(
                """
                WITH ranked AS (
                    SELECT
                        id,
                        ROW_NUMBER() OVER (
                            PARTITION BY conversation_id
                            ORDER BY created_at ASC, ctid ASC
                        ) - 1 AS new_index
                    FROM chat_messages
                )
                UPDATE chat_messages AS chat
                SET message_index = ranked.new_index
                FROM ranked
                WHERE chat.id = ranked.id
                """
            )
        )
        return

    if dialect == "sqlite":
        bind.execute(
            sa.text(
                """
                WITH ranked AS (
                    SELECT
                        rowid,
                        ROW_NUMBER() OVER (
                            PARTITION BY conversation_id
                            ORDER BY created_at ASC, rowid ASC
                        ) - 1 AS new_index
                    FROM chat_messages
                )
                UPDATE chat_messages
                SET message_index = (
                    SELECT ranked.new_index
                    FROM ranked
                    WHERE ranked.rowid = chat_messages.rowid
                )
                """
            )
        )
        return

    metadata = sa.MetaData()
    chat_messages = sa.Table(
        "chat_messages",
        metadata,
        sa.Column("id", sa.String(length=36), primary_key=True),
        sa.Column("conversation_id", sa.String(length=36), nullable=False),
        sa.Column("message_index", sa.Integer(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=True),
    )

    conversation_ids = [row[0] for row in bind.execute(sa.select(chat_messages.c.conversation_id).distinct())]
    for conversation_id in conversation_ids:
        rows = bind.execute(
            sa.select(chat_messages.c.id)
            .where(chat_messages.c.conversation_id == conversation_id)
            .order_by(chat_messages.c.created_at.asc(), chat_messages.c.id.asc())
        ).fetchall()
        for index, row in enumerate(rows):
            bind.execute(
                chat_messages.update()
                .where(chat_messages.c.id == row.id)
                .values(message_index=index)
            )


def downgrade() -> None:
    # This migration only repairs data ordering and has no schema change to reverse.
    pass
