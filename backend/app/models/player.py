from datetime import datetime

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
    backhand_style = Column(String(20), nullable=False)  # 'one_handed', 'two_handed'
    height = Column(Float, nullable=True)  # in cm
    notes = Column(Text, nullable=True)
    created_at = Column(DateTime(timezone=True), default=datetime.utcnow)
    updated_at = Column(DateTime(timezone=True), onupdate=datetime.utcnow)

    # Relationships
    ball_contacts = relationship("BallContact", back_populates="player")
