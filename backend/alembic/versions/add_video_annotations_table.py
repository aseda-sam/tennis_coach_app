"""Add video_annotations table

Revision ID: add_video_annotations
Revises: 16806dadaede
Create Date: 2025-09-03 08:12:47

"""

from typing import Sequence, Union

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "add_video_annotations"
down_revision: Union[str, Sequence[str], None] = "16806dadaede"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    # Create video_annotations table
    op.create_table(
        "video_annotations",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("video_id", sa.Integer(), nullable=False),
        sa.Column("annotation_type", sa.String(length=50), nullable=False),
        sa.Column("annotated_video_path", sa.String(), nullable=False),
        sa.Column("file_size_bytes", sa.Integer(), nullable=True),
        sa.Column("pose_detection_id", sa.Integer(), nullable=True),
        sa.Column("analysis_id", sa.Integer(), nullable=True),
        sa.Column("processing_time_seconds", sa.Float(), nullable=False),
        sa.Column("frames_annotated", sa.Integer(), nullable=True),
        sa.Column("annotation_style", sa.String(length=50), nullable=True),
        sa.Column("status", sa.String(length=50), nullable=False),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("(CURRENT_TIMESTAMP)"),
            nullable=True,
        ),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(["video_id"], ["videos.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(
            ["pose_detection_id"],
            ["pose_detections.id"],
        ),
        sa.ForeignKeyConstraint(
            ["analysis_id"],
            ["analyses.id"],
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        op.f("ix_video_annotations_id"), "video_annotations", ["id"], unique=False
    )
    op.create_index(
        op.f("ix_video_annotations_video_id"),
        "video_annotations",
        ["video_id"],
        unique=False,
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_index(op.f("ix_video_annotations_video_id"), table_name="video_annotations")
    op.drop_index(op.f("ix_video_annotations_id"), table_name="video_annotations")
    op.drop_table("video_annotations")
