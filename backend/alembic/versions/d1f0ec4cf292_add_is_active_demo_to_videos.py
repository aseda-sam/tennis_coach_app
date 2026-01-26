"""add_is_active_demo_to_videos

Revision ID: d1f0ec4cf292
Revises: 4212cb7567aa
Create Date: 2026-01-17 11:44:51.106260

"""

from typing import Sequence, Union

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "d1f0ec4cf292"
down_revision: Union[str, Sequence[str], None] = "4212cb7567aa"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Add is_active_demo column to videos table."""
    op.add_column(
        "videos",
        sa.Column(
            "is_active_demo",
            sa.Boolean(),
            nullable=False,
            server_default=sa.text("false"),
        ),
    )
    op.create_index(
        "ix_videos_is_active_demo", "videos", ["is_active_demo"], unique=False
    )
    # Set all existing videos to is_active_demo=false
    op.execute("UPDATE videos SET is_active_demo = false")


def downgrade() -> None:
    """Remove is_active_demo column from videos table."""
    op.drop_index("ix_videos_is_active_demo", table_name="videos")
    op.drop_column("videos", "is_active_demo")
