"""Serve window model for storing tagged or auto-detected serve windows."""

from datetime import datetime

from sqlalchemy import (
    Boolean,
    Column,
    DateTime,
    Float,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
)
from sqlalchemy.orm import relationship

from app.core.database import Base


class ServeWindow(Base):
    """One row = one serve window (manual or auto-detected)."""

    __tablename__ = "serve_windows"

    id = Column(Integer, primary_key=True, index=True)
    video_id = Column(
        Integer, ForeignKey("videos.id", ondelete="CASCADE"), nullable=False, index=True
    )
    user_id = Column(String(36), nullable=False, index=True)  # Auth/tenancy boundary
    player_id = Column(
        Integer,
        ForeignKey("players.id", ondelete="CASCADE"),
        nullable=True,
        index=True,
    )  # Nullable while pending auto-detected proposals are unassigned

    # Timing - manually tagged
    start_timestamp = Column(Float, nullable=False)  # When serve window starts
    end_timestamp = Column(Float, nullable=False)  # When serve window ends
    contact_timestamp = Column(Float, nullable=True)  # Optional - may not make contact

    # Context
    court_side = Column(String(10), nullable=True)  # 'deuce', 'ad'
    serve_number = Column(Integer, nullable=True)  # 1, 2
    serve_subtype = Column(String(20), nullable=True)  # 'flat', 'slice', 'kick'

    # Outcome
    in_out = Column(
        String(20), nullable=True
    )  # 'in', 'out_long', 'out_wide', 'net', 'unknown'

    # Timestamps
    created_at = Column(DateTime(timezone=True), default=datetime.utcnow)

    # Provenance tracking
    source = Column(String(20), nullable=False, default="manual")
    # Values: "manual", "auto"
    contact_source = Column(String(10), nullable=True)
    # Values: "manual" (user-tagged), "auto" (ball detection or lazy fallback)

    # Proposal metadata (one-table workflow)
    model_version = Column(String(50), nullable=True)  # e.g., "heuristic-v1"
    confidence = Column(Float, nullable=True)  # 0.0 - 1.0
    detection_features = Column(Text, nullable=True)  # JSON string
    status = Column(String(20), nullable=False, default="accepted")
    # Values: "pending", "accepted", "rejected", "edited"
    reviewed_at = Column(DateTime(timezone=True), nullable=True)

    # Original timestamps (if edited from proposal)
    original_start_timestamp = Column(Float, nullable=True)
    original_end_timestamp = Column(Float, nullable=True)

    # Active/split tracking
    is_active = Column(Boolean, nullable=False, default=True)
    # False when this window has been superseded by a split operation
    parent_window_id = Column(
        Integer,
        ForeignKey("serve_windows.id", ondelete="SET NULL"),
        nullable=True,
    )
    # Set when this window was created as a child of a split

    # Relationships
    video = relationship("Video", back_populates="serve_windows")
    player = relationship("Player", back_populates="serve_windows")
    parent_window = relationship(
        "ServeWindow",
        remote_side="ServeWindow.id",
        foreign_keys=[parent_window_id],
        backref="child_windows",
    )
    biomechanics_reports = relationship(
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
