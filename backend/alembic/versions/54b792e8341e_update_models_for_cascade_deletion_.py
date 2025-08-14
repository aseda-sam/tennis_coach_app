"""Update models for cascade deletion support

Revision ID: 54b792e8341e
Revises: 0d5584d5cf51
Create Date: 2025-08-14 21:42:30.123456

"""

from typing import Sequence, Union

# revision identifiers, used by Alembic.
revision: str = "54b792e8341e"
down_revision: Union[str, Sequence[str], None] = "0d5584d5cf51"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Update models for cascade deletion support.

    This migration documents the model changes made to support cascade deletion.
    The actual cascade deletion is handled at the application level through:
    1. Updated foreign key constraint in Analysis model with ondelete='CASCADE'
    2. Relationship in Video model with cascade='all, delete-orphan'
    3. Cleanup script to remove existing orphaned records

    Note: SQLite has limitations with foreign key constraints, so the cascade
    deletion is primarily enforced at the application level through SQLAlchemy
    relationships and the cleanup script.
    """
    # No database schema changes needed for this migration
    # The cascade deletion is handled at the application level
    pass


def downgrade() -> None:
    """Revert cascade deletion support.

    This would require reverting the model changes in:
    - app/models/analysis.py
    - app/models/video.py
    """
    # No database schema changes to revert
    pass
