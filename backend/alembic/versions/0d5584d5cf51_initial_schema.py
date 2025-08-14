"""initial_schema

Revision ID: 0d5584d5cf51
Revises:
Create Date: 2025-08-14 14:23:16.153460

"""

from typing import Sequence, Union

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "0d5584d5cf51"
down_revision: Union[str, Sequence[str], None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    # ### Create tables for initial schema ###
    op.create_table(
        "videos",
        sa.Column("id", sa.Integer(), primary_key=True, nullable=False),
        sa.Column("filename", sa.String(length=255), nullable=False),
        sa.Column("file_path", sa.String(length=500), nullable=False),
        sa.Column("file_size", sa.Integer(), nullable=False),
        sa.Column("content_type", sa.String(length=100), nullable=True),
        sa.Column(
            "duration",
            sa.Float(),
            nullable=True,
        ),
        sa.Column("fps", sa.Float(), nullable=True),
        sa.Column("width", sa.Integer(), nullable=True),
        sa.Column("height", sa.Integer(), nullable=True),
        sa.Column("frame_count", sa.Integer(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("CURRENT_TIMESTAMP"),
            nullable=True,
        ),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "status",
            sa.String(length=50),
            server_default=sa.text("'uploaded'"),
            nullable=True,
        ),
        sa.Column("error_message", sa.Text(), nullable=True),
    )

    op.create_index("ix_videos_id", "videos", ["id"], unique=False)
    op.create_index("ix_videos_filename", "videos", ["filename"], unique=True)

    op.create_table(
        "analyses",
        sa.Column("id", sa.Integer(), primary_key=True, nullable=False),
        sa.Column("video_id", sa.Integer(), sa.ForeignKey("videos.id"), nullable=True),
        sa.Column("video_filename", sa.String(), nullable=False),
        sa.Column("analysis_type", sa.String(), nullable=False),
        sa.Column(
            "total_frames", sa.Integer(), nullable=True, server_default=sa.text("0")
        ),
        sa.Column(
            "frames_with_balls",
            sa.Integer(),
            nullable=True,
            server_default=sa.text("0"),
        ),
        sa.Column(
            "total_ball_detections",
            sa.Integer(),
            nullable=True,
            server_default=sa.text("0"),
        ),
        sa.Column(
            "average_detections_per_frame",
            sa.Float(),
            nullable=True,
            server_default=sa.text("0.0"),
        ),
        sa.Column(
            "detection_rate", sa.Float(), nullable=True, server_default=sa.text("0.0")
        ),
        sa.Column(
            "frames_with_pose", sa.Integer(), nullable=True, server_default=sa.text("0")
        ),
        sa.Column(
            "pose_detection_rate",
            sa.Float(),
            nullable=True,
            server_default=sa.text("0.0"),
        ),
        sa.Column("ball_detections", sa.Text(), nullable=True),
        sa.Column("pose_detections", sa.Text(), nullable=True),
        sa.Column("annotated_video_path", sa.String(), nullable=True),
        sa.Column(
            "processing_time", sa.Float(), nullable=True, server_default=sa.text("0.0")
        ),
        sa.Column("model_used", sa.String(), nullable=True),
        sa.Column(
            "confidence_threshold",
            sa.Float(),
            nullable=True,
            server_default=sa.text("0.5"),
        ),
        sa.Column(
            "status",
            sa.String(length=50),
            nullable=True,
            server_default=sa.text("'completed'"),
        ),
        sa.Column("progress", sa.Integer(), nullable=True, server_default=sa.text("0")),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("CURRENT_TIMESTAMP"),
            nullable=True,
        ),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
    )

    op.create_index("ix_analyses_id", "analyses", ["id"], unique=False)
    op.create_index("ix_analyses_video_id", "analyses", ["video_id"], unique=False)
    op.create_index(
        "ix_analyses_video_filename", "analyses", ["video_filename"], unique=False
    )


def downgrade() -> None:
    """Downgrade schema."""
    # ### Drop tables in reverse order ###
    op.drop_index("ix_analyses_video_filename", table_name="analyses")
    op.drop_index("ix_analyses_video_id", table_name="analyses")
    op.drop_index("ix_analyses_id", table_name="analyses")
    op.drop_table("analyses")

    op.drop_index("ix_videos_filename", table_name="videos")
    op.drop_index("ix_videos_id", table_name="videos")
    op.drop_table("videos")
