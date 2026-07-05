"""add is_self flag to players

The account owner's player is now identified by an explicit is_self flag
instead of creation order. Backfill: for each user, the earliest-created
player that is not the dedicated "Someone Else" player is marked as self.
This matches the previous implicit behaviour (first-created player was
treated as the owner) except that "Someone Else" can no longer be adopted
as the owner's identity.

Revision ID: b7e4d1a9c3f2
Revises: a9f3c2e1b4d8
Create Date: 2026-07-05

"""

from typing import Sequence, Union

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "b7e4d1a9c3f2"
down_revision: Union[str, Sequence[str], None] = "a9f3c2e1b4d8"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.add_column(
        "players",
        sa.Column(
            "is_self", sa.Boolean(), server_default=sa.text("false"), nullable=False
        ),
    )
    # Backfill: earliest non-"Someone Else" player per user becomes self.
    op.execute(
        """
        UPDATE players
        SET is_self = true
        WHERE id IN (
            SELECT DISTINCT ON (user_id) id
            FROM players
            WHERE name != 'Someone Else'
            ORDER BY user_id, created_at ASC
        )
        """
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_column("players", "is_self")
