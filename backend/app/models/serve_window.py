"""Serve window model for storing tagged or auto-detected serve windows."""

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
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base

if TYPE_CHECKING:
    from app.models.player import Player
    from app.models.serve_biomechanics_report import ServeBiomechanicsReport
    from app.models.video import Video


class ServeWindow(Base):
    """One row = one serve window (manual or auto-detected)."""

    __tablename__ = "serve_windows"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    video_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("videos.id", ondelete="CASCADE"), index=True
    )
    user_id: Mapped[str] = mapped_column(
        String(36), index=True
    )  # Auth/tenancy boundary
    player_id: Mapped[int | None] = mapped_column(
        Integer,
        ForeignKey("players.id", ondelete="CASCADE"),
        index=True,
    )  # Nullable while pending auto-detected proposals are unassigned

    # Timing - manually tagged
    start_timestamp: Mapped[float] = mapped_column(Float)  # When serve window starts
    end_timestamp: Mapped[float] = mapped_column(Float)  # When serve window ends
    contact_timestamp: Mapped[float | None] = mapped_column(
        Float
    )  # Optional - may not make contact

    # Context
    court_side: Mapped[str | None] = mapped_column(String(10))  # 'deuce', 'ad'
    serve_number: Mapped[int | None] = mapped_column(Integer)  # 1, 2
    serve_subtype: Mapped[str | None] = mapped_column(
        String(20)
    )  # 'flat', 'slice', 'kick'

    # Outcome
    in_out: Mapped[str | None] = mapped_column(String(20))
    # 'in', 'out_long', 'out_wide', 'net', 'unknown'

    # Timestamps
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=datetime.utcnow
    )

    # Provenance tracking
    source: Mapped[str] = mapped_column(String(20), default="manual")
    # Values: "manual", "auto"
    contact_source: Mapped[str | None] = mapped_column(String(10))
    # Values: "manual" (user-tagged), "auto" (ball detection or lazy fallback)

    # Proposal metadata (one-table workflow)
    model_version: Mapped[str | None] = mapped_column(
        String(50)
    )  # e.g., "heuristic-v1"
    confidence: Mapped[float | None] = mapped_column(Float)  # 0.0 - 1.0
    detection_features: Mapped[str | None] = mapped_column(Text)  # JSON string
    status: Mapped[str] = mapped_column(String(20), default="accepted")
    # Values: "pending", "accepted", "rejected", "edited"
    reviewed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    # Original timestamps (if edited from proposal)
    original_start_timestamp: Mapped[float | None] = mapped_column(Float)
    original_end_timestamp: Mapped[float | None] = mapped_column(Float)

    # Active/split tracking
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    # False when this window has been superseded by a split operation
    parent_window_id: Mapped[int | None] = mapped_column(
        Integer,
        ForeignKey("serve_windows.id", ondelete="SET NULL"),
    )
    # Set when this window was created as a child of a split

    # Relationships
    video: Mapped["Video"] = relationship("Video", back_populates="serve_windows")  # type: ignore[name-defined]
    player: Mapped["Player | None"] = relationship(
        "Player", back_populates="serve_windows"
    )  # type: ignore[name-defined]
    parent_window: Mapped["ServeWindow | None"] = relationship(
        "ServeWindow",
        remote_side="ServeWindow.id",
        foreign_keys=[parent_window_id],
        backref="child_windows",
    )
    biomechanics_reports: Mapped[list["ServeBiomechanicsReport"]] = relationship(  # type: ignore[name-defined]
        "ServeBiomechanicsReport",
        back_populates="serve_window",
        cascade="all, delete-orphan",
        passive_deletes=True,
    )

    # Indexes for common query patterns
    __table_args__ = (
        Index("ix_serve_windows_user_created", "user_id", "created_at"),
        Index(
            "ix_serve_windows_player_created", "player_id", "created_at"
        ),  # Primary trend index
        Index(
            "ix_serve_windows_user_player_created",
            "user_id",
            "player_id",
            "created_at",
        ),
        Index(
            "ix_serve_windows_user_court_created",
            "user_id",
            "court_side",
            "created_at",
        ),
        Index("ix_serve_windows_video_start", "video_id", "start_timestamp"),
        Index("ix_serve_windows_video_status", "video_id", "status"),
        Index("ix_serve_windows_video_active", "video_id", "is_active"),
    )

    def __repr__(self) -> str:
        """String representation of serve window."""
        return (
            f"<ServeWindow(id={self.id}, video_id={self.video_id}, "
            f"player_id={self.player_id}, start={self.start_timestamp:.2f}s)>"
        )
