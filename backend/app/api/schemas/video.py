"""Video-related API schemas."""

from datetime import datetime
from typing import Dict, List, Optional

from pydantic import BaseModel, ConfigDict, Field


class VideoMetadata(BaseModel):
    """Video metadata extracted from file."""

    duration: Optional[float] = Field(
        default=None, ge=0, description="Video duration in seconds"
    )
    fps: Optional[float] = Field(default=None, ge=0, description="Frames per second")
    width: Optional[int] = Field(
        default=None, ge=1, description="Video width in pixels"
    )
    height: Optional[int] = Field(
        default=None, ge=1, description="Video height in pixels"
    )
    frame_count: Optional[int] = Field(
        default=None, ge=0, description="Total number of frames"
    )


class VideoQualityMetrics(BaseModel):
    """Video quality assessment metrics."""

    quality_score: float = Field(ge=0, le=1, description="Overall quality score (0-1)")
    blur_score: float = Field(ge=0, le=1, description="Blur quality score (0-1)")
    lighting_score: float = Field(
        ge=0, le=1, description="Lighting quality score (0-1)"
    )
    resolution_score: float = Field(
        ge=0, le=1, description="Resolution quality score (0-1)"
    )
    quality_level: str = Field(
        description="Quality level (excellent, good, fair, poor, unknown)"
    )
    recommended_confidence_threshold: float = Field(
        ge=0, le=1, description="Recommended confidence threshold for analysis"
    )
    frame_count_analyzed: int = Field(
        ge=0, description="Number of frames analyzed for quality assessment"
    )


class VideoQualityAssessmentResponse(BaseModel):
    """Response model for video quality assessment."""

    video_id: int = Field(description="Video ID")
    filename: str = Field(description="Video filename")
    quality_metrics: VideoQualityMetrics = Field(
        description="Quality assessment results"
    )
    assessment_time: float = Field(description="Assessment duration in seconds")
    message: str = Field(description="Assessment status message")


class VideoInfo(BaseModel):
    """Complete video information."""

    id: int = Field(description="Video ID")
    filename: str = Field(description="Video filename")
    file_path: str = Field(description="File path on disk")
    file_size: int = Field(ge=0, description="File size in bytes")
    content_type: Optional[str] = Field(default=None, description="MIME type")
    duration: Optional[float] = Field(default=None, description="Duration in seconds")
    fps: Optional[float] = Field(default=None, description="Frames per second")
    width: Optional[int] = Field(default=None, description="Width in pixels")
    height: Optional[int] = Field(default=None, description="Height in pixels")
    frame_count: Optional[int] = Field(default=None, description="Total frames")
    created_at: datetime = Field(description="Upload timestamp")
    updated_at: Optional[datetime] = Field(
        default=None, description="Last update timestamp"
    )
    status: str = Field(description="Video processing status")
    error_message: Optional[str] = Field(
        default=None, description="Error message if processing failed"
    )
    # Quality metrics (assessed once on upload)
    quality_score: Optional[float] = Field(
        default=None, ge=0, le=1, description="Overall quality score (0-1)"
    )
    blur_score: Optional[float] = Field(
        default=None, ge=0, le=1, description="Blur quality score (0-1)"
    )
    lighting_score: Optional[float] = Field(
        default=None, ge=0, le=1, description="Lighting quality score (0-1)"
    )
    resolution_score: Optional[float] = Field(
        default=None, ge=0, le=1, description="Resolution quality score (0-1)"
    )
    quality_level: Optional[str] = Field(
        default=None, description="Quality level (excellent, good, fair, poor, unknown)"
    )
    quality_assessed_at: Optional[datetime] = Field(
        default=None, description="Quality assessment timestamp"
    )

    model_config = ConfigDict(from_attributes=True)


class VideoListItem(BaseModel):
    """Simplified video information for list endpoints."""

    id: int = Field(description="Video ID")
    filename: str = Field(description="Video filename")
    file_size: int = Field(description="File size in bytes")
    duration: Optional[float] = Field(default=None, description="Duration in seconds")
    width: Optional[int] = Field(default=None, description="Width in pixels")
    height: Optional[int] = Field(default=None, description="Height in pixels")
    created_at: datetime = Field(description="Upload timestamp")
    status: str = Field(description="Video processing status")
    # Quality metrics for list display
    quality_score: Optional[float] = Field(
        default=None, ge=0, le=1, description="Overall quality score (0-1)"
    )
    quality_level: Optional[str] = Field(
        default=None, description="Quality level (excellent, good, fair, poor, unknown)"
    )

    model_config = ConfigDict(from_attributes=True)


class VideoUploadResponse(BaseModel):
    """Response model for video upload."""

    video_id: int = Field(description="Created video ID")
    filename: str = Field(description="Uploaded filename")
    file_size: int = Field(description="File size in bytes")
    status: str = Field(description="Upload status")
    message: str = Field(description="Status message")
    metadata: Optional[VideoMetadata] = Field(
        default=None, description="Extracted metadata"
    )
    # Quality assessment results
    quality_metrics: Optional[VideoQualityMetrics] = Field(
        default=None, description="Quality assessment results"
    )


class VideoDeleteResponse(BaseModel):
    """Response model for video deletion."""

    message: str = Field(description="Deletion status message")
    video_id: int = Field(description="Deleted video ID")
    filename: str = Field(description="Deleted filename")


class VideoMetrics(BaseModel):
    """Video performance metrics aggregated from ball contacts."""

    video_id: int = Field(description="Video ID")
    serve_count: int = Field(ge=0, description="Number of serves detected")
    avg_elbow_angle: Optional[float] = Field(
        default=None,
        ge=0,
        le=180,
        description="Average elbow angle in degrees (0-180°)",
    )
    total_contacts: int = Field(ge=0, description="Total number of ball contacts")
    toss_height: Optional[float] = Field(
        default=None,
        ge=0,
        description="Average toss height in cm (placeholder for future)",
    )
    contact_height: Optional[float] = Field(
        default=None,
        ge=0,
        description="Average contact height in cm (placeholder for future)",
    )


class BulkVideoMetricsRequest(BaseModel):
    """Request model for bulk video metrics."""

    video_ids: List[int] = Field(
        description="List of video IDs to get metrics for",
        min_length=1,
        max_length=100,
    )


class BulkVideoMetricsResponse(BaseModel):
    """Response model for bulk video metrics."""

    metrics: Dict[int, VideoMetrics] = Field(description="Metrics keyed by video ID")


# Validation functions
def validate_video_filename(filename: str) -> str:
    """Validate video filename format."""
    if not filename:
        raise ValueError("Filename cannot be empty")

    # Check for valid extensions
    valid_extensions = {".mp4", ".mov", ".avi", ".mkv", ".wmv"}
    if not any(filename.lower().endswith(ext) for ext in valid_extensions):
        raise ValueError(
            f"Unsupported file format. Supported: {', '.join(valid_extensions)}"
        )

    return filename


def validate_file_size(file_size: int, max_size: int) -> int:
    """Validate file size."""
    if file_size <= 0:
        raise ValueError("File size must be positive")

    if file_size > max_size:
        raise ValueError(f"File size {file_size} exceeds maximum {max_size} bytes")

    return file_size
