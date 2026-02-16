"""Serve biomechanics report model — phase segmentation + raw metrics per serve."""

from datetime import datetime, timezone

from sqlalchemy import (
    Column,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
)
from sqlalchemy.orm import relationship

from app.core.database import Base


class ServeBiomechanicsReport(Base):
    """Computed phase segmentation and biomechanics metrics for a single serve attempt.

    Stores phases + raw metric values only. No scoring, ratings, or coaching text.
    """

    __tablename__ = "serve_biomechanics_reports"

    id = Column(Integer, primary_key=True, index=True)
    serve_attempt_id = Column(
        Integer,
        ForeignKey("serve_attempts.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    user_id = Column(String(36), nullable=False, index=True)
    player_id = Column(
        Integer,
        ForeignKey("players.id", ondelete="CASCADE"),
        nullable=False,
    )

    # Structured data (JSON-serialized)
    phase_segmentation_json = Column(Text, nullable=True)
    metrics_json = Column(Text, nullable=True)

    # Version tracking
    analysis_version = Column(String(20), nullable=False)

    created_at = Column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
    )

    # Relationships
    serve_attempt = relationship("ServeAttempt", backref="biomechanics_reports")
    player = relationship("Player")

    __table_args__ = (
        Index("ix_biomechanics_reports_player_created", "player_id", "created_at"),
        Index("ix_biomechanics_reports_user_player", "user_id", "player_id"),
    )
