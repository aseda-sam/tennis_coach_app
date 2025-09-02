"""Ball detection API schemas."""

from datetime import datetime
from typing import List, Optional

from pydantic import BaseModel, Field


class BallDetectionMetrics(BaseModel):
    """Ball detection metrics response."""

    total_frames: int = Field(..., description="Total number of frames processed")
    frames_with_balls: int = Field(
        ..., description="Number of frames containing ball detections"
    )
    total_detections: int = Field(..., description="Total number of ball detections")
    detection_rate: float = Field(
        ..., description="Percentage of frames with ball detections (0.0-1.0)"
    )
    average_detections_per_frame: float = Field(
        ..., description="Average number of ball detections per frame"
    )

    # Model information
    model_used: str = Field(
        ..., description="YOLO model used for detection (e.g., 'yolov8n')"
    )
    confidence_threshold: float = Field(
        ..., description="Confidence threshold used for detections"
    )
    model_selection_reason: Optional[str] = Field(
        None, description="Reason for model selection"
    )

    # Quality metrics
    average_confidence: Optional[float] = Field(
        None, description="Average confidence score of detections"
    )
    min_confidence: Optional[float] = Field(
        None, description="Minimum confidence score"
    )
    max_confidence: Optional[float] = Field(
        None, description="Maximum confidence score"
    )

    # Performance metrics
    processing_time_seconds: float = Field(
        ..., description="Total processing time in seconds"
    )
    frame_processing_rate: Optional[float] = Field(
        None, description="Frames processed per second"
    )


class BallDetectionData(BaseModel):
    """Individual ball detection data."""

    bbox: List[float] = Field(
        ..., description="Bounding box coordinates [x1, y1, x2, y2]"
    )
    confidence: float = Field(..., description="Detection confidence score (0.0-1.0)")
    frame_index: int = Field(..., description="Frame index where detection occurred")


class BallDetectionResponse(BaseModel):
    """Ball detection analysis response."""

    id: int = Field(..., description="Ball detection record ID")
    video_id: int = Field(..., description="Associated video ID")
    status: str = Field(
        ..., description="Detection status (completed, failed, processing)"
    )

    # Detection metrics
    metrics: BallDetectionMetrics

    # Raw detection data (optional, can be large)
    detection_data: Optional[List[List[BallDetectionData]]] = Field(
        None, description="Raw detection data per frame (optional)"
    )

    # Timestamps
    created_at: datetime = Field(..., description="When detection was created")
    completed_at: Optional[datetime] = Field(
        None, description="When detection was completed"
    )

    class Config:
        from_attributes = True


class BallDetectionRequest(BaseModel):
    """Ball detection request parameters."""

    confidence_threshold: Optional[float] = Field(
        None,
        description="Confidence threshold for detections (0.0-1.0). If not provided, uses video quality-based threshold.",
        ge=0.0,
        le=1.0,
    )
    max_frames: Optional[int] = Field(
        None,
        description="Maximum number of frames to process. If not provided, processes all frames.",
        gt=0,
    )
    include_detection_data: bool = Field(
        False,
        description="Whether to include raw detection data in response (can be large)",
    )


class BallDetectionErrorResponse(BaseModel):
    """Ball detection error response."""

    error: str = Field(..., description="Error message")
    video_id: int = Field(..., description="Video ID that failed")
    details: Optional[str] = Field(None, description="Additional error details")


class BallDetectionSummary(BaseModel):
    """Summary information for ball detection results."""

    id: int = Field(..., description="Ball detection record ID")
    video_id: int = Field(..., description="Associated video ID")
    status: str = Field(..., description="Detection status")
    detection_rate: float = Field(..., description="Detection rate (0.0-1.0)")
    total_detections: int = Field(..., description="Total number of detections")
    model_used: str = Field(..., description="YOLO model used")
    processing_time_seconds: float = Field(
        ..., description="Processing time in seconds"
    )
    created_at: datetime = Field(..., description="Creation timestamp")

    class Config:
        from_attributes = True
