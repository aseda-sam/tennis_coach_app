"""remove_legacy_analyses_table

Revision ID: b5dff1b26946
Revises: 4607cab0cb52
Create Date: 2025-09-03 18:51:44.521555

"""

from typing import Sequence, Union

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "b5dff1b26946"
down_revision: Union[str, Sequence[str], None] = "4607cab0cb52"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Remove legacy analyses table."""
    # Drop the legacy analyses table
    op.drop_table("analyses")


def downgrade() -> None:
    """Recreate legacy analyses table (for rollback)."""
    # Recreate the analyses table with the original schema
    op.create_table(
        "analyses",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("video_id", sa.Integer(), nullable=False),
        sa.Column("video_filename", sa.String(), nullable=False),
        sa.Column("analysis_type", sa.String(), nullable=False),
        sa.Column("total_frames", sa.Integer(), nullable=True),
        sa.Column("frames_with_balls", sa.Integer(), nullable=True),
        sa.Column("total_ball_detections", sa.Integer(), nullable=True),
        sa.Column("average_detections_per_frame", sa.Float(), nullable=True),
        sa.Column("detection_rate", sa.Float(), nullable=True),
        sa.Column("frames_with_pose", sa.Integer(), nullable=True),
        sa.Column("pose_detection_rate", sa.Float(), nullable=True),
        sa.Column("contact_frames", sa.Integer(), nullable=True),
        sa.Column("contact_timestamps", sa.Text(), nullable=True),
        sa.Column("contact_detections", sa.Text(), nullable=True),
        sa.Column("ball_detections", sa.Text(), nullable=True),
        sa.Column("pose_detections", sa.Text(), nullable=True),
        sa.Column("annotated_video_path", sa.String(), nullable=True),
        sa.Column("processing_time", sa.Float(), nullable=True),
        sa.Column("model_used", sa.String(), nullable=True),
        sa.Column("confidence_threshold", sa.Float(), nullable=True),
        sa.Column("confidence_threshold_used", sa.Float(), nullable=True),
        sa.Column("status", sa.String(length=50), nullable=True),
        sa.Column("progress", sa.Integer(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(["video_id"], ["videos.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_analyses_id"), "analyses", ["id"], unique=False)
    op.create_index(
        op.f("ix_analyses_video_id"), "analyses", ["video_id"], unique=False
    )
    op.create_index(
        op.f("ix_analyses_video_filename"), "analyses", ["video_filename"], unique=False
    )
