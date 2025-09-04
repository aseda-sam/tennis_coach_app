"""Video quality assessment schemas."""

from pydantic import BaseModel, Field


class VideoQualityMetrics(BaseModel):
    """Video quality assessment metrics."""

    quality_score: float = Field(..., description="Overall quality score (0.0-1.0)")
    blur_score: float = Field(..., description="Blur quality score (0.0-1.0)")
    lighting_score: float = Field(..., description="Lighting quality score (0.0-1.0)")
    resolution_score: float = Field(
        ..., description="Resolution quality score (0.0-1.0)"
    )
    recommended_confidence_threshold: float = Field(
        ..., description="Recommended confidence threshold for detection"
    )
    quality_level: str = Field(
        ..., description="Quality level (excellent, good, fair, poor, unknown)"
    )
    frame_count_analyzed: int = Field(..., description="Number of frames analyzed")


class VideoQualityAssessmentResponse(BaseModel):
    """Response for video quality assessment."""

    video_id: int = Field(..., description="Video ID")
    metrics: VideoQualityMetrics = Field(..., description="Quality assessment metrics")
    assessment_type: str = Field(
        ..., description="Type of assessment (quick or detailed)"
    )
    processing_time_seconds: float = Field(..., description="Time taken for assessment")


class VideoQualityErrorResponse(BaseModel):
    """Error response for video quality assessment."""

    error: dict = Field(..., description="Error details")
    code: str = Field(..., description="Error code")
    message: str = Field(..., description="Error message")
    video_id: int = Field(..., description="Video ID that failed assessment")
