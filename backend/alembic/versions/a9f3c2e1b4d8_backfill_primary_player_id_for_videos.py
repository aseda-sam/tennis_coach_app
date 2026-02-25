"""backfill primary_player_id for existing videos

Revision ID: a9f3c2e1b4d8
Revises: b7c8d9e0f1a2
Create Date: 2026-02-25 00:00:00.000000

"""

from typing import Sequence, Union

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "a9f3c2e1b4d8"
down_revision: Union[str, Sequence[str], None] = "b7c8d9e0f1a2"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Set primary_player_id for videos where it is NULL.

    When the primary_player_to_videos migration (c3e7c1d9a2b4) added the column it
    left all existing rows as NULL.  The upload path also never auto-populated it
    until this fix.  For each video we assign the uploader's oldest player record
    (i.e. their default "Me" player), matching the logic used everywhere else in
    the codebase (get_or_create_default_player orders by created_at ASC).
    """
    op.execute(
        """
        UPDATE videos v
        SET primary_player_id = (
            SELECT p.id
            FROM players p
            WHERE p.user_id = v.user_id
            ORDER BY p.created_at ASC
            LIMIT 1
        )
        WHERE v.primary_player_id IS NULL
          AND EXISTS (
              SELECT 1 FROM players p WHERE p.user_id = v.user_id
          )
        """
    )


def downgrade() -> None:
    """Revert backfill — restore NULL for rows that were auto-backfilled.

    Because we cannot distinguish backfilled rows from rows that were set by
    the application after the column was introduced, this downgrade sets ALL
    primary_player_id values back to NULL.  Only use this if you are also
    reverting the c3e7c1d9a2b4 migration.
    """
    op.execute(
        """
        UPDATE videos
        SET primary_player_id = NULL
        """
    )
