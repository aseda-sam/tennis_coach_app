"""Serve attempt API schemas."""

from datetime import datetime
from typing import Optional

from pydantic import BaseModel, ConfigDict, Field


class ServeAttemptCreate(BaseModel):
    """Schema for creating a serve attempt."""

    video_id: int = Field(description="Video ID")
    player_id: Optional[int] = Field(
        default=None,
        description="Player ID (optional - defaults to user's 'Me' player)",
    )
    start_timestamp: float = Field(ge=0, description="Start timestamp in seconds")
    end_timestamp: float = Field(ge=0, description="End timestamp in seconds")
    contact_timestamp: Optional[float] = Field(
        default=None, ge=0, description="Contact timestamp in seconds (optional)"
    )
    court_side: Optional[str] = Field(
        default=None, description="Court side: 'deuce' or 'ad'"
    )
    serve_number: Optional[int] = Field(
        default=None, ge=1, le=2, description="Serve number: 1 or 2"
    )
    serve_subtype: Optional[str] = Field(
        default=None, description="Serve subtype: 'flat', 'slice', 'kick'"
    )
    in_out: Optional[str] = Field(
        default=None,
        description="Outcome: 'in', 'out_long', 'out_wide', 'net', 'unknown'",
    )


class ServeAttemptUpdate(BaseModel):
    """Schema for updating a serve attempt."""

    player_id: Optional[int] = Field(
        default=None, description="Player ID (can change player assignment)"
    )
    start_timestamp: Optional[float] = Field(
        default=None, ge=0, description="Start timestamp in seconds"
    )
    end_timestamp: Optional[float] = Field(
        default=None, ge=0, description="End timestamp in seconds"
    )
    contact_timestamp: Optional[float] = Field(
        default=None, ge=0, description="Contact timestamp in seconds (optional)"
    )
    court_side: Optional[str] = Field(
        default=None, description="Court side: 'deuce' or 'ad'"
    )
    serve_number: Optional[int] = Field(
        default=None, ge=1, le=2, description="Serve number: 1 or 2"
    )
    serve_subtype: Optional[str] = Field(
        default=None, description="Serve subtype: 'flat', 'slice', 'kick'"
    )
    in_out: Optional[str] = Field(
        default=None,
        description="Outcome: 'in', 'out_long', 'out_wide', 'net', 'unknown'",
    )


class ServeAttemptInfo(BaseModel):
    """Schema for serve attempt information."""

    id: int = Field(description="Serve attempt ID")
    video_id: int = Field(description="Video ID")
    player_id: int = Field(description="Player ID (always present)")
    start_timestamp: float = Field(description="Start timestamp in seconds")
    end_timestamp: float = Field(description="End timestamp in seconds")
    contact_timestamp: Optional[float] = Field(
        default=None, description="Contact timestamp in seconds"
    )
    elbow_angle_at_contact: Optional[float] = Field(
        default=None, ge=0, le=180, description="Elbow angle at contact in degrees"
    )
    knee_bend_detected: Optional[bool] = Field(
        default=None,
        description="Whether knee bend was detected during early serve phase",
    )
    knee_bend_confidence: Optional[float] = Field(
        default=None,
        ge=0,
        le=1,
        description="Confidence score (0.0-1.0) for knee bend detection",
    )
    knee_hip_ratio_min: Optional[float] = Field(
        default=None, description="Minimum knee-hip ratio (lower = more bend)"
    )
    knee_flexion_min_deg_left: Optional[float] = Field(
        default=None,
        ge=0,
        le=180,
        description="Minimum left knee flexion angle in degrees",
    )
    knee_flexion_min_deg_right: Optional[float] = Field(
        default=None,
        ge=0,
        le=180,
        description="Minimum right knee flexion angle in degrees",
    )
    analysis_version: Optional[str] = Field(
        default=None, description="Version of analysis heuristics used"
    )
    court_side: Optional[str] = Field(default=None, description="Court side")
    serve_number: Optional[int] = Field(default=None, description="Serve number")
    serve_subtype: Optional[str] = Field(default=None, description="Serve subtype")
    in_out: Optional[str] = Field(default=None, description="Outcome")
    created_at: datetime = Field(description="Creation timestamp")

    model_config = ConfigDict(from_attributes=True)


class ServeAttemptDetail(ServeAttemptInfo):
    """Detailed serve attempt information (extends ServeAttemptInfo)."""

    pass


class ServeAnalysisSummary(BaseModel):
    """Schema for serve analysis summary."""

    video_id: int = Field(description="Video ID")
    total_serves: int = Field(ge=0, description="Total number of serve attempts")
    serves_with_contact: int = Field(
        ge=0, description="Number of serves with contact timestamp"
    )
    avg_elbow_angle: Optional[float] = Field(
        default=None, ge=0, le=180, description="Average elbow angle in degrees"
    )
    knee_bend_analyzed: int = Field(
        ge=0, default=0, description="Number of serves with knee bend metrics computed"
    )
    knee_bend_failed: int = Field(
        ge=0, default=0, description="Number of serves where knee bend analysis failed"
    )
