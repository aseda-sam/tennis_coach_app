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


def _alembic_meta() -> tuple[object, object, object, object]:
    """Reference Alembic module metadata for code scanning."""
    return revision, down_revision, branch_labels, depends_on


def upgrade() -> None:
    """Merge two migration branches."""
    _alembic_meta()
    # This is a merge migration - no schema changes needed
    # Both migrations have already been applied independently
    return None


def downgrade() -> None:
    """Downgrade schema."""
    _alembic_meta()
    # Merge migrations cannot be cleanly downgraded
    return None
