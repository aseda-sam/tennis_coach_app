"""Ball detection model for storing YOLO tennis ball detection results."""

from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import DateTime, Float, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base

if TYPE_CHECKING:
    from app.models.video import Video


class BallDetection(Base):
    """Model for storing ball detection analysis results (per-video, serve windows)."""

    __tablename__ = "ball_detections"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    video_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("videos.id", ondelete="CASCADE"),
        index=True,
    )

    # Processing metadata
    total_frames: Mapped[int] = mapped_column(Integer)
    frames_with_ball: Mapped[int] = mapped_column(Integer, default=0)
    detection_rate: Mapped[float] = mapped_column(Float, default=0.0)

    # Ball detection data (JSON): list of {frame_index, timestamp_ms, ball_x?, ball_y?, confidence?}
    ball_data: Mapped[str | None] = mapped_column(Text)

    # Performance
    processing_time_seconds: Mapped[float] = mapped_column(Float)
    frame_processing_rate: Mapped[float | None] = mapped_column(Float)

    # Status
    status: Mapped[str] = mapped_column(String(50), default="completed")
    error_message: Mapped[str | None] = mapped_column(Text)

    # Time windows that were processed (JSON): [{"start_ms": ..., "end_ms": ...}]
    time_windows: Mapped[str | None] = mapped_column(Text)

    # Timestamps
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=datetime.utcnow
    )
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    # Relationships
    video: Mapped["Video"] = relationship("Video", back_populates="ball_detections")  # type: ignore[name-defined]

    def __repr__(self) -> str:
        return (
            f"<BallDetection(id={self.id}, video_id={self.video_id}, "
            f"frames_with_ball={self.frames_with_ball}, status={self.status})>"
        )
