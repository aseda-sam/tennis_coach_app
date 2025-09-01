"""Ball contact-related API schemas."""

from datetime import datetime
from typing import Literal, Optional

from pydantic import BaseModel, Field


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
    detection_source: Optional[Literal["automated", "manual"]] = Field(
        description="Source of contact detection", default=None
    )


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
    detection_source: Literal["automated", "manual"] = Field(
        description="Source of contact detection"
    )
    created_at: datetime = Field(description="Creation timestamp")

    class Config:
        from_attributes = True


class BallContactDeleteResponse(BaseModel):
    """Model for ball contact deletion response."""

    message: str = Field(description="Deletion confirmation message")
