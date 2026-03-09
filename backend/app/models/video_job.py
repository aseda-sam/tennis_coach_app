"""VideoJob model for tracking background job status."""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import DateTime, ForeignKey, Index, Integer, String, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base

if TYPE_CHECKING:
    from app.models.video import Video


class VideoJob(Base):
    """Track background job status in database instead of Redis polling.

    Jobs are created at enqueue time (status='queued'), updated by worker
    on start (status='processing') and completion (status='completed'/'failed').
    """

    __tablename__ = "video_jobs"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    video_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("videos.id", ondelete="CASCADE")
    )
    user_id: Mapped[str] = mapped_column(
        String(36)
    )  # UUID as string (matches Video.user_id)
    job_type: Mapped[str] = mapped_column(
        String(50)
    )  # pose_detection, serve_analysis, transcode
    status: Mapped[str] = mapped_column(String(20), default="queued")
    error: Mapped[str | None] = mapped_column(Text)
    rq_job_id: Mapped[str | None] = mapped_column(
        String(100)
    )  # For debugging correlation
    stage: Mapped[str | None] = mapped_column(String(50))
    # "transcoding", "scout", "detecting_serves", "refining", "complete"
    progress_percent: Mapped[int] = mapped_column(Integer, default=0)
    serve_windows_found: Mapped[int | None] = mapped_column(Integer)
    # Number of serve windows found (after scout pass)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=datetime.utcnow
    )
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    finished_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    # Relationship
    video: Mapped["Video"] = relationship("Video", back_populates="jobs")  # type: ignore[name-defined]

    __table_args__ = (
        Index("idx_video_jobs_user_status", "user_id", "status"),
        Index("idx_video_jobs_user_created", "user_id", "created_at"),
        Index("idx_video_jobs_video_id", "video_id"),
        Index("idx_video_jobs_rq_job_id", "rq_job_id"),
    )
