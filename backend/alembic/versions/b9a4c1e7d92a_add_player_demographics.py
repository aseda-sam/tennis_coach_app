"""add_player_demographics

Revision ID: b9a4c1e7d92a
Revises: fb60e79c5043
Create Date: 2026-02-07 12:00:00.000000

"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "b9a4c1e7d92a"
down_revision: Union[str, Sequence[str], None] = "fb60e79c5043"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def _get_columns(table_name: str) -> set[str]:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    if table_name not in inspector.get_table_names():
        return set()
    return {column["name"] for column in inspector.get_columns(table_name)}


def upgrade() -> None:
    """Upgrade schema."""
    columns = _get_columns("players")
    if "height_cm" not in columns:
        op.add_column("players", sa.Column("height_cm", sa.Float(), nullable=True))
    if "age_group" not in columns:
        op.add_column("players", sa.Column("age_group", sa.String(length=20), nullable=True))
    if "gender" not in columns:
        op.add_column("players", sa.Column("gender", sa.String(length=30), nullable=True))


def downgrade() -> None:
    """Downgrade schema."""
    columns = _get_columns("players")
    if "gender" in columns:
        op.drop_column("players", "gender")
    if "age_group" in columns:
        op.drop_column("players", "age_group")
    if "height_cm" in columns:
        op.drop_column("players", "height_cm")
