"""Pose detection model for storing MediaPipe pose detection results."""

from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import DateTime, Float, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base

if TYPE_CHECKING:
    from app.models.video import Video


class PoseDetection(Base):
    """Model for storing pose detection analysis results."""

    __tablename__ = "pose_detections"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    video_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("videos.id", ondelete="CASCADE"), index=True
    )

    # Processing metadata
    total_frames: Mapped[int] = mapped_column(Integer)
    frames_with_poses: Mapped[int] = mapped_column(Integer, default=0)
    total_pose_detections: Mapped[int] = mapped_column(Integer, default=0)
    detection_rate: Mapped[float] = mapped_column(Float, default=0.0)
    # percentage of frames with poses

    # Pose quality metrics
    average_pose_confidence: Mapped[float | None] = mapped_column(Float)
    min_pose_confidence: Mapped[float | None] = mapped_column(Float)
    max_pose_confidence: Mapped[float | None] = mapped_column(Float)
    pose_stability_score: Mapped[float | None] = mapped_column(
        Float
    )  # consistency across frames

    # MediaPipe configuration
    confidence_threshold: Mapped[float] = mapped_column(Float, default=0.5)
    detection_threshold: Mapped[float] = mapped_column(Float, default=0.5)

    # Pose detection data (JSON serialized)
    pose_data: Mapped[str | None] = mapped_column(Text)  # Full pose keypoints per frame
    visibility_scores: Mapped[str | None] = mapped_column(
        Text
    )  # Visibility scores per keypoint
    confidence_scores: Mapped[str | None] = mapped_column(
        Text
    )  # Confidence scores per frame

    # Performance metrics
    processing_time_seconds: Mapped[float] = mapped_column(Float)
    frame_processing_rate: Mapped[float | None] = mapped_column(
        Float
    )  # frames per second

    # Status tracking
    status: Mapped[str] = mapped_column(String(50), default="completed")
    error_message: Mapped[str | None] = mapped_column(Text)

    # Detection mode and windows (for scout/refine pipeline)
    detection_mode: Mapped[str] = mapped_column(String(20), default="full")
    # "scout", "full", "refine"
    time_windows: Mapped[str | None] = mapped_column(Text)
    # JSON: [{"start_ms": ..., "end_ms": ...}]

    # Timestamps
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=datetime.utcnow
    )
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    # Relationships
    video: Mapped["Video"] = relationship("Video", back_populates="pose_detections")  # type: ignore[name-defined]

    def __repr__(self) -> str:
        """String representation of pose detection record."""
        return (
            f"<PoseDetection(id={self.id}, video_id={self.video_id}, "
            f"frames_with_poses={self.frames_with_poses}, "
            f"status={self.status})>"
        )
