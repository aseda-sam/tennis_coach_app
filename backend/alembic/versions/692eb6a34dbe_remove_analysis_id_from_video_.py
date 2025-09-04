"""remove_analysis_id_from_video_annotations

Revision ID: 692eb6a34dbe
Revises: b5dff1b26946
Create Date: 2025-09-03 21:52:03.260668

"""

from typing import Sequence, Union

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "692eb6a34dbe"
down_revision: Union[str, Sequence[str], None] = "b5dff1b26946"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    # SQLite doesn't support dropping columns with foreign keys directly
    # We need to recreate the table without the analysis_id column

    # Create new table without analysis_id
    op.create_table(
        "video_annotations_new",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("video_id", sa.Integer(), nullable=False),
        sa.Column("annotation_type", sa.String(length=50), nullable=False),
        sa.Column("annotated_video_path", sa.String(), nullable=False),
        sa.Column("file_size_bytes", sa.Integer(), nullable=True),
        sa.Column("pose_detection_id", sa.Integer(), nullable=True),
        sa.Column("processing_time_seconds", sa.Float(), nullable=False),
        sa.Column("frames_annotated", sa.Integer(), nullable=True),
        sa.Column("annotation_style", sa.String(length=50), nullable=True),
        sa.Column("status", sa.String(length=50), nullable=False),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=True),
        sa.Column("completed_at", sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(
            ["pose_detection_id"],
            ["pose_detections.id"],
        ),
        sa.ForeignKeyConstraint(["video_id"], ["videos.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )

    # Copy data from old table to new table (excluding analysis_id)
    op.execute("""
        INSERT INTO video_annotations_new
        (id, video_id, annotation_type, annotated_video_path, file_size_bytes,
         pose_detection_id, processing_time_seconds, frames_annotated,
         annotation_style, status, error_message, created_at, completed_at)
        SELECT id, video_id, annotation_type, annotated_video_path, file_size_bytes,
               pose_detection_id, processing_time_seconds, frames_annotated,
               annotation_style, status, error_message, created_at, completed_at
        FROM video_annotations
    """)

    # Drop old table
    op.drop_table("video_annotations")

    # Rename new table
    op.rename_table("video_annotations_new", "video_annotations")

    # Recreate indexes
    op.create_index("ix_video_annotations_id", "video_annotations", ["id"])
    op.create_index("ix_video_annotations_video_id", "video_annotations", ["video_id"])


def downgrade() -> None:
    """Downgrade schema."""
    # Add back the analysis_id column (nullable since analyses table no longer exists)
    op.add_column(
        "video_annotations", sa.Column("analysis_id", sa.Integer(), nullable=True)
    )
