"""ball_detections table and toss metrics on serve_attempts

Revision ID: f1a2b3c4d5e6
Revises: ab12cd34ef56
Create Date: 2026-02-12

"""

from typing import Sequence, Union

import sqlalchemy as sa

from alembic import op

revision: str = "f1a2b3c4d5e6"
down_revision: Union[str, Sequence[str], None] = "ab12cd34ef56"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "ball_detections",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("video_id", sa.Integer(), nullable=False),
        sa.Column("total_frames", sa.Integer(), nullable=False),
        sa.Column("frames_with_ball", sa.Integer(), nullable=True, server_default="0"),
        sa.Column("detection_rate", sa.Float(), nullable=True, server_default="0"),
        sa.Column("ball_data", sa.Text(), nullable=True),
        sa.Column("processing_time_seconds", sa.Float(), nullable=False),
        sa.Column("frame_processing_rate", sa.Float(), nullable=True),
        sa.Column(
            "status", sa.String(length=50), nullable=False, server_default="completed"
        ),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.Column("time_windows", sa.Text(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=True,
        ),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(["video_id"], ["videos.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        op.f("ix_ball_detections_video_id"),
        "ball_detections",
        ["video_id"],
        unique=False,
    )

    op.add_column(
        "serve_attempts", sa.Column("toss_peak_height", sa.Float(), nullable=True)
    )
    op.add_column(
        "serve_attempts", sa.Column("toss_peak_timestamp", sa.Float(), nullable=True)
    )


def downgrade() -> None:
    op.drop_column("serve_attempts", "toss_peak_timestamp")
    op.drop_column("serve_attempts", "toss_peak_height")
    op.drop_index(op.f("ix_ball_detections_video_id"), table_name="ball_detections")
    op.drop_table("ball_detections")
