"""Analysis-related API schemas."""

import json
from datetime import datetime
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field
from pydantic.functional_validators import field_validator


class AnalysisRequest(BaseModel):
    """Request model for starting video analysis."""

    analysis_type: str = Field(
        default="ball_tracking",
        description="Type of analysis to perform",
        example="ball_tracking",
    )
    confidence_threshold: float = Field(
        default=0.7, ge=0.0, le=1.0, description="Detection confidence threshold"
    )
    include_pose_detection: bool = Field(
        default=False, description="Whether to include pose detection in analysis"
    )
    synchronous: bool = Field(
        default=False, description="Whether to run analysis synchronously (for testing)"
    )


class AnalysisMetadata(BaseModel):
    """Analysis metadata and configuration."""

    analysis_type: str = Field(description="Type of analysis performed")
    model_used: Optional[str] = Field(default=None, description="ML model used")
    confidence_threshold: float = Field(description="Detection confidence threshold")
    processing_parameters: dict = Field(
        default_factory=dict, description="Processing parameters"
    )


class AnalysisResults(BaseModel):
    """Detailed analysis results."""

    total_frames: int = Field(ge=0, description="Total frames processed")
    frames_with_balls: int = Field(ge=0, description="Frames with ball detections")
    total_ball_detections: int = Field(ge=0, description="Total ball detections")
    average_detections_per_frame: float = Field(
        ge=0, description="Average detections per frame"
    )
    detection_rate: float = Field(ge=0, le=1, description="Ball detection rate")
    frames_with_pose: Optional[int] = Field(
        default=None, ge=0, description="Frames with pose detections"
    )
    pose_detection_rate: Optional[float] = Field(
        default=None, ge=0, le=1, description="Pose detection rate"
    )
    pose_detections: Optional[str] = Field(
        default=None, description="Pose detection data"
    )


class AnalysisInfo(BaseModel):
    """Complete analysis information."""

    id: int = Field(description="Analysis ID")
    video_id: int = Field(description="Associated video ID")
    video_filename: str = Field(description="Video filename")
    analysis_type: str = Field(description="Type of analysis")
    status: Optional[str] = Field(default=None, description="Analysis status")
    total_frames: int = Field(description="Total frames processed")
    frames_with_balls: int = Field(description="Frames with ball detections")
    total_ball_detections: int = Field(description="Total ball detections")
    average_detections_per_frame: float = Field(
        description="Average detections per frame"
    )
    detection_rate: float = Field(description="Ball detection rate")
    processing_time: float = Field(description="Processing time in seconds")
    model_used: Optional[str] = Field(default=None, description="ML model used")
    confidence_threshold: Optional[float] = Field(
        default=None, description="Detection confidence threshold"
    )
    include_pose_detection: Optional[bool] = Field(
        default=None, description="Whether pose detection was included"
    )
    frames_with_pose: Optional[int] = Field(
        default=None, description="Frames with pose detections"
    )
    pose_detection_rate: Optional[float] = Field(
        default=None, description="Pose detection rate"
    )
    ball_detections: Optional[List[object]] = Field(
        default=None, description="Ball detection data (parsed from JSON)"
    )
    pose_detections: Optional[List[object]] = Field(
        default=None, description="Pose detection data (parsed from JSON)"
    )
    annotated_video_path: Optional[str] = Field(
        default=None, description="Path to annotated video"
    )
    created_at: datetime = Field(description="Analysis creation timestamp")
    updated_at: Optional[datetime] = Field(
        default=None, description="Last update timestamp"
    )

    @field_validator("ball_detections", mode="before")
    @classmethod
    def _parse_ball_detections(cls, v: object) -> List[object]:
        """Parse ball_detections from JSON string to array."""
        if isinstance(v, str):
            try:
                return json.loads(v or "[]")
            except (json.JSONDecodeError, TypeError):
                return []
        return v or []

    @field_validator("pose_detections", mode="before")
    @classmethod
    def _parse_pose_detections(cls, v: object) -> List[object]:
        """Parse pose_detections from JSON string to array."""
        if isinstance(v, str):
            try:
                return json.loads(v or "[]")
            except (json.JSONDecodeError, TypeError):
                return []
        return v or []

    class Config:
        from_attributes = True


class AnalysisListItem(BaseModel):
    """Simplified analysis information for list endpoints."""

    id: int = Field(description="Analysis ID")
    video_id: int = Field(description="Associated video ID")  # Added to match frontend
    video_filename: str = Field(description="Video filename")
    analysis_type: str = Field(description="Type of analysis")
    detection_rate: float = Field(description="Ball detection rate")
    processing_time: float = Field(description="Processing time in seconds")
    created_at: datetime = Field(description="Analysis creation timestamp")

    class Config:
        from_attributes = True


class AnalysisStartResponse(BaseModel):
    """Response model for starting analysis."""

    analysis_id: int = Field(description="Created analysis ID")
    video_filename: str = Field(description="Video filename")
    status: str = Field(description="Analysis status")
    message: str = Field(description="Status message")
    estimated_duration: Optional[float] = Field(
        default=None, description="Estimated processing time"
    )
    task_id: Optional[int] = Field(
        default=None, description="Background task ID for tracking"
    )


class AnalysisDeleteResponse(BaseModel):
    """Response model for analysis deletion."""

    message: str = Field(description="Deletion status message")
    analysis_id: int = Field(description="Deleted analysis ID")
    video_filename: str = Field(description="Associated video filename")


# Analysis status constants
class AnalysisStatus:
    """Analysis status constants."""

    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


# Analysis types
class AnalysisTypes:
    """Analysis type constants."""

    BALL_TRACKING = "ball_tracking"
    POSE_DETECTION = "pose_detection"
    COMPREHENSIVE = "comprehensive"


# Background task schemas
class TaskStatus(BaseModel):
    """Background task status information."""

    task_id: int = Field(description="Task ID")
    video_id: int = Field(description="Video ID being processed")
    analysis_type: str = Field(description="Type of analysis")
    status: str = Field(
        description="Task status (queued, processing, completed, failed, cancelled)"
    )
    progress: int = Field(ge=0, le=100, description="Progress percentage")
    error: Optional[str] = Field(default=None, description="Error message if failed")
    result: Optional[Dict[str, Any]] = Field(
        default=None, description="Analysis result if completed"
    )
    started_at: datetime = Field(description="Task start timestamp")
    completed_at: Optional[datetime] = Field(
        default=None, description="Task completion timestamp"
    )


class TaskListResponse(BaseModel):
    """Response model for listing background tasks."""

    tasks: Dict[int, TaskStatus] = Field(description="All active tasks")
    total: int = Field(description="Total number of tasks")


class TaskStatsResponse(BaseModel):
    """Response model for task statistics."""

    total_tasks: int = Field(description="Total number of tasks")
    status_counts: Dict[str, int] = Field(description="Count of tasks by status")
    active_workers: int = Field(description="Number of active worker threads")
    max_workers: int = Field(description="Maximum number of worker threads")
