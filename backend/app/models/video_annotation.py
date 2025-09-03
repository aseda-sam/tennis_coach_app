"""
Video annotation model for storing annotated video information.
"""

from datetime import datetime

from sqlalchemy import Column, DateTime, Float, ForeignKey, Integer, String, Text
from sqlalchemy.orm import relationship

from app.core.database import Base


class VideoAnnotation(Base):
    """Model for storing video annotation information."""

    __tablename__ = "video_annotations"

    id = Column(Integer, primary_key=True, index=True)
    video_id = Column(
        Integer, ForeignKey("videos.id", ondelete="CASCADE"), index=True, nullable=False
    )

    # Annotation metadata
    annotation_type = Column(
        String(50), nullable=False
    )  # 'pose_only', 'ball_only', 'comprehensive', etc.
    annotated_video_path = Column(
        String, nullable=False
    )  # Path to annotated video file
    file_size_bytes = Column(Integer, nullable=True)  # Size of annotated video file

    # Source analysis references (optional - for tracking which analyses contributed)
    pose_detection_id = Column(Integer, ForeignKey("pose_detections.id"), nullable=True)
    # ball_detection_id = Column(Integer, ForeignKey("ball_detections.id"), nullable=True)
    # Future: when ball_detections table exists
    analysis_id = Column(
        Integer, ForeignKey("analyses.id"), nullable=True
    )  # Legacy analysis reference

    # Processing metadata
    processing_time_seconds = Column(Float, nullable=False)
    frames_annotated = Column(Integer, nullable=True)
    annotation_style = Column(
        String(50), default="standard"
    )  # 'standard', 'debug', 'presentation'

    # Status tracking
    status = Column(String(50), default="completed", nullable=False)
    error_message = Column(Text, nullable=True)

    # Timestamps
    created_at = Column(DateTime(timezone=True), default=datetime.utcnow)
    completed_at = Column(DateTime(timezone=True), nullable=True)

    # Relationships
    video = relationship("Video", back_populates="video_annotations")
    pose_detection = relationship("PoseDetection", back_populates="video_annotations")
    # ball_detection = relationship("BallDetection", back_populates="video_annotations")
    # Future
    # analysis = relationship("Analysis", back_populates="video_annotations")  # Legacy

    def __repr__(self) -> str:
        """String representation of video annotation record."""
        return (
            f"<VideoAnnotation(id={self.id}, video_id={self.video_id}, "
            f"annotation_type={self.annotation_type}, "
            f"status={self.status})>"
        )
