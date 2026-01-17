"""add_is_active_demo_to_videos

Revision ID: d1f0ec4cf292
Revises: 4212cb7567aa
Create Date: 2026-01-17 11:44:51.106260

"""

from typing import Sequence, Union

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "d1f0ec4cf292"
down_revision: Union[str, Sequence[str], None] = "4212cb7567aa"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Add is_active_demo column to videos table."""
    bind = op.get_bind()
    is_sqlite = bind.dialect.name == "sqlite"

    if is_sqlite:
        # SQLite: Use batch_alter_table
        # SQLite stores Boolean as INTEGER (0/1), so use 0 for false
        with op.batch_alter_table("videos", schema=None) as batch_op:
            batch_op.add_column(
                sa.Column(
                    "is_active_demo",
                    sa.Boolean(),
                    nullable=False,
                    server_default=sa.text("0"),
                )
            )
            batch_op.create_index(
                "ix_videos_is_active_demo", ["is_active_demo"], unique=False
            )
        # Set all existing videos to is_active_demo=0 (false) in SQLite
        op.execute("UPDATE videos SET is_active_demo = 0")
    else:
        # PostgreSQL: Use direct operations
        op.add_column(
            "videos",
            sa.Column(
                "is_active_demo",
                sa.Boolean(),
                nullable=False,
                server_default=sa.text("false"),
            ),
        )
        op.create_index(
            "ix_videos_is_active_demo", "videos", ["is_active_demo"], unique=False
        )
        # Set all existing videos to is_active_demo=false in PostgreSQL
        op.execute("UPDATE videos SET is_active_demo = false")


def downgrade() -> None:
    """Remove is_active_demo column from videos table."""
    bind = op.get_bind()
    is_sqlite = bind.dialect.name == "sqlite"

    if is_sqlite:
        # SQLite: Use batch_alter_table
        with op.batch_alter_table("videos", schema=None) as batch_op:
            batch_op.drop_index("ix_videos_is_active_demo")
            batch_op.drop_column("is_active_demo")
    else:
        # PostgreSQL: Use direct operations
        op.drop_index("ix_videos_is_active_demo", table_name="videos")
        op.drop_column("videos", "is_active_demo")
