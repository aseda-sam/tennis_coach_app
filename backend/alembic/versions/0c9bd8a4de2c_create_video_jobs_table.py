"""create_video_jobs_table

Revision ID: 0c9bd8a4de2c
Revises: d30414b42ecb
Create Date: 2026-01-27 19:08:49.741076

"""

from typing import Sequence, Union

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "0c9bd8a4de2c"
down_revision: Union[str, Sequence[str], None] = "d30414b42ecb"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Create video_jobs table for tracking background job status."""
    op.create_table(
        "video_jobs",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("video_id", sa.Integer(), nullable=False),
        sa.Column("user_id", sa.String(36), nullable=False),
        sa.Column("job_type", sa.String(50), nullable=False),
        sa.Column("status", sa.String(20), nullable=False, server_default="queued"),
        sa.Column("error", sa.Text(), nullable=True),
        sa.Column("rq_job_id", sa.String(100), nullable=True),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.func.now()
        ),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("finished_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(
            ["video_id"],
            ["videos.id"],
            ondelete="CASCADE",
        ),
    )

    # Create indexes
    op.create_index(
        "idx_video_jobs_user_status",
        "video_jobs",
        ["user_id", "status"],
    )
    op.create_index("idx_video_jobs_video_id", "video_jobs", ["video_id"])
    op.create_index("idx_video_jobs_rq_job_id", "video_jobs", ["rq_job_id"])


def downgrade() -> None:
    """Drop video_jobs table."""
    op.drop_index("idx_video_jobs_rq_job_id", table_name="video_jobs")
    op.drop_index("idx_video_jobs_video_id", table_name="video_jobs")
    op.drop_index("idx_video_jobs_user_status", table_name="video_jobs")
    op.drop_table("video_jobs")
