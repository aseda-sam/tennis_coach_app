"""Player-related API schemas."""

from datetime import datetime
from typing import Literal, Optional

from pydantic import BaseModel, ConfigDict, Field

AgeGroup = Literal[
    "under_13",
    "13_to_17",
    "18_to_29",
    "30_to_44",
    "45_to_59",
    "60_plus",
]
Gender = Literal["female", "male", "non_binary", "prefer_not_to_say"]


class PlayerCreate(BaseModel):
    """Model for creating a player."""

    name: str = Field(..., min_length=1, max_length=100, description="Player name")
    dominant_hand: Literal["left", "right"] = Field(
        ..., description="The hand typically used for hitting"
    )
    backhand_style: Optional[Literal["one_handed", "two_handed"]] = Field(
        None, description="Backhand playing style"
    )
    height_cm: Optional[float] = Field(
        None, ge=0, le=300, description="Player height in centimeters"
    )
    age_group: Optional[AgeGroup] = Field(None, description="Player age group")
    gender: Optional[Gender] = Field(None, description="Player gender identity")
    notes: Optional[str] = Field(None, description="Additional notes about the player")


class PlayerUpdate(BaseModel):
    """Model for updating a player."""

    name: Optional[str] = Field(
        None, min_length=1, max_length=100, description="Player name"
    )
    dominant_hand: Optional[Literal["left", "right"]] = Field(
        None, description="The hand typically used for hitting"
    )
    backhand_style: Optional[Literal["one_handed", "two_handed"]] = Field(
        None, description="Backhand playing style"
    )
    height_cm: Optional[float] = Field(
        None, ge=0, le=300, description="Player height in centimeters"
    )
    age_group: Optional[AgeGroup] = Field(None, description="Player age group")
    gender: Optional[Gender] = Field(None, description="Player gender identity")
    notes: Optional[str] = Field(None, description="Additional notes about the player")


class PlayerInfo(BaseModel):
    """Model for player information."""

    id: int = Field(description="Player ID")
    name: str = Field(description="Player name")
    dominant_hand: str = Field(description="Dominant hand")
    backhand_style: Optional[str] = Field(description="Backhand style")
    height_cm: Optional[float] = Field(description="Player height in centimeters")
    age_group: Optional[AgeGroup] = Field(description="Player age group")
    gender: Optional[Gender] = Field(description="Player gender identity")
    notes: Optional[str] = Field(description="Additional notes")
    is_self: bool = Field(
        default=False,
        description="True when this player represents the account owner",
    )
    created_at: datetime = Field(description="Creation timestamp")
    updated_at: Optional[datetime] = Field(description="Last update timestamp")

    model_config = ConfigDict(from_attributes=True)


class PlayerListItem(BaseModel):
    """Model for listing players."""

    id: int = Field(description="Player ID")
    name: str = Field(description="Player name")
    dominant_hand: str = Field(description="Dominant hand")
    backhand_style: Optional[str] = Field(description="Backhand style")
    created_at: datetime = Field(description="Creation timestamp")

    model_config = ConfigDict(from_attributes=True)


class PlayerDeleteResponse(BaseModel):
    """Model for player deletion response."""

    message: str = Field(description="Deletion confirmation message")
