"""
VideoPlayer model for associating players with specific videos.
"""

from datetime import datetime, timezone

from sqlalchemy import Column, DateTime, ForeignKey, Integer, UniqueConstraint
from sqlalchemy.orm import relationship

from app.core.database import Base


class VideoPlayer(Base):
    """Junction table for players appearing in specific videos."""

    __tablename__ = "video_players"

    id = Column(Integer, primary_key=True, index=True)
    video_id = Column(
        Integer, ForeignKey("videos.id", ondelete="CASCADE"), nullable=False, index=True
    )
    player_id = Column(
        Integer,
        ForeignKey("players.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    pose_detection_id = Column(
        Integer, ForeignKey("pose_detections.id"), nullable=True, index=True
    )
    created_at = Column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )

    # Relationships
    video = relationship("Video", back_populates="video_players")
    player = relationship("Player", back_populates="video_appearances")
    pose_detection = relationship("PoseDetection", back_populates="video_player")

    # Prevent duplicate associations
    __table_args__ = (
        UniqueConstraint("video_id", "player_id", name="uq_video_player"),
    )

    def __repr__(self) -> str:
        """String representation of video player association."""
        return (
            f"<VideoPlayer(id={self.id}, video_id={self.video_id}, "
            f"player_id={self.player_id}, pose_detection_id={self.pose_detection_id})>"
        )
