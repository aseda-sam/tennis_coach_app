"""
Database model for video analysis results.
"""

from sqlalchemy import Column, DateTime, Float, ForeignKey, Integer, String, Text
from sqlalchemy.sql import func

from app.core.database import Base


class Analysis(Base):
    """Model for storing video analysis results."""

    __tablename__ = "analyses"

    id = Column(Integer, primary_key=True, index=True)
    # Updated foreign key with cascade deletion - now required to match frontend
    video_id = Column(
        Integer, ForeignKey("videos.id", ondelete="CASCADE"), index=True, nullable=False
    )
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

    # Pose detection results
    frames_with_pose = Column(Integer, default=0)
    pose_detection_rate = Column(Float, default=0.0)

    # Raw detection data (JSON)
    ball_detections = Column(Text, nullable=True)  # JSON string of detections
    pose_detections = Column(Text, nullable=True)  # JSON string of pose keypoints
    annotated_video_path = Column(String, nullable=True)  # Path to annotated video

    # Processing metadata
    processing_time = Column(Float, default=0.0)  # seconds
    model_used = Column(String, nullable=True)  # 'yolov8n', etc.
    confidence_threshold = Column(Float, default=0.5)

    # Video quality metrics
    quality_score = Column(Float, nullable=True)
    blur_score = Column(Float, nullable=True)
    lighting_score = Column(Float, nullable=True)
    resolution_score = Column(Float, nullable=True)
    quality_level = Column(
        String(20), nullable=True
    )  # 'excellent', 'good', 'fair', 'poor'
    confidence_threshold_used = Column(
        Float, nullable=True
    )  # Actual threshold used after adaptation

    # Processing status (processing, completed, failed)
    status = Column(String(50), default="completed")

    # Progress tracking (0-100)
    progress = Column(Integer, default=0)

    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    completed_at = Column(DateTime(timezone=True), nullable=True)

    def __repr__(self) -> str:
        return f"<Analysis(id={self.id}, video={self.video_filename}, type={self.analysis_type})>"
