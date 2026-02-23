"""Ball detection API schemas."""

from typing import Literal, Optional

from pydantic import BaseModel, Field


class BallDetectionJobResponse(BaseModel):
    """Response schema for ball detection job status."""

    job_id: str = Field(description="Background job identifier (UUID string)")
    video_id: int = Field(description="Video ID being analyzed")
    status: Literal["queued", "processing", "completed", "failed"] = Field(
        description="Current job status"
    )
    message: str = Field(description="Status message")
    estimated_duration: Optional[float] = Field(
        default=None, description="Estimated completion time in seconds"
    )
