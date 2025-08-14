"""Video-related API schemas."""

from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field


class VideoUploadRequest(BaseModel):
    """Request model for video upload with optional metadata."""

    description: Optional[str] = Field(
        default=None, max_length=500, description="Optional description of the video"
    )


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
    error_message: Optional[str] = Field(default=None, description="Error message if processing failed")

    class Config:
        from_attributes = True


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

    class Config:
        from_attributes = True


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


class VideoDeleteResponse(BaseModel):
    """Response model for video deletion."""

    message: str = Field(description="Deletion status message")
    video_id: int = Field(description="Deleted video ID")
    filename: str = Field(description="Deleted filename")


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
