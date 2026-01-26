"""drop_video_annotations_table

Revision ID: f2f8e3a9b1c7
Revises: e585518be299
Create Date: 2026-01-25 15:12:00.000000

"""

from typing import Sequence, Union

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "f2f8e3a9b1c7"
down_revision: Union[str, Sequence[str], None] = "e585518be299"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def _table_exists(table_name: str) -> bool:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    return table_name in inspector.get_table_names()


def _index_exists(table_name: str, index_name: str) -> bool:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    return any(
        index["name"] == index_name for index in inspector.get_indexes(table_name)
    )


def upgrade() -> None:
    """Upgrade schema."""
    if not _table_exists("video_annotations"):
        return

    if _index_exists("video_annotations", op.f("ix_video_annotations_video_id")):
        op.drop_index(
            op.f("ix_video_annotations_video_id"), table_name="video_annotations"
        )
    if _index_exists("video_annotations", op.f("ix_video_annotations_id")):
        op.drop_index(op.f("ix_video_annotations_id"), table_name="video_annotations")

    op.drop_table("video_annotations")


def downgrade() -> None:
    """Downgrade schema."""
    op.create_table(
        "video_annotations",
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
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(["pose_detection_id"], ["pose_detections.id"]),
        sa.ForeignKeyConstraint(["video_id"], ["videos.id"], ondelete="CASCADE"),
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
