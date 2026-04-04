"""Add notebook deletion lifecycle state

Revision ID: 20260401_0002
Revises: 20260401_0001
Create Date: 2026-04-01 01:00:00
"""

from alembic import op
import sqlalchemy as sa


revision = "20260401_0002"
down_revision = "20260401_0001"
branch_labels = None
depends_on = None


notebook_lifecycle_status = sa.Enum("active", "deleting", "delete_failed", name="notebooklifecyclestatus")


def upgrade() -> None:
    bind = op.get_bind()
    notebook_lifecycle_status.create(bind, checkfirst=True)
    op.add_column(
        "notebooks",
        sa.Column(
            "lifecycle_status",
            notebook_lifecycle_status,
            nullable=False,
            server_default="active",
        ),
    )
    op.add_column("notebooks", sa.Column("deletion_error", sa.Text(), nullable=True))
    op.create_index(op.f("ix_notebooks_lifecycle_status"), "notebooks", ["lifecycle_status"], unique=False)


def downgrade() -> None:
    op.drop_index(op.f("ix_notebooks_lifecycle_status"), table_name="notebooks")
    op.drop_column("notebooks", "deletion_error")
    op.drop_column("notebooks", "lifecycle_status")
    bind = op.get_bind()
    notebook_lifecycle_status.drop(bind, checkfirst=True)
