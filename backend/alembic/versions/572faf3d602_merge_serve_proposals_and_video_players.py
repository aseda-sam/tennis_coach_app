"""merge_serve_proposals_and_video_players

Revision ID: 572faf3d602
Revises: 98d49ef0d4d, fb60e79c5043
Create Date: 2026-01-30 12:00:00.000000

"""

from typing import Sequence, Union

# revision identifiers, used by Alembic.
revision: str = "572faf3d602"
down_revision: Union[str, Sequence[str], None] = ("98d49ef0d4d", "fb60e79c5043")
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Merge two migration branches."""
    # This is a merge migration - no schema changes needed
    # Both migrations have already been applied independently
    pass


def downgrade() -> None:
    """Downgrade schema."""
    # Merge migrations cannot be cleanly downgraded
    pass
