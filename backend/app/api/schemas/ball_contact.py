"""Ball contact-related API schemas."""

from datetime import datetime
from typing import Dict, List, Literal, Optional

from pydantic import BaseModel, Field

from app.api.schemas.player import PlayerInfo


class BallContactInfo(BaseModel):
    """Model for ball contact information."""

    id: int = Field(description="Ball contact ID")
    video_id: int = Field(description="Video ID")
    frame_number: Optional[int] = Field(description="Frame number of the ball contact")
    video_timestamp: float = Field(
        description="Timestamp of the ball contact in the video"
    )
    detection_source: Literal["automated", "manual"] = Field(
        description="Source of contact detection"
    )
    contact_hand: Literal["left", "right"] = Field(
        description="Hand used for the contact"
    )
    stroke_type: Optional[Literal["ground_stroke", "serve", "volley", "overhead"]] = (
        Field(description="Type of stroke", default=None)
    )
    stroke_subtype: Optional[str] = Field(
        description="Subtype of the stroke", default=None
    )
    elbow_angle: Optional[float] = Field(
        description="Elbow angle in degrees from posture analysis (0-180°)",
        default=None,
        ge=0.0,
        le=180.0,
    )
    player_id: Optional[int] = Field(description="Player ID", default=None)
    player: Optional[PlayerInfo] = Field(description="Player information", default=None)
    created_at: datetime = Field(description="Creation timestamp")
    updated_at: Optional[datetime] = Field(description="Last update timestamp")

    class Config:
        from_attributes = True


class BallContactCreate(BaseModel):
    """Model for creating ball contact information."""

    video_id: int = Field(description="Video ID")
    video_timestamp: float = Field(
        description="Timestamp of the ball contact in the video"
    )
    contact_hand: Literal["left", "right"] = Field(
        description="Hand used for the contact"
    )
    stroke_type: Optional[Literal["ground_stroke", "serve", "volley", "overhead"]] = (
        Field(default=None, description="Type of stroke")
    )
    stroke_subtype: Optional[str] = Field(
        default=None, description="Subtype of the stroke"
    )
    detection_source: Literal["automated", "manual"] = Field(
        default="manual", description="Source of contact detection"
    )
    player_id: Optional[int] = Field(default=None, description="Player ID")


class BallContactUpdate(BaseModel):
    """Model for updating ball contact information."""

    video_timestamp: Optional[float] = Field(
        description="Timestamp of the ball contact in the video", default=None
    )
    contact_hand: Optional[Literal["left", "right"]] = Field(
        description="Hand used for the contact", default=None
    )
    stroke_type: Optional[Literal["ground_stroke", "serve", "volley", "overhead"]] = (
        Field(description="Type of stroke", default=None)
    )
    stroke_subtype: Optional[str] = Field(
        description="Subtype of the stroke", default=None
    )
    elbow_angle: Optional[float] = Field(
        description="Elbow angle in degrees from posture analysis (0-180°)",
        default=None,
        ge=0.0,
        le=180.0,
    )
    detection_source: Optional[Literal["automated", "manual"]] = Field(
        description="Source of contact detection", default=None
    )
    player_id: Optional[int] = Field(default=None, description="Player ID")


class BallContactListItem(BaseModel):
    """Model for listing ball contact information."""

    id: int = Field(description="Ball contact ID")
    video_id: int = Field(description="Video ID")
    frame_number: Optional[int] = Field(description="Frame number of the ball contact")
    video_timestamp: float = Field(
        description="Timestamp of the ball contact in the video"
    )
    contact_hand: Literal["left", "right"] = Field(
        description="Hand used for the contact"
    )
    stroke_type: Optional[Literal["ground_stroke", "serve", "volley", "overhead"]] = (
        Field(description="Type of stroke", default=None)
    )
    stroke_subtype: Optional[str] = Field(
        description="Subtype of the stroke", default=None
    )
    elbow_angle: Optional[float] = Field(
        description="Elbow angle in degrees from posture analysis (0-180°)",
        default=None,
        ge=0.0,
        le=180.0,
    )
    detection_source: Literal["automated", "manual"] = Field(
        description="Source of contact detection"
    )
    player_id: Optional[int] = Field(description="Player ID", default=None)
    player_name: Optional[str] = Field(description="Player name", default=None)
    created_at: datetime = Field(description="Creation timestamp")

    class Config:
        from_attributes = True


class BallContactDeleteResponse(BaseModel):
    """Model for ball contact deletion response."""

    message: str = Field(description="Deletion confirmation message")


class BulkBallContactRequest(BaseModel):
    """Request model for bulk ball contact fetch."""

    video_ids: List[int] = Field(
        description="List of video IDs to fetch ball contacts for",
        min_length=1,
        max_length=100,
    )


class BulkBallContactResponse(BaseModel):
    """Response model for bulk ball contact fetch."""

    contacts: Dict[int, List[BallContactListItem]] = Field(
        description="Ball contacts keyed by video ID"
    )


class PostureAnalysisResponse(BaseModel):
    """Model for posture analysis response."""

    ball_contact_id: int = Field(description="Ball contact ID")
    elbow_angle: Optional[float] = Field(
        description="Calculated elbow angle in degrees (0-180°)",
        default=None,
        ge=0.0,
        le=180.0,
    )
    analysis_status: Literal["success", "failed", "no_pose_data", "invalid_stroke"] = (
        Field(description="Status of the posture analysis")
    )
    message: Optional[str] = Field(
        description="Additional information about the analysis", default=None
    )


class PostureAnalysisRequest(BaseModel):
    """Model for triggering posture analysis."""

    force_reanalysis: bool = Field(
        default=False, description="Force reanalysis even if already analyzed"
    )
