import enum

from sqlalchemy import (
    Column,
    DateTime,
    Float,
    ForeignKey,
    Integer,
    String,
)
from sqlalchemy import Enum as SqlEnum
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from app.core.database import Base


class BallContact(Base):
    """Model for storing info on frames with ball contact data."""

    __tablename__ = "ball_contacts"

    class ContactHandEnum(enum.Enum):
        left = "left"
        right = "right"

    id = Column(Integer, primary_key=True, index=True)
    frame_number = Column(Integer, nullable=True, index=True)
    video_timestamp = Column(Float, nullable=True)
    player = Column(Integer, nullable=True)

    contact_hand = Column(
        SqlEnum(ContactHandEnum, name="contact_hand_enum"), nullable=True
    )
    stroke_type = Column(
        String, nullable=True
    )  # ground_stroke, serve, volley, overhead
    stroke_subtype = Column(
        String, nullable=True
    )  # topspin, backspin, forehand, backhand, flat, slice, lob, drop
    confidence = Column(Float, nullable=True)
    ball_position = Column(String, nullable=True)  # JSON: {"x": 0.5, "y": 0.3}
    player_position = Column(String, nullable=True)  # JSON: {"x": 0.5, "y": 0.3}
    description = Column(String, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    detection_source = Column(
        String(20), nullable=False, default="automated"
    )  # 'automated' or 'manual'

    # Questions: Don't understand these columns
    ball_area = Column(Float, nullable=True)
    ball_size_factor = Column(Float, nullable=True)
    racket_data = Column(String, nullable=True)
    ball_bbox = Column(String, nullable=True)
    ball_racket_distance = Column(Float, nullable=True)

    # Foreign key to video
    video_id = Column(
        Integer, ForeignKey("videos.id", ondelete="CASCADE"), nullable=False, index=True
    )
    video = relationship("Video", backref="ball_contacts")
