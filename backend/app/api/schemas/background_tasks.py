"""Background task API schemas."""

from datetime import datetime
from typing import Any, Dict, Literal, Optional

from pydantic import BaseModel, Field


class TaskStatus(BaseModel):
    """Base task status response model (RQ-compatible)."""

    job_id: str = Field(description="Unique job identifier (UUID string)")
    video_id: int = Field(description="Video ID being analyzed")
    analysis_type: Literal[
        "pose_only",
        "ball_only",
        "video_annotation_only",
        "pose_with_annotation",
        "contact_metrics",
    ] = Field(description="Type of analysis being performed")
    status: Literal["queued", "processing", "completed", "failed", "cancelled"] = Field(
        description="Current task status (mapped from RQ statuses)"
    )
    progress: int = Field(
        default=0,
        ge=0,
        le=100,
        description="Overall progress percentage (0-100, calculated client-side from elapsed time)",
    )
    error: Optional[str] = Field(default=None, description="Error message if failed")
    result: Optional[Dict[str, Any]] = Field(
        default=None, description="Task results when completed"
    )
    started_at: Optional[datetime] = Field(
        default=None, description="Task start timestamp"
    )
    completed_at: Optional[datetime] = Field(
        default=None, description="Task completion timestamp"
    )
    estimated_duration: Optional[float] = Field(
        default=None, description="Estimated completion time in seconds"
    )


class TaskStartResponse(BaseModel):
    """Response model for starting a background task (deprecated, use AnalysisResponse)."""

    task_id: int = Field(description="Unique task identifier (deprecated, use job_id)")
    video_id: int = Field(description="Video ID being analyzed")
    analysis_type: Literal[
        "pose_only",
        "ball_only",
        "video_annotation_only",
        "pose_with_annotation",
        "contact_metrics",
    ] = Field(description="Type of analysis being performed")
    status: Literal["queued"] = Field(description="Initial task status")
    message: str = Field(description="Confirmation message")
    estimated_duration: Optional[float] = Field(
        default=None, description="Estimated completion time in seconds"
    )


class TaskListResponse(BaseModel):
    """Response model for listing all tasks."""

    tasks: Dict[str, TaskStatus] = Field(
        description="Dictionary of job_id (string) to task status"
    )
    total_tasks: int = Field(description="Total number of active tasks")
    status_counts: Dict[str, int] = Field(description="Count of tasks by status")


class TaskStatsResponse(BaseModel):
    """Response model for task statistics."""

    total_tasks: int = Field(description="Total number of tasks")
    status_counts: Dict[str, int] = Field(description="Count of tasks by status")
    active_workers: int = Field(description="Number of active worker threads")
    max_workers: int = Field(description="Maximum number of worker threads")
    queue_size: int = Field(description="Number of queued tasks")


class AnalysisRequest(BaseModel):
    """Request model for starting analysis."""

    analysis_type: Literal[
        "pose_only",
        "ball_only",
        "video_annotation_only",
        "pose_with_annotation",
        "contact_metrics",
    ] = Field(description="Type of analysis to perform")
    confidence_threshold: float = Field(
        default=0.7,
        ge=0.0,
        le=1.0,
        description="YOLO confidence threshold (not used for contact_metrics)",
    )
    force_reanalysis: bool = Field(
        default=False,
        description="Force reanalysis even if already analyzed (for contact_metrics)",
    )


class AnalysisResponse(BaseModel):
    """Unified analysis response model (RQ-compatible)."""

    job_id: str = Field(description="Background job identifier (UUID string)")
    video_id: int = Field(description="Video ID being analyzed")
    analysis_type: Literal[
        "pose_only",
        "ball_only",
        "video_annotation_only",
        "pose_with_annotation",
        "contact_metrics",
    ] = Field(description="Type of analysis being performed")
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
