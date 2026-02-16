"""Serve detection API schemas."""

import json
from datetime import datetime
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, ConfigDict, Field, field_validator


class ServeWindowProposalInfo(BaseModel):
    """Schema for serve window proposal information."""

    id: int = Field(description="Proposal ID")
    video_id: int = Field(description="Video ID")
    start_timestamp: float = Field(description="Start timestamp in seconds")
    end_timestamp: float = Field(description="End timestamp in seconds")
    model_version: str = Field(description="Model version that generated this proposal")
    confidence: float = Field(ge=0.0, le=1.0, description="Confidence score (0-1)")
    detection_features: Optional[Dict[str, Any]] = Field(
        default=None, description="Detection features (peak_velocity, arm_height, etc.)"
    )
    status: str = Field(
        description="Proposal status: pending, accepted, rejected, edited"
    )
    created_at: datetime = Field(description="Creation timestamp")
    reviewed_at: Optional[datetime] = Field(
        default=None, description="Review timestamp"
    )

    model_config = ConfigDict(from_attributes=True)

    @field_validator("detection_features", mode="before")
    @classmethod
    def parse_detection_features(cls, v: object) -> Optional[Dict[str, Any]]:
        """Parse detection_features from JSON string if needed."""
        if v is None:
            return None
        if isinstance(v, dict):
            return v
        if isinstance(v, str):
            try:
                return json.loads(v)
            except json.JSONDecodeError:
                return None
        return None


class ProposeResponse(BaseModel):
    """Response after running serve detection."""

    video_id: int = Field(description="Video ID")
    proposals: List[ServeWindowProposalInfo] = Field(description="Generated proposals")
    count: int = Field(description="Number of proposals generated")


class AcceptProposalRequest(BaseModel):
    """Request to accept a proposal."""

    player_id: Optional[int] = Field(
        default=None, description="Player ID (defaults to user's default player)"
    )


class EditProposalRequest(BaseModel):
    """Request to accept a proposal with edits."""

    start_timestamp: float = Field(
        ge=0, description="Edited start timestamp in seconds"
    )
    end_timestamp: float = Field(ge=0, description="Edited end timestamp in seconds")
    player_id: Optional[int] = Field(
        default=None, description="Player ID (defaults to user's default player)"
    )


class DetectionStatusResponse(BaseModel):
    """Response with detection status for a video."""

    video_id: int = Field(description="Video ID")
    pending_proposals: int = Field(description="Number of pending proposals")
    reviewed_proposals: int = Field(description="Number of reviewed proposals")
    serve_windows: int = Field(description="Number of serve windows")
    can_run_detection: bool = Field(
        description="Whether detection can be run without force flag"
    )


class ClearProposalsResponse(BaseModel):
    """Response after clearing proposals."""

    video_id: int = Field(description="Video ID")
    cleared_count: int = Field(description="Number of proposals cleared")


class BulkAcceptRequest(BaseModel):
    """Request to accept all pending proposals."""

    player_id: Optional[int] = Field(
        default=None, description="Player ID (defaults to user's default player)"
    )


class BulkAcceptResponse(BaseModel):
    """Response after accepting all proposals."""

    video_id: int = Field(description="Video ID")
    accepted_count: int = Field(description="Number of proposals accepted")
    serve_window_ids: List[int] = Field(description="IDs of created serve windows")


class RejectByConfidenceRequest(BaseModel):
    """Request to reject proposals below a confidence threshold."""

    threshold: Optional[float] = Field(
        default=None,
        ge=0.0,
        le=1.0,
        description="Confidence threshold (reject proposals below this value). "
        "Defaults to SERVE_DETECTION_LOW_CONFIDENCE_THRESHOLD from config (0.6).",
    )


class RejectByConfidenceResponse(BaseModel):
    """Response after rejecting low-confidence proposals."""

    video_id: int = Field(description="Video ID")
    rejected_count: int = Field(description="Number of proposals rejected")
    threshold: float = Field(description="Confidence threshold used")
