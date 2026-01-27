"""Background task API schemas."""

from typing import Any, Dict, Literal, Optional

from pydantic import BaseModel, Field


class AnalysisRequest(BaseModel):
    """Request model for starting analysis."""

    analysis_type: Literal["pose_only"] = Field(
        description="Type of analysis to perform"
    )
    confidence_threshold: float = Field(
        default=0.7,
        ge=0.0,
        le=1.0,
        description="Pose detection confidence threshold",
    )


class AnalysisResponse(BaseModel):
    """Unified analysis response model (RQ-compatible)."""

    job_id: str = Field(description="Background job identifier (UUID string)")
    video_id: int = Field(description="Video ID being analyzed")
    analysis_type: Literal["pose_only",] = Field(
        description="Type of analysis being performed"
    )
    status: Literal["queued", "processing", "completed", "failed", "cancelled"] = Field(
        description="Current task status (mapped from RQ statuses)"
    )
    message: str = Field(description="Status message")
    estimated_duration: Optional[float] = Field(
        default=None, description="Estimated completion time in seconds"
    )
    # Include result data when completed
    result: Optional[Dict[str, Any]] = Field(
        default=None, description="Analysis results when completed"
    )
