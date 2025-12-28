"""add_user_id_to_videos

Revision ID: 548990cbbcc3
Revises: 4377c00f3e6e
Create Date: 2025-12-28 20:59:27.108518

"""
from typing import Sequence, Union

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = '548990cbbcc3'
down_revision: Union[str, Sequence[str], None] = '4377c00f3e6e'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Add user_id column to videos table for authentication."""
    op.add_column("videos", sa.Column("user_id", sa.String(36), nullable=True))
    op.create_index("idx_videos_user_id", "videos", ["user_id"])


def downgrade() -> None:
    """Remove user_id column from videos table."""
    op.drop_index("idx_videos_user_id", "videos")
    op.drop_column("videos", "user_id")
