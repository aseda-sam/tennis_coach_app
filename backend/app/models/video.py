from datetime import datetime

from sqlalchemy import Boolean, Column, DateTime, Float, Integer, String, Text, text
from sqlalchemy.orm import relationship

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
    created_at = Column(DateTime(timezone=True), default=datetime.utcnow)
    updated_at = Column(DateTime(timezone=True), onupdate=datetime.utcnow)

    # Processing status
    status = Column(
        String(50), default="uploaded"
    )  # uploaded, processing, completed, failed
    error_message = Column(Text, nullable=True)

    # Authentication - user who owns this video
    user_id = Column(String(36), nullable=False, index=True)  # UUID as string

    # Demo video flag
    is_demo = Column(Boolean, nullable=False, server_default=text("false"), index=True)
    # Active demo flag (only one video should have this set to True at a time)
    is_active_demo = Column(
        Boolean, nullable=False, server_default=text("false"), index=True
    )
    # Original user_id before promotion to demo (for unpromote/restore)
    original_user_id = Column(String(36), nullable=True)

    # Session metadata (serve-focused)
    session_type = Column(
        String(20), nullable=True
    )  # 'serve_practice', 'match', 'other'
    camera_angle = Column(
        String(20), nullable=True
    )  # 'behind', 'profile', 'diagonal', 'unknown'
    recorded_at = Column(
        DateTime(timezone=True), nullable=True
    )  # When video was recorded (for trends)

    # Transcoding metadata
    is_transcoded = Column(Boolean, nullable=False, server_default=text("false"))
    original_file_size = Column(Integer, nullable=True)  # File size before transcoding

    # New granular analysis relationships
    pose_detections = relationship(
        "PoseDetection", back_populates="video", cascade="all, delete-orphan"
    )
    serve_attempts = relationship(
        "ServeAttempt", back_populates="video", cascade="all, delete-orphan"
    )
    serve_window_proposals = relationship(
        "ServeWindowProposal", back_populates="video", cascade="all, delete-orphan"
    )
    jobs = relationship(
        "VideoJob", back_populates="video", cascade="all, delete-orphan"
    )
