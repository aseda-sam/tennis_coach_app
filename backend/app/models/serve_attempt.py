"""Serve attempt model for storing serve-specific analysis data."""

from datetime import datetime

from sqlalchemy import Column, DateTime, Float, ForeignKey, Integer, String, Index
from sqlalchemy.orm import relationship

from app.core.database import Base


class ServeAttempt(Base):
    """One row = one serve attempt with all key metrics."""

    __tablename__ = "serve_attempts"

    id = Column(Integer, primary_key=True, index=True)
    video_id = Column(Integer, ForeignKey("videos.id", ondelete="CASCADE"), nullable=False, index=True)
    user_id = Column(String(36), nullable=False, index=True)  # Auth/tenancy boundary
    player_id = Column(Integer, ForeignKey("players.id", ondelete="SET NULL"), nullable=False, index=True)  # Domain identity - REQUIRED for MVP

    # Timing - manually tagged
    start_timestamp = Column(Float, nullable=False)  # When serve attempt starts
    end_timestamp = Column(Float, nullable=False)  # When serve attempt ends
    contact_timestamp = Column(Float, nullable=True)  # Optional - may not make contact

    # Metrics - calculated from pose data
    elbow_angle_at_contact = Column(Float, nullable=True)  # Calculated if contact_timestamp exists

    # Context
    court_side = Column(String(10), nullable=True)  # 'deuce', 'ad'
    serve_number = Column(Integer, nullable=True)  # 1, 2
    serve_subtype = Column(String(20), nullable=True)  # 'flat', 'slice', 'kick'

    # Outcome
    in_out = Column(String(20), nullable=True)  # 'in', 'out_long', 'out_wide', 'net', 'unknown'

    # Timestamps
    created_at = Column(DateTime(timezone=True), default=datetime.utcnow)

    # Relationships
    video = relationship("Video", back_populates="serve_attempts")
    player = relationship("Player", back_populates="serve_attempts")

    # Indexes for common query patterns
    __table_args__ = (
        Index("ix_serve_attempts_user_created", "user_id", "created_at"),
        Index("ix_serve_attempts_player_created", "player_id", "created_at"),  # Primary trend index
        Index("ix_serve_attempts_user_player_created", "user_id", "player_id", "created_at"),
        Index("ix_serve_attempts_user_court_created", "user_id", "court_side", "created_at"),
        Index("ix_serve_attempts_video_start", "video_id", "start_timestamp"),
    )

    def __repr__(self) -> str:
        """String representation of serve attempt."""
        return (
            f"<ServeAttempt(id={self.id}, video_id={self.video_id}, "
            f"player_id={self.player_id}, start={self.start_timestamp:.2f}s, "
            f"elbow_angle={self.elbow_angle_at_contact})>"
        )
