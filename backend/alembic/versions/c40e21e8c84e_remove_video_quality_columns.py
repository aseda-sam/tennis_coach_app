"""remove_video_quality_columns

Revision ID: c40e21e8c84e
Revises: 3f2a1c9d7b10
Create Date: 2026-01-25 00:00:00.000000

"""

from typing import Sequence, Union

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "c40e21e8c84e"
down_revision: Union[str, Sequence[str], None] = "3f2a1c9d7b10"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def _get_columns(table_name: str) -> set[str]:
    """Get set of column names for a table."""
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    if table_name not in inspector.get_table_names():
        return set()
    return {column["name"] for column in inspector.get_columns(table_name)}


def upgrade() -> None:
    """Remove video quality columns from videos table."""
    # Drop quality assessment columns (legacy from ball detection days)
    video_columns = _get_columns("videos")

    if "quality_assessed_at" in video_columns:
        op.drop_column("videos", "quality_assessed_at")
    if "quality_level" in video_columns:
        op.drop_column("videos", "quality_level")
    if "resolution_score" in video_columns:
        op.drop_column("videos", "resolution_score")
    if "lighting_score" in video_columns:
        op.drop_column("videos", "lighting_score")
    if "blur_score" in video_columns:
        op.drop_column("videos", "blur_score")
    if "quality_score" in video_columns:
        op.drop_column("videos", "quality_score")


def downgrade() -> None:
    """Restore video quality columns (for rollback)."""
    op.add_column(
        "videos",
        sa.Column("quality_score", sa.Float(), nullable=True),
    )
    op.add_column(
        "videos",
        sa.Column("blur_score", sa.Float(), nullable=True),
    )
    op.add_column(
        "videos",
        sa.Column("lighting_score", sa.Float(), nullable=True),
    )
    op.add_column(
        "videos",
        sa.Column("resolution_score", sa.Float(), nullable=True),
    )
    op.add_column(
        "videos",
        sa.Column("quality_level", sa.String(length=20), nullable=True),
    )
    op.add_column(
        "videos",
        sa.Column("quality_assessed_at", sa.DateTime(timezone=True), nullable=True),
    )
