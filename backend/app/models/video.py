from sqlalchemy import Column, DateTime, Float, Integer, String, Text
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from app.core.database import Base


class Video(Base):
    """Video model for storing video metadata."""

    __tablename__ = "videos"

    id = Column(Integer, primary_key=True, index=True)
    filename = Column(String(255), unique=True, index=True, nullable=False)
    file_path = Column(String(500), nullable=False)
    file_size = Column(Integer, nullable=False)
    content_type = Column(String(100), nullable=True)

    # Video metadata
    duration = Column(Float, nullable=True)  # seconds
    fps = Column(Float, nullable=True)
    width = Column(Integer, nullable=True)
    height = Column(Integer, nullable=True)
    frame_count = Column(Integer, nullable=True)

    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    # Processing status
    status = Column(
        String(50), default="uploaded"
    )  # uploaded, processing, completed, failed
    error_message = Column(Text, nullable=True)

    # Quality metrics (assessed once on upload)
    quality_score = Column(Float, nullable=True)
    blur_score = Column(Float, nullable=True)
    lighting_score = Column(Float, nullable=True)
    resolution_score = Column(Float, nullable=True)
    quality_level = Column(
        String(20), nullable=True
    )  # 'excellent', 'good', 'fair', 'poor'
    quality_assessed_at = Column(DateTime(timezone=True), nullable=True)

    # Relationship to analyses with cascade deletion
    analyses = relationship(
        "Analysis", backref="video", cascade="all, delete-orphan", lazy="dynamic"
    )

    # New granular analysis relationships
    ball_detections = relationship(
        "BallDetection", back_populates="video", cascade="all, delete-orphan"
    )
    pose_detections = relationship(
        "PoseDetection", back_populates="video", cascade="all, delete-orphan"
    )
    ball_contacts = relationship(
        "BallContact", back_populates="video", cascade="all, delete-orphan"
    )
    video_annotations = relationship(
        "VideoAnnotation", back_populates="video", cascade="all, delete-orphan"
    )
