"""Serve window API schemas."""

from datetime import datetime
from typing import Literal, Optional

from pydantic import BaseModel, ConfigDict, Field, model_validator


class ServeWindowCreate(BaseModel):
    """Schema for creating a serve window."""

    video_id: int = Field(description="Video ID")
    player_id: Optional[int] = Field(
        default=None,
        description="Player ID (optional - defaults to user's 'Me' player)",
    )
    start_timestamp: float = Field(ge=0, description="Start timestamp in seconds")
    end_timestamp: float = Field(ge=0, description="End timestamp in seconds")
    contact_timestamp: Optional[float] = Field(
        default=None, ge=0, description="Contact timestamp in seconds (optional)"
    )
    court_side: Optional[Literal["deuce", "ad"]] = Field(
        default=None, description="Court side: 'deuce' or 'ad'"
    )
    serve_number: Optional[int] = Field(
        default=None, ge=1, le=2, description="Serve number: 1 or 2"
    )
    serve_subtype: Optional[Literal["flat", "slice", "kick"]] = Field(
        default=None, description="Serve subtype: 'flat', 'slice', 'kick'"
    )
    in_out: Optional[Literal["in", "out_long", "out_wide", "net", "unknown"]] = Field(
        default=None,
        description="Outcome: 'in', 'out_long', 'out_wide', 'net', 'unknown'",
    )

    @model_validator(mode="after")
    def validate_timestamps(self) -> "ServeWindowCreate":
        if self.start_timestamp >= self.end_timestamp:
            raise ValueError("start_timestamp must be less than end_timestamp")
        if self.contact_timestamp is not None and not (
            self.start_timestamp <= self.contact_timestamp <= self.end_timestamp
        ):
            raise ValueError(
                "contact_timestamp must be between start_timestamp and end_timestamp"
            )
        return self


class ServeWindowUpdate(BaseModel):
    """Schema for updating a serve window."""

    player_id: Optional[int] = Field(
        default=None, description="Player ID (can change player assignment)"
    )
    start_timestamp: Optional[float] = Field(
        default=None, ge=0, description="Start timestamp in seconds"
    )
    end_timestamp: Optional[float] = Field(
        default=None, ge=0, description="End timestamp in seconds"
    )
    contact_timestamp: Optional[float] = Field(
        default=None, ge=0, description="Contact timestamp in seconds (optional)"
    )
    court_side: Optional[Literal["deuce", "ad"]] = Field(
        default=None, description="Court side: 'deuce' or 'ad'"
    )
    serve_number: Optional[int] = Field(
        default=None, ge=1, le=2, description="Serve number: 1 or 2"
    )
    serve_subtype: Optional[Literal["flat", "slice", "kick"]] = Field(
        default=None, description="Serve subtype: 'flat', 'slice', 'kick'"
    )
    in_out: Optional[Literal["in", "out_long", "out_wide", "net", "unknown"]] = Field(
        default=None,
        description="Outcome: 'in', 'out_long', 'out_wide', 'net', 'unknown'",
    )

    @model_validator(mode="after")
    def validate_timestamps(self) -> "ServeWindowUpdate":
        start = self.start_timestamp
        end = self.end_timestamp
        contact = self.contact_timestamp
        if start is not None and end is not None and start >= end:
            raise ValueError("start_timestamp must be less than end_timestamp")
        if (
            contact is not None
            and start is not None
            and end is not None
            and not (start <= contact <= end)
        ):
            raise ValueError(
                "contact_timestamp must be between start_timestamp and end_timestamp"
            )
        return self


class ServeWindowInfo(BaseModel):
    """Schema for serve window information."""

    id: int = Field(description="Serve window ID")
    video_id: int = Field(description="Video ID")
    player_id: int = Field(description="Player ID (always present)")
    start_timestamp: float = Field(description="Start timestamp in seconds")
    end_timestamp: float = Field(description="End timestamp in seconds")
    contact_timestamp: Optional[float] = Field(
        default=None, description="Contact timestamp in seconds"
    )
    source: str = Field(description="Origin of window: manual or auto")
    status: str = Field(
        description="Workflow status: pending, accepted, rejected, edited"
    )
    confidence: Optional[float] = Field(
        default=None,
        ge=0,
        le=1,
        description="Detection confidence for auto-generated windows",
    )
    model_version: Optional[str] = Field(
        default=None, description="Detection model version for auto-generated windows"
    )
    court_side: Optional[str] = Field(default=None, description="Court side")
    serve_number: Optional[int] = Field(default=None, description="Serve number")
    serve_subtype: Optional[str] = Field(default=None, description="Serve subtype")
    in_out: Optional[str] = Field(default=None, description="Outcome")
    contact_source: Optional[str] = Field(
        default=None,
        description="How contact_timestamp was set: 'manual' (user-tagged) or 'auto' (ball detection)",
    )
    created_at: datetime = Field(description="Creation timestamp")

    model_config = ConfigDict(from_attributes=True)
