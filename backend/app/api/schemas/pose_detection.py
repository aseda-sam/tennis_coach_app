"""
Pydantic schemas for pose detection API endpoints.
"""

from datetime import datetime
from typing import List, Optional

from pydantic import BaseModel, Field


class PoseDetectionRequest(BaseModel):
    """Request schema for starting pose detection analysis."""

    confidence_threshold: Optional[float] = Field(
        default=0.5,
        ge=0.0,
        le=1.0,
        description="Minimum confidence threshold for pose detection (0.0-1.0)",
    )
    detection_threshold: Optional[float] = Field(
        default=0.5,
        ge=0.0,
        le=1.0,
        description="Minimum detection threshold for pose landmarks (0.0-1.0)",
    )
    max_frames: Optional[int] = Field(
        default=None,
        ge=1,
        description="Maximum number of frames to process (optional)",
    )


class PoseDetectionMetrics(BaseModel):
    """Pose detection quality and performance metrics."""

    total_frames: int = Field(..., description="Total number of frames processed")
    frames_with_poses: int = Field(
        ..., description="Number of frames with detected poses"
    )
    total_pose_detections: int = Field(..., description="Total pose detections found")
    detection_rate: float = Field(
        ..., description="Percentage of frames with pose detections (0.0-1.0)"
    )

    # Quality metrics
    average_pose_confidence: Optional[float] = Field(
        None, description="Average confidence score across all pose detections"
    )
    min_pose_confidence: Optional[float] = Field(
        None, description="Minimum confidence score"
    )
    max_pose_confidence: Optional[float] = Field(
        None, description="Maximum confidence score"
    )
    pose_stability_score: Optional[float] = Field(
        None, description="Pose stability/consistency score across frames"
    )

    # Configuration used
    confidence_threshold: float = Field(
        ..., description="Confidence threshold used for detection"
    )
    detection_threshold: float = Field(
        ..., description="Detection threshold used for landmarks"
    )

    # Performance metrics
    processing_time_seconds: float = Field(
        ..., description="Total processing time in seconds"
    )
    frame_processing_rate: Optional[float] = Field(
        None, description="Processing rate in frames per second"
    )


class PoseKeypoint(BaseModel):
    """Individual pose keypoint data."""

    name: str = Field(..., description="Keypoint name (e.g., 'left_shoulder')")
    x: float = Field(..., description="X coordinate in pixels")
    y: float = Field(..., description="Y coordinate in pixels")
    confidence: Optional[float] = Field(
        None, description="Confidence score for this keypoint"
    )


class PoseDetectionData(BaseModel):
    """Individual pose detection for a single frame."""

    frame_index: int = Field(..., description="Frame number in the video")
    keypoints: List[PoseKeypoint] = Field(
        ..., description="List of detected pose keypoints"
    )
    overall_confidence: Optional[float] = Field(
        None, description="Overall confidence for this pose detection"
    )


class PoseDetectionInfo(BaseModel):
    """Complete pose detection information."""

    id: int = Field(..., description="Unique pose detection ID")
    video_id: int = Field(..., description="Associated video ID")

    # Detection metrics
    metrics: PoseDetectionMetrics = Field(
        ..., description="Detection metrics and quality scores"
    )

    # Frame-by-frame pose data (optional)
    frame_data: Optional[List[PoseDetectionData]] = Field(
        None, description="Frame-by-frame pose detection data"
    )

    # Timestamps
    created_at: datetime = Field(..., description="When the analysis was created")
    completed_at: Optional[datetime] = Field(
        None, description="When the analysis was completed"
    )

    # Status
    status: str = Field(..., description="Analysis status")
    error_message: Optional[str] = Field(None, description="Error message if failed")

    class Config:
        """Pydantic configuration."""

        from_attributes = True


class PoseDetectionResponse(BaseModel):
    """Response schema for pose detection endpoints."""

    pose_detection: PoseDetectionInfo = Field(
        ..., description="Pose detection information"
    )
    message: str = Field(..., description="Response message")


class PoseDetectionStartResponse(BaseModel):
    """Response schema for starting pose detection analysis."""

    pose_detection_id: Optional[int] = Field(
        None, description="Pose detection ID (if completed immediately)"
    )
    video_filename: str = Field(..., description="Name of the analyzed video file")
    status: str = Field(..., description="Analysis status")
    message: str = Field(..., description="Status message")
    estimated_duration: float = Field(
        ..., description="Estimated processing time in seconds"
    )
    task_id: Optional[int] = Field(
        None, description="Background task ID (if processing asynchronously)"
    )


class PoseDetectionListResponse(BaseModel):
    """Response schema for listing pose detections."""

    pose_detections: List[PoseDetectionInfo] = Field(
        ..., description="List of pose detection results"
    )
    total_count: int = Field(..., description="Total number of pose detections")
    message: str = Field(..., description="Response message")
