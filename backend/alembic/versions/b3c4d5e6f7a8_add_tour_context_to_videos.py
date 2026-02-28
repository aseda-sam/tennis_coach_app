"""add_tour_context_to_videos

Revision ID: b3c4d5e6f7a8
Revises: a9f3c2e1b4d8
Create Date: 2026-02-28 00:00:00.000000

"""

import json
from typing import Sequence, Union

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "b3c4d5e6f7a8"
down_revision: Union[str, Sequence[str], None] = "a9f3c2e1b4d8"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


# Tour context for known demo videos, keyed by filename fragment.
# These are observational — they describe what is interesting to *notice*
# in the video, not coaching prescriptions.
_MPETSHI_CONTEXT = {
    "player_note": "ATP pro · 6'8\" (204 cm) · serve practice",
    "step_notes": {
        "hero-display": (
            "At 6'8\", the contact point sits well above head height. "
            "Watch how the trunk rotation and arm extension time together "
            "through the upswing."
        ),
        "metrics-section": (
            "The Knee Flexion value here reflects the leg drive that propels "
            "this much height and mass into the ball at contact."
        ),
    },
}


def upgrade() -> None:
    """Add tour_context JSON column to videos and seed known demo videos."""
    op.add_column("videos", sa.Column("tour_context", sa.JSON(), nullable=True))

    # Seed tour_context for known demo videos by filename pattern.
    # Safe to run on both local and prod — UPDATE only affects existing rows.
    connection = op.get_bind()
    connection.execute(
        sa.text(
            "UPDATE videos SET tour_context = :ctx "
            "WHERE filename LIKE :pattern AND is_demo = true"
        ),
        {
            "ctx": json.dumps(_MPETSHI_CONTEXT),
            "pattern": "%Mpetshi%",
        },
    )


def downgrade() -> None:
    """Remove tour_context column."""
    op.drop_column("videos", "tour_context")
