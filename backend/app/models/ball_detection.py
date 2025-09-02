"""
Database model for ball detection results.
"""

from sqlalchemy import Column, DateTime, Float, ForeignKey, Integer, String, Text
from sqlalchemy.sql import func

from app.core.database import Base


class BallDetection(Base):
    """Model for storing ball detection results."""

    __tablename__ = "ball_detections"

    id = Column(Integer, primary_key=True, index=True)
    video_id = Column(
        Integer, ForeignKey("videos.id", ondelete="CASCADE"), index=True, nullable=False
    )

    # Detection metadata
    total_frames = Column(Integer, nullable=False)
    frames_with_balls = Column(Integer, default=0)
    total_ball_detections = Column(Integer, default=0)
    average_detections_per_frame = Column(Float, default=0.0)
    detection_rate = Column(Float, default=0.0)

    # YOLO model information
    model_used = Column(String, nullable=False)  # 'yolov8n', 'yolov8s', etc.
    confidence_threshold = Column(Float, nullable=False, default=0.5)
    model_selection_reason = Column(
        String, nullable=True
    )  # e.g., "Quality-based selection: good quality"

    # Raw detection data (JSON format)
    detection_data = Column(Text, nullable=True)  # JSON string of all detections
    confidence_scores = Column(
        Text, nullable=True
    )  # JSON string of confidence statistics

    # Processing metadata
    processing_time_seconds = Column(Float, nullable=False)
    frame_processing_rate = Column(
        Float, nullable=True
    )  # frames per second during processing

    # Quality metrics
    average_confidence = Column(Float, nullable=True)
    min_confidence = Column(Float, nullable=True)
    max_confidence = Column(Float, nullable=True)

    # Processing status
    status = Column(
        String(50), default="completed", nullable=False
    )  # processing, completed, failed
    error_message = Column(Text, nullable=True)

    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    completed_at = Column(DateTime(timezone=True), nullable=True)

    def __repr__(self) -> str:
        return f"<BallDetection(id={self.id}, video_id={self.video_id}, model={self.model_used}, detection_rate={self.detection_rate:.2f})>"
