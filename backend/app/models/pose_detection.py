"""
Pose detection model for storing MediaPipe pose detection results.
"""

from sqlalchemy import Column, DateTime, Float, ForeignKey, Integer, String, Text, func
from sqlalchemy.orm import relationship

from app.core.database import Base


class PoseDetection(Base):
    """Model for storing pose detection analysis results."""

    __tablename__ = "pose_detections"

    id = Column(Integer, primary_key=True, index=True)
    video_id = Column(
        Integer, ForeignKey("videos.id", ondelete="CASCADE"), index=True, nullable=False
    )

    # Processing metadata
    total_frames = Column(Integer, nullable=False)
    frames_with_poses = Column(Integer, default=0)
    total_pose_detections = Column(Integer, default=0)
    detection_rate = Column(Float, default=0.0)  # percentage of frames with poses

    # Pose quality metrics
    average_pose_confidence = Column(Float, nullable=True)
    min_pose_confidence = Column(Float, nullable=True)
    max_pose_confidence = Column(Float, nullable=True)
    pose_stability_score = Column(Float, nullable=True)  # consistency across frames

    # MediaPipe configuration
    confidence_threshold = Column(Float, nullable=False, default=0.5)
    detection_threshold = Column(Float, nullable=False, default=0.5)

    # Pose detection data (JSON serialized)
    pose_data = Column(Text, nullable=True)  # Full pose keypoints per frame
    visibility_scores = Column(Text, nullable=True)  # Visibility scores per keypoint
    confidence_scores = Column(Text, nullable=True)  # Confidence scores per frame

    # Annotated video path
    annotated_video_path = Column(String, nullable=True)  # Path to annotated video

    # Performance metrics
    processing_time_seconds = Column(Float, nullable=False)
    frame_processing_rate = Column(Float, nullable=True)  # frames per second

    # Status tracking
    status = Column(String(50), default="completed", nullable=False)
    error_message = Column(Text, nullable=True)

    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    completed_at = Column(DateTime(timezone=True), nullable=True)

    # Relationships
    video = relationship("Video", back_populates="pose_detections")
    video_annotations = relationship("VideoAnnotation", back_populates="pose_detection")

    def __repr__(self) -> str:
        """String representation of pose detection record."""
        return (
            f"<PoseDetection(id={self.id}, video_id={self.video_id}, "
            f"frames_with_poses={self.frames_with_poses}, "
            f"status={self.status})>"
        )
