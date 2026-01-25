"""
Pydantic schemas for VideoPlayer operations.
"""

from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field

from app.api.schemas.player import PlayerInfo


class VideoPlayerCreate(BaseModel):
    """Schema for creating a video-player association."""

    player_id: int = Field(
        ..., description="ID of the player to associate with the video"
    )
    pose_detection_id: Optional[int] = Field(
        None, description="ID of the pose detection to link with this player"
    )


class VideoPlayerUpdate(BaseModel):
    """Schema for updating a video-player association."""

    pose_detection_id: Optional[int] = Field(
        None, description="ID of the pose detection to link with this player"
    )


class VideoPlayerInfo(BaseModel):
    """Schema for video-player association information."""

    id: int = Field(description="VideoPlayer association ID")
    video_id: int = Field(description="Video ID")
    player_id: int = Field(description="Player ID")
    player: PlayerInfo = Field(description="Player details")
    pose_detection_id: Optional[int] = Field(
        None, description="ID of the linked pose detection"
    )
    created_at: datetime = Field(description="When association was created")

    model_config = {"from_attributes": True}


class VideoWithPlayers(BaseModel):
    """Schema for video with associated players."""

    id: int = Field(description="Video ID")
    filename: str = Field(description="Video filename")
    players: list[PlayerInfo] = Field(description="Players appearing in this video")
    total_players: int = Field(description="Number of players in video")

    model_config = {"from_attributes": True}


class PlayerWithVideos(BaseModel):
    """Schema for player with associated videos."""

    id: int = Field(description="Player ID")
    name: str = Field(description="Player name")
    videos: list[dict] = Field(description="Videos where this player appears")
    total_videos: int = Field(description="Number of videos for this player")

    model_config = {"from_attributes": True}
