"""
Video annotation API schemas.
"""

from datetime import datetime
from typing import List, Optional

from pydantic import BaseModel, Field


class VideoAnnotationRequest(BaseModel):
    """Request schema for creating video annotations."""

    annotation_type: str = Field(
        default="pose_only",
        description="Type of annotation to create",
        example="pose_only",
    )
    annotation_style: str = Field(
        default="standard",
        description="Style of annotation overlay",
        example="standard",
    )
    pose_detection_id: Optional[int] = Field(
        None, description="Specific pose detection ID to use (optional)"
    )


class VideoAnnotationInfo(BaseModel):
    """Video annotation information."""

    id: int = Field(..., description="Unique annotation ID")
    video_id: int = Field(..., description="Associated video ID")
    annotation_type: str = Field(..., description="Type of annotation")
    annotated_video_path: str = Field(..., description="Path to annotated video file")
    file_size_bytes: Optional[int] = Field(
        None, description="Size of annotated video file"
    )

    # Source analysis references
    pose_detection_id: Optional[int] = Field(
        None, description="Source pose detection ID"
    )
    # ball_detection_id: Optional[int] = Field(None, description="Source ball detection ID")  # Future
    analysis_id: Optional[int] = Field(None, description="Source analysis ID")

    # Processing metadata
    processing_time_seconds: float = Field(
        ..., description="Time taken to create annotation"
    )
    frames_annotated: Optional[int] = Field(
        None, description="Number of frames annotated"
    )
    annotation_style: str = Field(..., description="Style of annotation overlay")

    # Status
    status: str = Field(..., description="Annotation status")
    error_message: Optional[str] = Field(None, description="Error message if failed")

    # Timestamps
    created_at: datetime = Field(..., description="When the annotation was created")
    completed_at: Optional[datetime] = Field(
        None, description="When the annotation was completed"
    )

    class Config:
        """Pydantic configuration."""

        from_attributes = True


class VideoAnnotationResponse(BaseModel):
    """Response schema for video annotation operations."""

    success: bool = Field(..., description="Whether the operation was successful")
    message: str = Field(..., description="Operation message")
    annotation: Optional[VideoAnnotationInfo] = Field(
        None, description="Annotation information"
    )


class VideoAnnotationListResponse(BaseModel):
    """Response schema for listing video annotations."""

    annotations: List[VideoAnnotationInfo] = Field(
        ..., description="List of video annotations"
    )
    total_count: int = Field(..., description="Total number of annotations")


class VideoAnnotationDeleteResponse(BaseModel):
    """Response schema for deleting video annotations."""

    success: bool = Field(..., description="Whether the deletion was successful")
    message: str = Field(..., description="Deletion message")
    annotation_id: int = Field(..., description="ID of deleted annotation")
