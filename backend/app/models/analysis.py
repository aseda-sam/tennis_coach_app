"""
Database model for video analysis results.
"""

from sqlalchemy import Column, DateTime, Float, Integer, String, Text
from sqlalchemy.sql import func

from app.core.database import Base


class Analysis(Base):
    """Model for storing video analysis results."""

    __tablename__ = "analyses"

    id = Column(Integer, primary_key=True, index=True)
    video_filename = Column(String, nullable=False, index=True)
    analysis_type = Column(
        String, nullable=False
    )  # 'ball_detection', 'pose_estimation', etc.

    # Analysis results
    total_frames = Column(Integer, default=0)
    frames_with_balls = Column(Integer, default=0)
    total_ball_detections = Column(Integer, default=0)
    average_detections_per_frame = Column(Float, default=0.0)
    detection_rate = Column(Float, default=0.0)

    # Raw detection data (JSON)
    ball_detections = Column(Text, nullable=True)  # JSON string of detections

    # Processing metadata
    processing_time = Column(Float, default=0.0)  # seconds
    model_used = Column(String, nullable=True)  # 'yolov8n', etc.
    confidence_threshold = Column(Float, default=0.5)

    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    def __repr__(self) -> str:
        return f"<Analysis(id={self.id}, video={self.video_filename}, type={self.analysis_type})>"
