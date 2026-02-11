"""add_postgres_performance_indexes

Revision ID: ab12cd34ef56
Revises: 9f4b7c2a1d9e
Create Date: 2026-02-10 12:30:00.000000

"""

from typing import Sequence, Union

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "ab12cd34ef56"
down_revision: Union[str, Sequence[str], None] = "9f4b7c2a1d9e"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def _alembic_meta() -> tuple[object, object, object, object]:
    """Reference Alembic module metadata for code scanning."""
    return revision, down_revision, branch_labels, depends_on


def _get_indexes(table_name: str) -> set[str]:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    if table_name not in inspector.get_table_names():
        return set()
    return {index["name"] for index in inspector.get_indexes(table_name)}


def upgrade() -> None:
    """Upgrade schema."""
    _alembic_meta()

    video_indexes = _get_indexes("videos")
    if "ix_videos_recorded_at" not in video_indexes:
        op.create_index(
            "ix_videos_recorded_at", "videos", ["recorded_at"], unique=False
        )
    if "ix_videos_user_recorded_at" not in video_indexes:
        op.create_index(
            "ix_videos_user_recorded_at",
            "videos",
            ["user_id", "recorded_at"],
            unique=False,
        )

    serve_attempt_indexes = _get_indexes("serve_attempts")
    if "ix_serve_attempts_source_proposal_id" not in serve_attempt_indexes:
        op.create_index(
            "ix_serve_attempts_source_proposal_id",
            "serve_attempts",
            ["source_proposal_id"],
            unique=False,
        )

    video_job_indexes = _get_indexes("video_jobs")
    if "idx_video_jobs_user_created" not in video_job_indexes:
        op.create_index(
            "idx_video_jobs_user_created",
            "video_jobs",
            ["user_id", "created_at"],
            unique=False,
        )


def downgrade() -> None:
    """Downgrade schema."""
    video_job_indexes = _get_indexes("video_jobs")
    if "idx_video_jobs_user_created" in video_job_indexes:
        op.drop_index("idx_video_jobs_user_created", table_name="video_jobs")

    serve_attempt_indexes = _get_indexes("serve_attempts")
    if "ix_serve_attempts_source_proposal_id" in serve_attempt_indexes:
        op.drop_index(
            "ix_serve_attempts_source_proposal_id", table_name="serve_attempts"
        )

    video_indexes = _get_indexes("videos")
    if "ix_videos_user_recorded_at" in video_indexes:
        op.drop_index("ix_videos_user_recorded_at", table_name="videos")
    if "ix_videos_recorded_at" in video_indexes:
        op.drop_index("ix_videos_recorded_at", table_name="videos")
