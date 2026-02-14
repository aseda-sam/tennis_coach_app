"""Schemas for overlay data API."""

from typing import Dict, List, Optional

from pydantic import BaseModel, Field


class PoseKeypoint(BaseModel):
    """A single pose keypoint."""

    name: str = Field(..., description="Keypoint name (e.g., 'left_shoulder')")
    x: float = Field(..., description="X coordinate in original video dimensions")
    y: float = Field(..., description="Y coordinate in original video dimensions")
    confidence: Optional[float] = Field(
        None, description="Keypoint detection confidence"
    )


class PoseFrame(BaseModel):
    """Pose detection data for a single frame."""

    frame_index: int = Field(..., description="Frame index in video")
    timestamp: float = Field(
        ..., description="Timestamp in seconds (calculated from frame_index / fps)"
    )
    keypoints: Dict[str, List[float]] = Field(
        ...,
        description="Keypoints as dict: {'left_shoulder': [x, y], ...}",
    )
    confidence: float = Field(
        ..., description="Overall pose detection confidence for this frame"
    )
    ball_position: Optional[List[float]] = Field(
        None,
        description="Ball center [x, y] in video coordinates if detected, else None",
    )
    ball_confidence: Optional[float] = Field(
        None, description="Ball detection confidence (0-1) when ball_position is set"
    )


class PoseOverlayData(BaseModel):
    """Complete overlay data for a video."""

    video_id: int = Field(..., description="Video ID")
    fps: float = Field(..., description="Video frames per second")
    total_frames: int = Field(..., description="Total number of frames")
    width: int = Field(..., description="Original video width")
    height: int = Field(..., description="Original video height")
    frames: List[PoseFrame] = Field(..., description="Pose data for each frame")
