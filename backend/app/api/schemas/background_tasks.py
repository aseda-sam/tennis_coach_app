"""Background task API schemas."""

from datetime import datetime
from typing import Any, Dict, Literal, Optional

from pydantic import BaseModel, Field


class TaskStatus(BaseModel):
    """Base task status response model."""

    task_id: int = Field(description="Unique task identifier")
    video_id: int = Field(description="Video ID being analyzed")
    analysis_type: Literal["pose_only", "ball_only", "video_annotation_only"] = Field(
        description="Type of analysis being performed"
    )
    status: Literal["queued", "processing", "completed", "failed", "cancelled"] = Field(
        description="Current task status"
    )
    progress: int = Field(
        ge=0, le=100, description="Overall progress percentage (0-100)"
    )
    current_stage: Optional[str] = Field(
        default=None, description="Current processing stage"
    )
    stage_progress: Optional[int] = Field(
        default=None, ge=0, le=100, description="Progress within current stage (0-100)"
    )
    stage_message: Optional[str] = Field(
        default=None, description="Human-readable stage description"
    )
    error: Optional[str] = Field(default=None, description="Error message if failed")
    result: Optional[Dict[str, Any]] = Field(
        default=None, description="Task results when completed"
    )
    started_at: datetime = Field(description="Task start timestamp")
    completed_at: Optional[datetime] = Field(
        default=None, description="Task completion timestamp"
    )


class TaskStartResponse(BaseModel):
    """Response model for starting a background task."""

    task_id: int = Field(description="Unique task identifier")
    video_id: int = Field(description="Video ID being analyzed")
    analysis_type: Literal["pose_only", "ball_only", "video_annotation_only"] = Field(
        description="Type of analysis being performed"
    )
    status: Literal["queued"] = Field(description="Initial task status")
    message: str = Field(description="Confirmation message")
    estimated_duration: Optional[float] = Field(
        default=None, description="Estimated completion time in seconds"
    )


class TaskListResponse(BaseModel):
    """Response model for listing all tasks."""

    tasks: Dict[int, TaskStatus] = Field(
        description="Dictionary of task_id to task status"
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

    analysis_type: Literal["pose_only", "ball_only", "video_annotation_only"] = Field(
        description="Type of analysis to perform"
    )
    confidence_threshold: float = Field(
        default=0.7, ge=0.0, le=1.0, description="YOLO confidence threshold"
    )


class AnalysisResponse(BaseModel):
    """Unified analysis response model."""

    task_id: int = Field(description="Background task identifier")
    video_id: int = Field(description="Video ID being analyzed")
    analysis_type: Literal["pose_only", "ball_only", "video_annotation_only"] = Field(
        description="Type of analysis being performed"
    )
    status: Literal["queued", "processing", "completed", "failed", "cancelled"] = Field(
        description="Current task status"
    )
    message: str = Field(description="Status message")
    estimated_duration: Optional[float] = Field(
        default=None, description="Estimated completion time in seconds"
    )
    # Include result data when completed
    result: Optional[Dict[str, Any]] = Field(
        default=None, description="Analysis results when completed"
    )
