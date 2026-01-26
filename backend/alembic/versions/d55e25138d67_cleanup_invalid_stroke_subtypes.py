"""cleanup_invalid_stroke_subtypes

Revision ID: d55e25138d67
Revises: d30414b42ecb
Create Date: 2026-01-15 16:55:13.364337

"""

import logging
from typing import Sequence, Union

import sqlalchemy as sa

from alembic import op

logger = logging.getLogger(__name__)

# revision identifiers, used by Alembic.
revision: str = "d55e25138d67"
down_revision: Union[str, Sequence[str], None] = "d30414b42ecb"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Migrate legacy stroke subtypes to canonical subtypes.

    NOTE: This migration is now a no-op because:
    1. The ball_contacts table was dropped in migration 3f2a1c9d7b10
    2. The shot_types functions it depended on were removed in favor of serve-only MVP
    3. This migration likely already ran before the table was dropped

    If the ball_contacts table exists, this migration will skip (table already dropped).
    """
    bind = op.get_bind()
    inspector = sa.inspect(bind)

    # Check if ball_contacts table exists (it shouldn't after migration 3f2a1c9d7b10)
    if "ball_contacts" not in inspector.get_table_names():
        logger.info(
            "Migration d55e25138d67 skipped: ball_contacts table does not exist "
            "(table was dropped in migration 3f2a1c9d7b10)"
        )
        return

    # If table exists (shouldn't happen), log warning but don't fail
    logger.warning(
        "ball_contacts table still exists but migration dependencies removed. "
        "Skipping subtype cleanup."
    )


def downgrade() -> None:
    """Downgrade schema.

    Note: This migration cannot be reversed as we don't store the original
    invalid subtype values. The data loss is acceptable as these were
    invalid values that would cause validation errors.
    """
    pass
