from datetime import datetime, timezone

from sqlalchemy import Column, DateTime, Float, Integer, String, Text
from sqlalchemy.orm import relationship

from app.core.database import Base


class Player(Base):
    """Model for storing player information."""

    __tablename__ = "players"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(100), nullable=False, index=True)
    dominant_hand = Column(
        String(10), nullable=False
    )  # 'left', 'right' - the hand typically used for hitting
    backhand_style = Column(String(20), nullable=True)  # 'one_handed', 'two_handed'
    height = Column(Float, nullable=True)  # in cm
    notes = Column(Text, nullable=True)
    created_at = Column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )
    updated_at = Column(
        DateTime(timezone=True), onupdate=lambda: datetime.now(timezone.utc)
    )

    # Authentication - user who owns this player
    user_id = Column(String(36), nullable=False, index=True)  # UUID as string

    # Relationships
    ball_contacts = relationship("BallContact", back_populates="player")
    video_appearances = relationship("VideoPlayer", back_populates="player")
    serve_attempts = relationship("ServeAttempt", back_populates="player")

    # Convenience properties
    @property
    def videos(self) -> list:
        """Get list of videos where this player appears."""
        return [vp.video for vp in self.video_appearances]

    @property
    def total_videos(self) -> int:
        """Get total number of videos where this player appears."""
        return len(self.video_appearances)
