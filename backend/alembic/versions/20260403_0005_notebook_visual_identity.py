"""Add notebook visual identity metadata

Revision ID: 20260403_0005
Revises: 20260402_0004
Create Date: 2026-04-03
"""

from alembic import op
import sqlalchemy as sa


revision = "20260403_0005"
down_revision = "20260402_0004"
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    existing_columns = {column["name"] for column in inspector.get_columns("notebooks")}

    if "visual_theme_category" not in existing_columns:
        op.add_column("notebooks", sa.Column("visual_theme_category", sa.String(length=64), nullable=True))
    if "primary_motif" not in existing_columns:
        op.add_column("notebooks", sa.Column("primary_motif", sa.String(length=64), nullable=True))
    if "accent_motifs" not in existing_columns:
        op.add_column("notebooks", sa.Column("accent_motifs", sa.JSON(), nullable=True))
    if "icon_asset_key" not in existing_columns:
        op.add_column("notebooks", sa.Column("icon_asset_key", sa.String(length=128), nullable=True))
    if "secondary_categories" not in existing_columns:
        op.add_column("notebooks", sa.Column("secondary_categories", sa.JSON(), nullable=True))
    if "semantic_keywords" not in existing_columns:
        op.add_column("notebooks", sa.Column("semantic_keywords", sa.JSON(), nullable=True))
    if "semantic_summary" not in existing_columns:
        op.add_column("notebooks", sa.Column("semantic_summary", sa.Text(), nullable=True))

    indexes = {index["name"] for index in inspector.get_indexes("notebooks")}
    if "ix_notebooks_visual_theme_category" not in indexes:
        op.create_index("ix_notebooks_visual_theme_category", "notebooks", ["visual_theme_category"], unique=False)


def downgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    indexes = {index["name"] for index in inspector.get_indexes("notebooks")}
    if "ix_notebooks_visual_theme_category" in indexes:
        op.drop_index("ix_notebooks_visual_theme_category", table_name="notebooks")

    existing_columns = {column["name"] for column in inspector.get_columns("notebooks")}
    for column_name in [
        "semantic_summary",
        "semantic_keywords",
        "secondary_categories",
        "icon_asset_key",
        "accent_motifs",
        "primary_motif",
        "visual_theme_category",
    ]:
        if column_name in existing_columns:
            op.drop_column("notebooks", column_name)
