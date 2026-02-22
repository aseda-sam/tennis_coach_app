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


class BiomechanicsReportResponse(BaseModel):
    """Biomechanics report: phases + raw metrics only."""

    id: int = Field(description="Report ID")
    serve_window_id: int = Field(description="Serve window ID")
    phase_segmentation: List[PhaseWindowResponse] = Field(
        default_factory=list,
        description="Detected phase windows for timeline",
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
    created_at: datetime = Field(description="Report creation time")
