from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import (
    Boolean,
    DateTime,
    Float,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    text,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base

if TYPE_CHECKING:
    from app.models.ball_detection import BallDetection
    from app.models.pose_detection import PoseDetection
    from app.models.serve_window import ServeWindow
    from app.models.video_job import VideoJob


class Video(Base):
    """Video model for storing video metadata."""

    __tablename__ = "videos"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    filename: Mapped[str] = mapped_column(String(255), unique=True, index=True)
    file_path: Mapped[str] = mapped_column(String(500))
    file_size: Mapped[int] = mapped_column(Integer)
    content_type: Mapped[str | None] = mapped_column(String(100))

    # Video metadata
    duration: Mapped[float | None] = mapped_column(Float)  # seconds
    fps: Mapped[float | None] = mapped_column(Float)
    width: Mapped[int | None] = mapped_column(Integer)
    height: Mapped[int | None] = mapped_column(Integer)
    frame_count: Mapped[int | None] = mapped_column(Integer)

    # Timestamps
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=datetime.utcnow
    )
    updated_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), onupdate=datetime.utcnow
    )

    # Processing status
    status: Mapped[str] = mapped_column(String(50), default="uploaded")
    # uploaded, processing, completed, failed
    error_message: Mapped[str | None] = mapped_column(Text)

    # Authentication - user who owns this video
    user_id: Mapped[str] = mapped_column(String(36), index=True)  # UUID as string

    # Demo video flag
    is_demo: Mapped[bool] = mapped_column(
        Boolean, server_default=text("false"), index=True
    )
    # Active demo flag (only one video should have this set to True at a time)
    is_active_demo: Mapped[bool] = mapped_column(
        Boolean, server_default=text("false"), index=True
    )
    # Original user_id before promotion to demo (for unpromote/restore)
    original_user_id: Mapped[str | None] = mapped_column(String(36))

    # Session metadata (serve-focused)
    session_type: Mapped[str | None] = mapped_column(String(20))
    # 'serve_practice', 'match', 'other'
    camera_angle: Mapped[str | None] = mapped_column(
        String(20)
    )  # 'behind', 'profile', 'unknown'
    title: Mapped[str | None] = mapped_column(String(200))  # user-defined label
    notes: Mapped[str | None] = mapped_column(Text)  # free-form session memo
    recorded_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    # When video was recorded (for trends)
    recorded_at_source: Mapped[str | None] = mapped_column(String(20))
    # 'metadata', 'client', 'upload_time'

    # Default player attribution for serves created from this video
    primary_player_id: Mapped[int | None] = mapped_column(
        Integer,
        ForeignKey("players.id", ondelete="SET NULL"),
        index=True,
    )

    # Transcoding metadata
    is_transcoded: Mapped[bool] = mapped_column(Boolean, server_default=text("false"))
    original_file_size: Mapped[int | None] = mapped_column(Integer)
    # File size before transcoding

    # New granular analysis relationships
    pose_detections: Mapped[list["PoseDetection"]] = relationship(  # type: ignore[name-defined]
        "PoseDetection", back_populates="video", cascade="all, delete-orphan"
    )
    ball_detections: Mapped[list["BallDetection"]] = relationship(  # type: ignore[name-defined]
        "BallDetection", back_populates="video", cascade="all, delete-orphan"
    )
    serve_windows: Mapped[list["ServeWindow"]] = relationship(  # type: ignore[name-defined]
        "ServeWindow", back_populates="video", cascade="all, delete-orphan"
    )
    jobs: Mapped[list["VideoJob"]] = relationship(  # type: ignore[name-defined]
        "VideoJob", back_populates="video", cascade="all, delete-orphan"
    )

    __table_args__ = (
        Index("ix_videos_recorded_at", "recorded_at"),
        Index("ix_videos_user_recorded_at", "user_id", "recorded_at"),
    )
