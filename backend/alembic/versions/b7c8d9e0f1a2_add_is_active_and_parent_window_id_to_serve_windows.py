"""add_is_active_and_parent_window_id_to_serve_windows

Revision ID: b7c8d9e0f1a2
Revises: f5fdd0df2ff5
Create Date: 2026-02-25 10:00:00.000000

Adds:
- is_active (Boolean, NOT NULL, DEFAULT TRUE): False when superseded by a split operation.
- parent_window_id (Integer, FK -> serve_windows.id, nullable): set on children created by split.
- Index ix_serve_windows_video_active on (video_id, is_active).

Existing rows are backfilled with is_active = TRUE.
"""

from typing import Sequence, Union

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "b7c8d9e0f1a2"
down_revision: Union[str, Sequence[str], None] = "f5fdd0df2ff5"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Add is_active column (nullable first so we can backfill, then set NOT NULL)
    op.add_column(
        "serve_windows",
        sa.Column("is_active", sa.Boolean(), nullable=True),
    )
    # Backfill existing rows
    op.execute("UPDATE serve_windows SET is_active = TRUE")
    # Now enforce NOT NULL
    op.alter_column("serve_windows", "is_active", nullable=False)

    # Add parent_window_id FK (self-referential, nullable)
    op.add_column(
        "serve_windows",
        sa.Column("parent_window_id", sa.Integer(), nullable=True),
    )
    op.create_foreign_key(
        "fk_serve_windows_parent_window_id",
        "serve_windows",
        "serve_windows",
        ["parent_window_id"],
        ["id"],
        ondelete="SET NULL",
    )

    # Add composite index for active window queries
    op.create_index(
        "ix_serve_windows_video_active",
        "serve_windows",
        ["video_id", "is_active"],
    )


def downgrade() -> None:
    op.drop_index("ix_serve_windows_video_active", table_name="serve_windows")
    op.drop_constraint(
        "fk_serve_windows_parent_window_id", "serve_windows", type_="foreignkey"
    )
    op.drop_column("serve_windows", "parent_window_id")
    op.drop_column("serve_windows", "is_active")
