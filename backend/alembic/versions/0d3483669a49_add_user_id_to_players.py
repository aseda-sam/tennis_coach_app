"""add_user_id_to_players

Revision ID: 0d3483669a49
Revises: 548990cbbcc3
Create Date: 2025-12-28 22:05:16.149917

"""

from typing import Sequence, Union

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "0d3483669a49"
down_revision: Union[str, Sequence[str], None] = "548990cbbcc3"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Add user_id column to players table for authentication."""
    op.add_column("players", sa.Column("user_id", sa.String(36), nullable=True))
    op.create_index("idx_players_user_id", "players", ["user_id"])


def downgrade() -> None:
    """Remove user_id column from players table."""
    op.drop_index("idx_players_user_id", "players")
    op.drop_column("players", "user_id")
