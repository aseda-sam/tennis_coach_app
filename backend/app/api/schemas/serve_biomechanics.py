"""Pydantic schemas for serve biomechanics API."""

from datetime import datetime
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field


class MetricValueResponse(BaseModel):
    """Single metric with value only (no rating or feedback)."""

    metric_name: str = Field(description="Metric key, e.g. knee_flexion_min_deg")
    value: Optional[float] = Field(
        default=None, description="Computed value or null if unavailable"
    )
    unit: str = Field(default="", description="Unit of measure, e.g. degrees")
    phase: Optional[str] = Field(
        default=None, description="Phase this metric belongs to"
    )
    timestamp: Optional[float] = Field(
        default=None,
        description="Timestamp (seconds) of the event this metric measures",
    )


class PhaseWindowResponse(BaseModel):
    """Time window for one detected phase (for timeline UI)."""

    phase: str = Field(description="Phase key")
    phase_label: str = Field(default="", description="Display label")
    start_timestamp: float = Field(description="Start time in seconds")
    end_timestamp: float = Field(description="End time in seconds")
    confidence: float = Field(description="Detection confidence 0-1")
    detected: bool = Field(description="Whether phase was heuristically detected")


class MomentMarkerResponse(BaseModel):
    """A single timestamp marker for a Key Time Point."""

    moment: str = Field(description="Moment key, e.g. ball_impact")
    moment_label: str = Field(default="", description="Display label")
    timestamp: Optional[float] = Field(
        default=None, description="Timestamp in seconds, or null if undetected"
    )
    frame: Optional[int] = Field(
        default=None, description="Frame index, or null if undetected"
    )
    confidence: float = Field(description="Detection confidence 0-1")
    detected: bool = Field(description="Whether moment was detected")


class BiomechanicsReportResponse(BaseModel):
    """Biomechanics report: phases + moments + raw metrics only."""

    id: int = Field(description="Report ID")
    serve_window_id: int = Field(description="Serve window ID")
    phase_segmentation: List[PhaseWindowResponse] = Field(
        default_factory=list,
        description="Detected phase windows for timeline",
    )
    moments: List[MomentMarkerResponse] = Field(
        default_factory=list,
        description="Key Time Point markers (single timestamps)",
    )
    metrics: List[MetricValueResponse] = Field(
        default_factory=list,
        description="Raw metric values (no ratings)",
    )
    analysis_version: str = Field(description="Phase/metrics analysis version")
    detection_meta: Optional[Dict[str, Any]] = Field(
        default=None,
        description="KTP detection reasoning and feature curves (stats for nerds)",
    )
    player_id: Optional[int] = Field(
        default=None,
        description="Player ID (for fetching metric history)",
    )
    created_at: datetime = Field(description="Report creation time")
    video_id: Optional[int] = Field(
        default=None,
        description="Video ID (included in history responses)",
    )
    video_filename: Optional[str] = Field(
        default=None,
        description="Video filename (included in history responses)",
    )


class CoachingFeedbackResponse(BaseModel):
    """LLM coaching feedback for a serve."""

    feedback: str = Field(description="Coaching feedback text (markdown)")
    model: str = Field(description="LLM model used")
    latency_ms: float = Field(description="LLM call latency in milliseconds")
    input_tokens: int = Field(description="Input token count")
    output_tokens: int = Field(description="Output token count")


class CoachingNoteRequest(BaseModel):
    """Open-coding annotation for a serve."""

    note: str = Field(description="The annotation text", min_length=1, max_length=2000)


class CoachingNoteResponse(BaseModel):
    """Saved open-coding note."""

    serve_window_id: int
    note: str
    timestamp: float = Field(description="Unix timestamp when saved")
    user_id: int
