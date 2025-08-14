"""Add video_id FK and status to analyses

Revision ID: a1b2c3d4e5f6
Revises: 63c79de0875a
Create Date: 2025-08-14
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "a1b2c3d4e5f6"
down_revision: Union[str, None] = "63c79de0875a"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Add columns
    op.add_column("analyses", sa.Column("video_id", sa.Integer(), nullable=True))
    op.add_column(
        "analyses",
        sa.Column(
            "status", sa.String(length=50), server_default="completed", nullable=False
        ),
    )

    # Index + FK
    op.create_index(
        op.f("ix_analyses_video_id"), "analyses", ["video_id"], unique=False
    )
    op.create_foreign_key(
        "analyses_video_id_fkey",
        "analyses",
        "videos",
        ["video_id"],
        ["id"],
        ondelete=None,
    )

    # Backfill video_id by filename
    op.execute(
        """
        UPDATE analyses
        SET video_id = (
            SELECT id FROM videos WHERE videos.filename = analyses.video_filename
        )
        WHERE video_id IS NULL
        """
    )

    # Ensure status non-null
    op.execute("UPDATE analyses SET status = 'completed' WHERE status IS NULL")


def downgrade() -> None:
    op.drop_constraint("analyses_video_id_fkey", "analyses", type_="foreignkey")
    op.drop_index(op.f("ix_analyses_video_id"), table_name="analyses")
    op.drop_column("analyses", "status")
    op.drop_column("analyses", "video_id")
