from datetime import datetime

from sqlalchemy import (
    Column,
    DateTime,
    Float,
    ForeignKey,
    Integer,
    String,
)
from sqlalchemy.orm import relationship

from app.core.database import Base


class BallContact(Base):
    """Model for storing info on frames with ball contact data."""

    __tablename__ = "ball_contacts"

    id = Column(Integer, primary_key=True, index=True)
    frame_number = Column(Integer, nullable=True, index=True)
    video_timestamp = Column(Float, nullable=False)
    contact_hand = Column(String(10), nullable=True)  # 'left' or 'right'
    stroke_type = Column(
        String, nullable=True
    )  # ground_stroke, serve, volley, overhead
    stroke_subtype = Column(
        String, nullable=True
    )  # topspin, backspin, forehand, backhand, flat, slice, lob, drop
    created_at = Column(DateTime(timezone=True), default=datetime.utcnow)
    updated_at = Column(DateTime(timezone=True), onupdate=datetime.utcnow)
    detection_source = Column(
        String(20), nullable=False, default="manual"
    )  # 'automated' or 'manual'

    # Foreign key to video
    video_id = Column(
        Integer, ForeignKey("videos.id", ondelete="CASCADE"), nullable=False, index=True
    )
    video = relationship("Video", back_populates="ball_contacts")
