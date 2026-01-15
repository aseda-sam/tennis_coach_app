"""Ball contact-related API schemas."""

import logging
from datetime import datetime
from typing import Dict, List, Literal, Optional

from pydantic import BaseModel, Field, ValidationInfo, field_validator

from app.api.schemas.player import PlayerInfo
from app.core.shot_types import (
    StrokeType,
    is_valid_subtype_for_type,
    map_legacy_subtype_to_canonical,
)

logger = logging.getLogger(__name__)


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
    stroke_type: Optional[StrokeType] = Field(
        description="Type of stroke", default=None
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

    @field_validator("stroke_subtype")
    @classmethod
    def validate_subtype(cls, v: Optional[str], info: ValidationInfo) -> Optional[str]:
        """Validate that subtype is valid for the given stroke type.

        For reading existing data, invalid subtypes are first attempted to be
        mapped to canonical subtypes. If mapping fails, they are normalized to None
        to prevent validation errors on legacy data. New data should be
        validated strictly in the service layer.
        """
        if v is None or v == "":
            return None
        stroke_type = info.data.get("stroke_type")

        # Check if already valid
        if is_valid_subtype_for_type(stroke_type, v):
            return v

        # Try to map legacy subtype to canonical
        canonical_subtype = map_legacy_subtype_to_canonical(stroke_type, v)
        if canonical_subtype:
            logger.info(
                f"Mapped legacy subtype '{v}' → '{canonical_subtype}' "
                f"for stroke_type '{stroke_type}' during validation"
            )
            return canonical_subtype

        # No mapping possible, normalize to None
        logger.warning(
            f"Invalid subtype '{v}' for stroke_type '{stroke_type}' "
            f"in ball contact. Could not map to canonical subtype. "
            f"Normalizing to None. This may indicate legacy data that needs migration."
        )
        return None

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
    stroke_type: Optional[StrokeType] = Field(
        default=None, description="Type of stroke"
    )
    stroke_subtype: Optional[str] = Field(
        default=None, description="Subtype of the stroke"
    )
    detection_source: Literal["automated", "manual"] = Field(
        default="manual", description="Source of contact detection"
    )
    player_id: Optional[int] = Field(default=None, description="Player ID")

    @field_validator("stroke_subtype")
    @classmethod
    def validate_subtype(cls, v: Optional[str], info: ValidationInfo) -> Optional[str]:
        """Validate that subtype is valid for the given stroke type.

        Strict validation for create operations - raises ValueError for invalid subtypes.
        """
        if v is None or v == "":
            return None
        stroke_type = info.data.get("stroke_type")
        if not is_valid_subtype_for_type(stroke_type, v):
            from app.core.shot_types import get_subtypes_for_type

            allowed = ", ".join(get_subtypes_for_type(stroke_type))
            raise ValueError(
                f"Invalid subtype '{v}' for stroke type '{stroke_type}'. "
                f"Allowed subtypes: {allowed}"
            )
        return v


class BallContactUpdate(BaseModel):
    """Model for updating ball contact information."""

    video_timestamp: Optional[float] = Field(
        description="Timestamp of the ball contact in the video", default=None
    )
    contact_hand: Optional[Literal["left", "right"]] = Field(
        description="Hand used for the contact", default=None
    )
    stroke_type: Optional[StrokeType] = Field(
        description="Type of stroke", default=None
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

    @field_validator("stroke_subtype")
    @classmethod
    def validate_subtype(cls, v: Optional[str], info: ValidationInfo) -> Optional[str]:
        """Validate that subtype is valid for the given stroke type.

        Strict validation for update operations - raises ValueError for invalid subtypes.
        """
        if v is None or v == "":
            return None
        stroke_type = info.data.get("stroke_type")
        if not is_valid_subtype_for_type(stroke_type, v):
            from app.core.shot_types import get_subtypes_for_type

            allowed = ", ".join(get_subtypes_for_type(stroke_type))
            raise ValueError(
                f"Invalid subtype '{v}' for stroke type '{stroke_type}'. "
                f"Allowed subtypes: {allowed}"
            )
        return v


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
    stroke_type: Optional[StrokeType] = Field(
        description="Type of stroke", default=None
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
