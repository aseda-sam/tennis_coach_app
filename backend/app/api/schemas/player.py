"""Player-related API schemas."""

from datetime import datetime
from typing import Literal, Optional

from pydantic import BaseModel, Field


class PlayerCreate(BaseModel):
    """Model for creating a player."""

    name: str = Field(..., min_length=1, max_length=100, description="Player name")
    dominant_hand: Literal["left", "right"] = Field(
        ..., description="The hand typically used for hitting"
    )
    backhand_style: Literal["one_handed", "two_handed"] = Field(
        ..., description="Backhand playing style"
    )
    height: Optional[float] = Field(
        None, gt=0, description="Height in cm", example=175.5
    )
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
    height: Optional[float] = Field(
        None, gt=0, description="Height in cm", example=175.5
    )
    notes: Optional[str] = Field(None, description="Additional notes about the player")


class PlayerInfo(BaseModel):
    """Model for player information."""

    id: int = Field(description="Player ID")
    name: str = Field(description="Player name")
    dominant_hand: str = Field(description="Dominant hand")
    backhand_style: str = Field(description="Backhand style")
    height: Optional[float] = Field(description="Height in cm")
    notes: Optional[str] = Field(description="Additional notes")
    created_at: datetime = Field(description="Creation timestamp")
    updated_at: Optional[datetime] = Field(description="Last update timestamp")

    class Config:
        from_attributes = True


class PlayerListItem(BaseModel):
    """Model for listing players."""

    id: int = Field(description="Player ID")
    name: str = Field(description="Player name")
    dominant_hand: str = Field(description="Dominant hand")
    backhand_style: str = Field(description="Backhand style")
    height: Optional[float] = Field(description="Height in cm")
    created_at: datetime = Field(description="Creation timestamp")

    class Config:
        from_attributes = True


class PlayerDeleteResponse(BaseModel):
    """Model for player deletion response."""

    message: str = Field(description="Deletion confirmation message")
