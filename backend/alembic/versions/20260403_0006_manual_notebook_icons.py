"""Switch notebooks to manual icon selection

Revision ID: 20260403_0006
Revises: 20260403_0005
Create Date: 2026-04-03
"""

from alembic import op
import sqlalchemy as sa


revision = "20260403_0006"
down_revision = "20260403_0005"
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    columns = {column["name"] for column in inspector.get_columns("notebooks")}

    if "icon_key" not in columns:
        op.add_column(
            "notebooks",
            sa.Column("icon_key", sa.String(length=64), nullable=False, server_default="folder"),
        )

    indexes = {index["name"] for index in inspector.get_indexes("notebooks")}
    if "ix_notebooks_visual_theme_category" in indexes:
        op.drop_index("ix_notebooks_visual_theme_category", table_name="notebooks")

    for column_name in [
        "visual_theme_category",
        "primary_motif",
        "accent_motifs",
        "icon_asset_key",
        "secondary_categories",
        "semantic_keywords",
        "semantic_summary",
    ]:
        if column_name in columns:
            op.drop_column("notebooks", column_name)


def downgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    columns = {column["name"] for column in inspector.get_columns("notebooks")}

    if "visual_theme_category" not in columns:
        op.add_column("notebooks", sa.Column("visual_theme_category", sa.String(length=64), nullable=True))
    if "primary_motif" not in columns:
        op.add_column("notebooks", sa.Column("primary_motif", sa.String(length=64), nullable=True))
    if "accent_motifs" not in columns:
        op.add_column("notebooks", sa.Column("accent_motifs", sa.JSON(), nullable=True))
    if "icon_asset_key" not in columns:
        op.add_column("notebooks", sa.Column("icon_asset_key", sa.String(length=128), nullable=True))
    if "secondary_categories" not in columns:
        op.add_column("notebooks", sa.Column("secondary_categories", sa.JSON(), nullable=True))
    if "semantic_keywords" not in columns:
        op.add_column("notebooks", sa.Column("semantic_keywords", sa.JSON(), nullable=True))
    if "semantic_summary" not in columns:
        op.add_column("notebooks", sa.Column("semantic_summary", sa.Text(), nullable=True))

    indexes = {index["name"] for index in inspector.get_indexes("notebooks")}
    if "ix_notebooks_visual_theme_category" not in indexes:
        op.create_index("ix_notebooks_visual_theme_category", "notebooks", ["visual_theme_category"], unique=False)

    columns = {column["name"] for column in inspector.get_columns("notebooks")}
    if "icon_key" in columns:
        op.drop_column("notebooks", "icon_key")
