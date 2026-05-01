"""Serve biomechanics report model — phase segmentation + raw metrics per serve."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import TYPE_CHECKING, Any

from sqlalchemy import DateTime, ForeignKey, Index, Integer, String, Text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base

if TYPE_CHECKING:
    from app.models.player import Player
    from app.models.serve_window import ServeWindow


class ServeBiomechanicsReport(Base):
    """Computed phase segmentation and biomechanics metrics for a single serve window.

    Stores phases + raw metric values only. No scoring, ratings, or coaching text.
    """

    __tablename__ = "serve_biomechanics_reports"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    serve_window_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("serve_windows.id", ondelete="CASCADE"),
        index=True,
    )
    user_id: Mapped[str] = mapped_column(String(36), index=True)
    player_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("players.id", ondelete="CASCADE"),
    )

    # Structured data
    phase_segmentation_json: Mapped[str | None] = mapped_column(Text)
    metrics: Mapped[dict[str, Any] | None] = mapped_column(JSONB)

    # Version tracking
    analysis_version: Mapped[str] = mapped_column(String(20))

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
    )

    # Relationships
    serve_window: Mapped["ServeWindow"] = relationship(  # type: ignore[name-defined]
        "ServeWindow",
        back_populates="biomechanics_reports",
        passive_deletes=True,
    )
    player: Mapped["Player"] = relationship("Player")  # type: ignore[name-defined]

    __table_args__ = (
        Index("ix_biomechanics_reports_player_created", "player_id", "created_at"),
        Index("ix_biomechanics_reports_user_player", "user_id", "player_id"),
    )
