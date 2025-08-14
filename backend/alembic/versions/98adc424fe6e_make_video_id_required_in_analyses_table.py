"""Make video_id required in analyses table

Revision ID: 98adc424fe6e
Revises: 54b792e8341e
Create Date: 2025-08-14 22:15:30.123456

"""

from typing import Sequence, Union

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "98adc424fe6e"
down_revision: Union[str, Sequence[str], None] = "54b792e8341e"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Make video_id required in analyses table."""
    # SQLite doesn't support ALTER COLUMN NOT NULL directly
    # We need to recreate the table with the new constraint
    # Since we verified there are no null video_id values, this is safe

    # Create new table with NOT NULL constraint
    op.create_table(
        "analyses_new",
        sa.Column("id", sa.Integer(), primary_key=True, nullable=False),
        sa.Column(
            "video_id",
            sa.Integer(),
            sa.ForeignKey("videos.id", ondelete="CASCADE"),
            nullable=False,
        ),
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

    # Copy data from old table to new table
    op.execute("""
        INSERT INTO analyses_new
        SELECT * FROM analyses
        WHERE video_id IS NOT NULL
    """)

    # Drop old table and rename new table
    op.drop_table("analyses")
    op.rename_table("analyses_new", "analyses")

    # Recreate indexes
    op.create_index("ix_analyses_id", "analyses", ["id"], unique=False)
    op.create_index("ix_analyses_video_id", "analyses", ["video_id"], unique=False)
    op.create_index(
        "ix_analyses_video_filename", "analyses", ["video_filename"], unique=False
    )


def downgrade() -> None:
    """Revert video_id to nullable in analyses table."""
    # Recreate table with nullable video_id
    op.create_table(
        "analyses_old",
        sa.Column("id", sa.Integer(), primary_key=True, nullable=False),
        sa.Column(
            "video_id",
            sa.Integer(),
            sa.ForeignKey("videos.id", ondelete="CASCADE"),
            nullable=True,
        ),
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

    # Copy data back
    op.execute("""
        INSERT INTO analyses_old
        SELECT * FROM analyses
    """)

    # Drop new table and rename old table
    op.drop_table("analyses")
    op.rename_table("analyses_old", "analyses")

    # Recreate indexes
    op.create_index("ix_analyses_id", "analyses", ["id"], unique=False)
    op.create_index("ix_analyses_video_id", "analyses", ["video_id"], unique=False)
    op.create_index(
        "ix_analyses_video_filename", "analyses", ["video_filename"], unique=False
    )
