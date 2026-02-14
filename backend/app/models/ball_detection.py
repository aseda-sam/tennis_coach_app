"""
Ball detection model for storing YOLO tennis ball detection results.
"""

from datetime import datetime

from sqlalchemy import Column, DateTime, Float, ForeignKey, Integer, String, Text
from sqlalchemy.orm import relationship

from app.core.database import Base


class BallDetection(Base):
    """Model for storing ball detection analysis results (per-video, serve windows)."""

    __tablename__ = "ball_detections"

    id = Column(Integer, primary_key=True, index=True)
    video_id = Column(
        Integer,
        ForeignKey("videos.id", ondelete="CASCADE"),
        index=True,
        nullable=False,
    )

    # Processing metadata
    total_frames = Column(Integer, nullable=False)
    frames_with_ball = Column(Integer, default=0)
    detection_rate = Column(Float, default=0.0)

    # Ball detection data (JSON): list of {frame_index, timestamp_ms, ball_x?, ball_y?, confidence?}
    ball_data = Column(Text, nullable=True)

    # Performance
    processing_time_seconds = Column(Float, nullable=False)
    frame_processing_rate = Column(Float, nullable=True)

    # Status
    status = Column(String(50), default="completed", nullable=False)
    error_message = Column(Text, nullable=True)

    # Time windows that were processed (JSON): [{"start_ms": ..., "end_ms": ...}]
    time_windows = Column(Text, nullable=True)

    # Timestamps
    created_at = Column(DateTime(timezone=True), default=datetime.utcnow)
    completed_at = Column(DateTime(timezone=True), nullable=True)

    # Relationships
    video = relationship("Video", back_populates="ball_detections")

    def __repr__(self) -> str:
        return (
            f"<BallDetection(id={self.id}, video_id={self.video_id}, "
            f"frames_with_ball={self.frames_with_ball}, status={self.status})>"
        )
