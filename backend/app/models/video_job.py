"""VideoJob model for tracking background job status."""

import uuid
from datetime import datetime

from sqlalchemy import Column, DateTime, ForeignKey, Index, Integer, String, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship

from app.core.database import Base


class VideoJob(Base):
    """Track background job status in database instead of Redis polling.

    Jobs are created at enqueue time (status='queued'), updated by worker
    on start (status='processing') and completion (status='completed'/'failed').
    """

    __tablename__ = "video_jobs"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    video_id = Column(
        Integer, ForeignKey("videos.id", ondelete="CASCADE"), nullable=False
    )
    user_id = Column(
        String(36), nullable=False
    )  # UUID as string (matches Video.user_id)
    job_type = Column(
        String(50), nullable=False
    )  # pose_detection, serve_analysis, transcode
    status = Column(String(20), nullable=False, default="queued")
    error = Column(Text, nullable=True)
    rq_job_id = Column(String(100), nullable=True)  # For debugging correlation
    stage = Column(
        String(50), nullable=True
    )  # "transcoding", "scout", "detecting_serves", "refining", "complete"
    progress_percent = Column(Integer, default=0, nullable=False)
    serve_windows_found = Column(
        Integer, nullable=True
    )  # Number of serve windows found (after scout pass)
    created_at = Column(DateTime(timezone=True), default=datetime.utcnow)
    started_at = Column(DateTime(timezone=True), nullable=True)
    finished_at = Column(DateTime(timezone=True), nullable=True)

    # Relationship
    video = relationship("Video", back_populates="jobs")

    __table_args__ = (
        Index("idx_video_jobs_user_status", "user_id", "status"),
        Index("idx_video_jobs_user_created", "user_id", "created_at"),
        Index("idx_video_jobs_video_id", "video_id"),
        Index("idx_video_jobs_rq_job_id", "rq_job_id"),
    )
