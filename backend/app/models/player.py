from __future__ import annotations

from datetime import datetime, timezone
from typing import TYPE_CHECKING

from sqlalchemy import Boolean, DateTime, Float, Integer, String, Text, text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base

if TYPE_CHECKING:
    from app.models.serve_window import ServeWindow


class Player(Base):
    """Model for storing player information."""

    __tablename__ = "players"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    name: Mapped[str] = mapped_column(String(100), index=True)
    dominant_hand: Mapped[str] = mapped_column(String(10))
    # 'left', 'right' - the hand typically used for hitting
    backhand_style: Mapped[str | None] = mapped_column(
        String(20)
    )  # 'one_handed', 'two_handed'
    height_cm: Mapped[float | None] = mapped_column(
        Float
    )  # Player height in centimeters
    age_group: Mapped[str | None] = mapped_column(
        String(20)
    )  # 'under_13', '13_to_17', etc.
    gender: Mapped[str | None] = mapped_column(
        String(30)
    )  # 'female', 'male', 'non_binary', etc.
    notes: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )
    updated_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), onupdate=lambda: datetime.now(timezone.utc)
    )

    # Authentication - user who owns this player
    user_id: Mapped[str] = mapped_column(String(36), index=True)  # UUID as string

    # True for the player representing the account owner themselves.
    # Exactly one player per user should have this set; identity must come
    # from this flag, never from creation order.
    is_self: Mapped[bool] = mapped_column(Boolean, server_default=text("false"))

    # Relationships
    serve_windows: Mapped[list["ServeWindow"]] = relationship(  # type: ignore[name-defined]
        "ServeWindow", back_populates="player"
    )
