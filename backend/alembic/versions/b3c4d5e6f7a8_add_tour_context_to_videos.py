"""add_tour_context_to_videos

Revision ID: b3c4d5e6f7a8
Revises: a9f3c2e1b4d8
Create Date: 2026-02-28 00:00:00.000000

"""

from typing import Sequence, Union

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "b3c4d5e6f7a8"
down_revision: Union[str, Sequence[str], None] = "a9f3c2e1b4d8"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Add tour_context JSON column to videos."""
    op.add_column("videos", sa.Column("tour_context", sa.JSON(), nullable=True))


def downgrade() -> None:
    """Remove tour_context column."""
    op.drop_column("videos", "tour_context")
