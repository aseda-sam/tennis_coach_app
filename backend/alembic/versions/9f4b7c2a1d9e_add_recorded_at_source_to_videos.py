"""add_recorded_at_source_to_videos

Revision ID: 9f4b7c2a1d9e
Revises: e8de030d34fd
Create Date: 2026-02-09 10:00:00.000000

"""

from typing import Sequence, Union

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "9f4b7c2a1d9e"
down_revision: Union[str, Sequence[str], None] = "e8de030d34fd"
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
    columns = _get_columns("videos")
    if "recorded_at_source" not in columns:
        op.add_column(
            "videos",
            sa.Column("recorded_at_source", sa.String(length=20), nullable=True),
        )


def downgrade() -> None:
    """Downgrade schema."""
    columns = _get_columns("videos")
    if "recorded_at_source" in columns:
        op.drop_column("videos", "recorded_at_source")
