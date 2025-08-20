"""remove_quality_metrics_from_analyses

Revision ID: ecaf51c7eb6d
Revises: 4f9e54504529
Create Date: 2025-08-19 12:54:52.079543

"""

from typing import Sequence, Union

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "ecaf51c7eb6d"
down_revision: Union[str, Sequence[str], None] = "4f9e54504529"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Remove quality metrics columns from analyses table."""
    # Remove quality assessment columns (keep only confidence_threshold_used)
    op.drop_column("analyses", "quality_level")
    op.drop_column("analyses", "resolution_score")
    op.drop_column("analyses", "lighting_score")
    op.drop_column("analyses", "blur_score")
    op.drop_column("analyses", "quality_score")


def downgrade() -> None:
    """Add quality metrics columns back to analyses table."""
    # Add quality assessment columns back
    op.add_column("analyses", sa.Column("quality_score", sa.Float(), nullable=True))
    op.add_column("analyses", sa.Column("blur_score", sa.Float(), nullable=True))
    op.add_column("analyses", sa.Column("lighting_score", sa.Float(), nullable=True))
    op.add_column("analyses", sa.Column("resolution_score", sa.Float(), nullable=True))
    op.add_column(
        "analyses", sa.Column("quality_level", sa.String(length=20), nullable=True)
    )
