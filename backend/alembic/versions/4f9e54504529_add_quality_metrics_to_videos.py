"""add_quality_metrics_to_videos

Revision ID: 4f9e54504529
Revises: 1a2b3c4d5e6f
Create Date: 2025-08-19 12:53:52.079543

"""

from typing import Sequence, Union

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "4f9e54504529"
down_revision: Union[str, Sequence[str], None] = "1a2b3c4d5e6f"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Add quality metrics columns to videos table."""
    # Add quality assessment columns
    op.add_column("videos", sa.Column("quality_score", sa.Float(), nullable=True))
    op.add_column("videos", sa.Column("blur_score", sa.Float(), nullable=True))
    op.add_column("videos", sa.Column("lighting_score", sa.Float(), nullable=True))
    op.add_column("videos", sa.Column("resolution_score", sa.Float(), nullable=True))
    op.add_column(
        "videos", sa.Column("quality_level", sa.String(length=20), nullable=True)
    )
    op.add_column(
        "videos",
        sa.Column("quality_assessed_at", sa.DateTime(timezone=True), nullable=True),
    )


def downgrade() -> None:
    """Remove quality metrics columns from videos table."""
    # Remove quality assessment columns
    op.drop_column("videos", "quality_assessed_at")
    op.drop_column("videos", "quality_level")
    op.drop_column("videos", "resolution_score")
    op.drop_column("videos", "lighting_score")
    op.drop_column("videos", "blur_score")
    op.drop_column("videos", "quality_score")
