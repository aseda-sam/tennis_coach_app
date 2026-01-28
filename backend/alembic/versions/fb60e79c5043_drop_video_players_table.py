"""drop_video_players_table

Revision ID: fb60e79c5043
Revises: 7d36585465af
Create Date: 2026-01-28 15:38:52.356658

"""

from typing import Sequence, Union

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "fb60e79c5043"
down_revision: Union[str, Sequence[str], None] = "7d36585465af"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Drop video_players table (legacy table, no longer used).

    This table was created in the initial schema but is no longer part of
    the application model. The relationship between videos and players is
    now handled through serve_attempts.

    Made idempotent to handle cases where table may not exist in some
    environments (e.g., already dropped locally).
    """
    # Drop table if it exists (idempotent)
    op.execute("""
        DO $$
        BEGIN
            IF EXISTS (
                SELECT FROM information_schema.tables
                WHERE table_schema = 'public'
                AND table_name = 'video_players'
            ) THEN
                -- Drop indexes first
                DROP INDEX IF EXISTS ix_video_players_video_id;
                DROP INDEX IF EXISTS ix_video_players_pose_detection_id;
                DROP INDEX IF EXISTS ix_video_players_player_id;
                DROP INDEX IF EXISTS ix_video_players_id;

                -- Drop table (cascades to foreign keys)
                DROP TABLE public.video_players CASCADE;
            END IF;
        END $$;
    """)


def downgrade() -> None:
    """Recreate video_players table (for rollback if needed)."""
    op.create_table(
        "video_players",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("video_id", sa.Integer(), nullable=False),
        sa.Column("player_id", sa.Integer(), nullable=False),
        sa.Column("pose_detection_id", sa.Integer(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(["player_id"], ["players.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(
            ["pose_detection_id"],
            ["pose_detections.id"],
        ),
        sa.ForeignKeyConstraint(["video_id"], ["videos.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("video_id", "player_id", name="uq_video_player"),
    )
    op.create_index(op.f("ix_video_players_id"), "video_players", ["id"], unique=False)
    op.create_index(
        op.f("ix_video_players_player_id"), "video_players", ["player_id"], unique=False
    )
    op.create_index(
        op.f("ix_video_players_pose_detection_id"),
        "video_players",
        ["pose_detection_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_video_players_video_id"), "video_players", ["video_id"], unique=False
    )
