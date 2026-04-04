"""Add notebook share id

Revision ID: 20260402_0004
Revises: 20260402_0003
Create Date: 2026-04-02
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy import inspect


revision = "20260402_0004"
down_revision = "20260402_0003"
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind = op.get_bind()
    inspector = inspect(bind)
    columns = {column["name"] for column in inspector.get_columns("notebooks")}
    indexes = {index["name"] for index in inspector.get_indexes("notebooks")}

    if "share_id" not in columns:
        op.add_column("notebooks", sa.Column("share_id", sa.String(length=36), nullable=True))

    if "ix_notebooks_share_id" not in indexes:
        op.create_index("ix_notebooks_share_id", "notebooks", ["share_id"], unique=True)


def downgrade() -> None:
    bind = op.get_bind()
    inspector = inspect(bind)
    columns = {column["name"] for column in inspector.get_columns("notebooks")}
    indexes = {index["name"] for index in inspector.get_indexes("notebooks")}

    if "ix_notebooks_share_id" in indexes:
        op.drop_index("ix_notebooks_share_id", table_name="notebooks")
    if "share_id" in columns:
        op.drop_column("notebooks", "share_id")
