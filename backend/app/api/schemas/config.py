"""App configuration schemas."""

from pydantic import BaseModel, Field


class UploadLimits(BaseModel):
    """Upload size and format limits."""

    max_file_size_bytes: int = Field(
        description="Maximum upload size in bytes",
        example=104857600,
    )
    max_video_duration_seconds: int = Field(
        description="Maximum video duration in seconds",
        example=300,
    )
    supported_formats: list[str] = Field(
        description="Supported file extensions",
        example=[".mp4", ".mov"],
    )


class ServeDetectionConfig(BaseModel):
    """Serve detection configuration."""

    low_confidence_threshold: float = Field(
        description="Proposals below this confidence are considered 'uncertain'",
    )


class AppConfigResponse(BaseModel):
    """Public app configuration."""

    upload_limits: UploadLimits = Field(description="Upload limits")
    serve_detection: ServeDetectionConfig = Field(
        description="Serve detection settings"
    )
