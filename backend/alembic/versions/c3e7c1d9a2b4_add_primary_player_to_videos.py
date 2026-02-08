"""add_primary_player_to_videos

Revision ID: c3e7c1d9a2b4
Revises: b9a4c1e7d92a
Create Date: 2026-02-08 12:45:00.000000

"""

from typing import Sequence, Union

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "c3e7c1d9a2b4"
down_revision: Union[str, Sequence[str], None] = "b9a4c1e7d92a"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def _get_columns(table_name: str) -> set[str]:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    if table_name not in inspector.get_table_names():
        return set()
    return {column["name"] for column in inspector.get_columns(table_name)}


def _get_foreign_keys(table_name: str) -> list[dict]:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    if table_name not in inspector.get_table_names():
        return []
    return inspector.get_foreign_keys(table_name)


def _has_fk(table_name: str, column_name: str) -> bool:
    for fk in _get_foreign_keys(table_name):
        constrained_columns = fk.get("constrained_columns", [])
        if column_name in constrained_columns:
            return True
    return False


def _get_indexes(table_name: str) -> set[str]:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    if table_name not in inspector.get_table_names():
        return set()
    return {index["name"] for index in inspector.get_indexes(table_name)}


def upgrade() -> None:
    """Upgrade schema."""
    columns = _get_columns("videos")
    if "primary_player_id" not in columns:
        op.add_column(
            "videos",
            sa.Column(
                "primary_player_id",
                sa.Integer(),
                nullable=True,
            ),
        )

    if not _has_fk("videos", "primary_player_id"):
        op.create_foreign_key(
            "fk_videos_primary_player_id_players",
            "videos",
            "players",
            ["primary_player_id"],
            ["id"],
            ondelete="SET NULL",
        )

    indexes = _get_indexes("videos")
    if "ix_videos_primary_player_id" not in indexes:
        op.create_index("ix_videos_primary_player_id", "videos", ["primary_player_id"])


def downgrade() -> None:
    """Downgrade schema."""
    indexes = _get_indexes("videos")
    if "ix_videos_primary_player_id" in indexes:
        op.drop_index("ix_videos_primary_player_id", table_name="videos")

    if _has_fk("videos", "primary_player_id"):
        op.drop_constraint(
            "fk_videos_primary_player_id_players",
            "videos",
            type_="foreignkey",
        )

    columns = _get_columns("videos")
    if "primary_player_id" in columns:
        op.drop_column("videos", "primary_player_id")
