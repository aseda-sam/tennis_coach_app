"""add_is_demo_to_videos

Revision ID: 4212cb7567aa
Revises: d55e25138d67
Create Date: 2026-01-16 18:25:59.685031

"""
from typing import Sequence, Union

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = '4212cb7567aa'
down_revision: Union[str, Sequence[str], None] = 'd55e25138d67'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Add is_demo and original_user_id columns to videos table."""
    bind = op.get_bind()
    is_sqlite = bind.dialect.name == "sqlite"

    if is_sqlite:
        # SQLite: Use batch_alter_table
        with op.batch_alter_table("videos", schema=None) as batch_op:
            batch_op.add_column(
                sa.Column("is_demo", sa.Boolean(), nullable=False, server_default="false")
            )
            batch_op.add_column(
                sa.Column("original_user_id", sa.String(36), nullable=True)
            )
            batch_op.create_index("ix_videos_is_demo", ["is_demo"], unique=False)
    else:
        # PostgreSQL: Use direct operations
        op.add_column("videos", sa.Column("is_demo", sa.Boolean(), nullable=False, server_default="false"))
        op.add_column("videos", sa.Column("original_user_id", sa.String(36), nullable=True))
        op.create_index("ix_videos_is_demo", "videos", ["is_demo"], unique=False)

    # Set all existing videos to is_demo=False (explicit, even though default is false)
    op.execute("UPDATE videos SET is_demo = false WHERE is_demo IS NULL")


def downgrade() -> None:
    """Remove is_demo and original_user_id columns from videos table."""
    bind = op.get_bind()
    is_sqlite = bind.dialect.name == "sqlite"

    if is_sqlite:
        # SQLite: Use batch_alter_table
        with op.batch_alter_table("videos", schema=None) as batch_op:
            batch_op.drop_index("ix_videos_is_demo")
            batch_op.drop_column("original_user_id")
            batch_op.drop_column("is_demo")
    else:
        # PostgreSQL: Use direct operations
        op.drop_index("ix_videos_is_demo", table_name="videos")
        op.drop_column("videos", "original_user_id")
        op.drop_column("videos", "is_demo")
