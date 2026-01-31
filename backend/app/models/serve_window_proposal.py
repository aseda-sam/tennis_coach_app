"""Serve window proposal model for storing machine-generated serve window proposals."""

from datetime import datetime

from sqlalchemy import Column, DateTime, Float, ForeignKey, Index, Integer, String, Text
from sqlalchemy.orm import relationship

from app.core.database import Base


class ServeWindowProposal(Base):
    """Machine-generated serve window proposals awaiting user review."""

    __tablename__ = "serve_window_proposals"

    id = Column(Integer, primary_key=True, index=True)
    video_id = Column(
        Integer, ForeignKey("videos.id", ondelete="CASCADE"), nullable=False, index=True
    )
    user_id = Column(String(36), nullable=False, index=True)  # Auth/tenancy boundary

    # Proposed timing
    start_timestamp = Column(Float, nullable=False)  # When serve attempt starts
    end_timestamp = Column(Float, nullable=False)  # When serve attempt ends

    # Model metadata
    model_version = Column(
        String(50), nullable=False
    )  # e.g., "heuristic-v1", "tcn-v1.2"
    confidence = Column(Float, nullable=False)  # 0.0 - 1.0

    # Detection features (for debugging/analysis)
    detection_features = Column(
        Text, nullable=True
    )  # JSON: peak_velocity, arm_height, etc.

    # Status tracking
    status = Column(String(20), nullable=False, default="pending")
    # Values: "pending", "accepted", "rejected", "edited", "merged"

    # If accepted/edited, optional link to the resulting ServeAttempt
    serve_attempt_id = Column(Integer, nullable=True)

    # Timestamps
    created_at = Column(DateTime(timezone=True), default=datetime.utcnow)
    reviewed_at = Column(DateTime(timezone=True), nullable=True)

    # Relationships
    video = relationship("Video", back_populates="serve_window_proposals")
    serve_attempt = relationship(
        "ServeAttempt",
        back_populates="source_proposal",
        primaryjoin="ServeWindowProposal.id==ServeAttempt.source_proposal_id",
        uselist=False,  # One-to-one: one proposal creates one serve attempt
    )

    # Indexes for common query patterns
    __table_args__ = (
        Index("ix_serve_window_proposals_video_status", "video_id", "status"),
        Index("ix_serve_window_proposals_user_created", "user_id", "created_at"),
    )

    def __repr__(self) -> str:
        """String representation of serve window proposal."""
        return (
            f"<ServeWindowProposal(id={self.id}, video_id={self.video_id}, "
            f"start={self.start_timestamp:.2f}s, end={self.end_timestamp:.2f}s, "
            f"confidence={self.confidence:.2f}, status={self.status})>"
        )
