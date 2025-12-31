"""remove_video_shares_table

Revision ID: 8591bc6ff486
Revises: 823ec332e464
Create Date: 2025-12-29 07:42:17.355357

"""

from typing import Sequence, Union

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "8591bc6ff486"
down_revision: Union[str, Sequence[str], None] = "823ec332e464"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Remove video_shares table (not implementing video sharing)."""
    op.drop_index("idx_video_shares_user_id", "video_shares")
    op.drop_index("idx_video_shares_video_id", "video_shares")
    op.drop_table("video_shares")


def downgrade() -> None:
    """Recreate video_shares table (for rollback if needed)."""
    op.create_table(
        "video_shares",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("video_id", sa.Integer(), nullable=False),
        sa.Column("shared_with_user_id", sa.String(36), nullable=False),
        sa.Column("permission", sa.String(20), nullable=False, server_default="view"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(
            ["video_id"],
            ["videos.id"],
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("video_id", "shared_with_user_id", name="uq_video_share"),
    )
    op.create_index("idx_video_shares_video_id", "video_shares", ["video_id"])
    op.create_index("idx_video_shares_user_id", "video_shares", ["shared_with_user_id"])
