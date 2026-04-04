"""Add password hashes and session storage

Revision ID: 20260403_0007
Revises: 20260403_0006
Create Date: 2026-04-03 00:30:00
"""

from alembic import op
import sqlalchemy as sa


revision = "20260403_0007"
down_revision = "20260403_0006"
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)

    user_columns = {column["name"] for column in inspector.get_columns("users")}
    if "password_hash" not in user_columns:
        op.add_column("users", sa.Column("password_hash", sa.String(length=255), nullable=True))

    tables = set(inspector.get_table_names())
    if "user_sessions" not in tables:
        op.create_table(
            "user_sessions",
            sa.Column("user_id", sa.String(length=36), nullable=False),
            sa.Column("token_hash", sa.String(length=64), nullable=False),
            sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
            sa.Column("last_seen_at", sa.DateTime(timezone=True), nullable=True),
            sa.Column("user_agent", sa.String(length=512), nullable=True),
            sa.Column("id", sa.String(length=36), nullable=False),
            sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
            sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
            sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
            sa.PrimaryKeyConstraint("id"),
            sa.UniqueConstraint("token_hash"),
        )

    session_indexes = {index["name"] for index in inspector.get_indexes("user_sessions")}
    if op.f("ix_user_sessions_expires_at") not in session_indexes:
        op.create_index(op.f("ix_user_sessions_expires_at"), "user_sessions", ["expires_at"], unique=False)
    if op.f("ix_user_sessions_token_hash") not in session_indexes:
        op.create_index(op.f("ix_user_sessions_token_hash"), "user_sessions", ["token_hash"], unique=False)
    if op.f("ix_user_sessions_user_id") not in session_indexes:
        op.create_index(op.f("ix_user_sessions_user_id"), "user_sessions", ["user_id"], unique=False)


def downgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)

    tables = set(inspector.get_table_names())
    if "user_sessions" in tables:
        session_indexes = {index["name"] for index in inspector.get_indexes("user_sessions")}
        if op.f("ix_user_sessions_user_id") in session_indexes:
            op.drop_index(op.f("ix_user_sessions_user_id"), table_name="user_sessions")
        if op.f("ix_user_sessions_token_hash") in session_indexes:
            op.drop_index(op.f("ix_user_sessions_token_hash"), table_name="user_sessions")
        if op.f("ix_user_sessions_expires_at") in session_indexes:
            op.drop_index(op.f("ix_user_sessions_expires_at"), table_name="user_sessions")
        op.drop_table("user_sessions")

    user_columns = {column["name"] for column in inspector.get_columns("users")}
    if "password_hash" in user_columns:
        op.drop_column("users", "password_hash")
