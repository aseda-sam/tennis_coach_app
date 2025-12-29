"""make_user_id_not_null

Revision ID: 823ec332e464
Revises: aeee916f28b9
Create Date: 2025-12-29 07:13:16.881630

"""
from typing import Sequence, Union

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = '823ec332e464'
down_revision: Union[str, Sequence[str], None] = 'aeee916f28b9'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Make user_id NOT NULL after data migration.

    IMPORTANT: Run migrate_user_ids.sql first to assign user_id to all existing records.
    This migration will fail if there are any NULL user_id values.
    """
    # Make videos.user_id NOT NULL
    op.alter_column("videos", "user_id", nullable=False, existing_type=sa.String(36))

    # Make players.user_id NOT NULL
    op.alter_column("players", "user_id", nullable=False, existing_type=sa.String(36))


def downgrade() -> None:
    """Revert user_id back to nullable (for rollback if needed)."""
    op.alter_column("videos", "user_id", nullable=True, existing_type=sa.String(36))
    op.alter_column("players", "user_id", nullable=True, existing_type=sa.String(36))
