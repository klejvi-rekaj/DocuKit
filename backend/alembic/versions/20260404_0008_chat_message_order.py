"""Add explicit chat message ordering

Revision ID: 20260404_0008
Revises: 20260403_0007
Create Date: 2026-04-04 12:00:00
"""

from alembic import op
import sqlalchemy as sa


revision = "20260404_0008"
down_revision = "20260403_0007"
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    columns = {column["name"] for column in inspector.get_columns("chat_messages")}

    if "message_index" not in columns:
        op.add_column("chat_messages", sa.Column("message_index", sa.Integer(), nullable=True))

    metadata = sa.MetaData()
    chat_messages = sa.Table(
        "chat_messages",
        metadata,
        sa.Column("id", sa.String(length=36), primary_key=True),
        sa.Column("conversation_id", sa.String(length=36), nullable=False),
        sa.Column("message_index", sa.Integer(), nullable=True),
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

    with op.batch_alter_table("chat_messages") as batch_op:
        batch_op.alter_column("message_index", existing_type=sa.Integer(), nullable=False)


def downgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    columns = {column["name"] for column in inspector.get_columns("chat_messages")}
    if "message_index" in columns:
        with op.batch_alter_table("chat_messages") as batch_op:
            batch_op.drop_column("message_index")
