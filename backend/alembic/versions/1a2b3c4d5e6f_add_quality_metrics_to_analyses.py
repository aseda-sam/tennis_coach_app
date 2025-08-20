"""add quality metrics columns to analyses

Revision ID: 1a2b3c4d5e6f
Revises: 0c2b5d53ba8c
Create Date: 2025-08-19
"""

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision = "1a2b3c4d5e6f"
down_revision = "0c2b5d53ba8c"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("analyses", sa.Column("quality_score", sa.Float(), nullable=True))
    op.add_column("analyses", sa.Column("blur_score", sa.Float(), nullable=True))
    op.add_column("analyses", sa.Column("lighting_score", sa.Float(), nullable=True))
    op.add_column("analyses", sa.Column("resolution_score", sa.Float(), nullable=True))
    op.add_column(
        "analyses", sa.Column("quality_level", sa.String(length=20), nullable=True)
    )
    op.add_column(
        "analyses", sa.Column("confidence_threshold_used", sa.Float(), nullable=True)
    )


def downgrade() -> None:
    op.drop_column("analyses", "confidence_threshold_used")
    op.drop_column("analyses", "quality_level")
    op.drop_column("analyses", "resolution_score")
    op.drop_column("analyses", "lighting_score")
    op.drop_column("analyses", "blur_score")
    op.drop_column("analyses", "quality_score")
