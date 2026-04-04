"""Add user theme preference

Revision ID: 20260404_0010
Revises: 20260404_0009
Create Date: 2026-04-04 16:15:00
"""

from alembic import op
import sqlalchemy as sa


revision = "20260404_0010"
down_revision = "20260404_0009"
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    user_columns = {column["name"] for column in inspector.get_columns("users")}
    if "theme_preference" not in user_columns:
        op.add_column("users", sa.Column("theme_preference", sa.String(length=16), nullable=True))


def downgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    user_columns = {column["name"] for column in inspector.get_columns("users")}
    if "theme_preference" in user_columns:
        op.drop_column("users", "theme_preference")
