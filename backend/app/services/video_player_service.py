"""
Service layer for VideoPlayer operations.
"""

from typing import List, Optional

from sqlalchemy.orm import Session

from app.models.player import Player
from app.models.video import Video
from app.models.video_player import VideoPlayer


def create_video_player_association(
    db: Session,
    video_id: int,
    player_id: int,
    pose_detection_id: Optional[int] = None,
) -> VideoPlayer:
    """Create a new video-player association."""
    # Check if video exists
    video = db.query(Video).filter(Video.id == video_id).first()
    if not video:
        raise ValueError(f"Video with ID {video_id} not found")

    # Check if player exists
    player = db.query(Player).filter(Player.id == player_id).first()
    if not player:
        raise ValueError(f"Player with ID {player_id} not found")

    # Check if association already exists
    existing = (
        db.query(VideoPlayer)
        .filter(VideoPlayer.video_id == video_id, VideoPlayer.player_id == player_id)
        .first()
    )
    if existing:
        raise ValueError(
            f"Player {player_id} is already associated with video {video_id}"
        )

    # Create new association
    video_player = VideoPlayer(
        video_id=video_id,
        player_id=player_id,
        pose_detection_id=pose_detection_id,
    )
    db.add(video_player)
    db.commit()
    db.refresh(video_player)
    return video_player


def get_video_player_association(
    db: Session, video_id: int, player_id: int
) -> Optional[VideoPlayer]:
    """Get a specific video-player association."""
    return (
        db.query(VideoPlayer)
        .filter(VideoPlayer.video_id == video_id, VideoPlayer.player_id == player_id)
        .first()
    )


def get_players_in_video(db: Session, video_id: int) -> List[VideoPlayer]:
    """Get all players associated with a specific video."""
    return db.query(VideoPlayer).filter(VideoPlayer.video_id == video_id).all()


def get_videos_for_player(db: Session, player_id: int) -> List[VideoPlayer]:
    """Get all videos where a specific player appears."""
    return db.query(VideoPlayer).filter(VideoPlayer.player_id == player_id).all()


def update_video_player_association(
    db: Session,
    video_id: int,
    player_id: int,
    pose_detection_id: Optional[int] = None,
) -> VideoPlayer:
    """Update a video-player association."""
    video_player = get_video_player_association(db, video_id, player_id)
    if not video_player:
        raise ValueError(f"Player {player_id} is not associated with video {video_id}")

    video_player.pose_detection_id = pose_detection_id
    db.commit()
    db.refresh(video_player)
    return video_player


def delete_video_player_association(db: Session, video_id: int, player_id: int) -> None:
    """Delete a video-player association."""
    video_player = get_video_player_association(db, video_id, player_id)
    if not video_player:
        raise ValueError(f"Player {player_id} is not associated with video {video_id}")

    db.delete(video_player)
    db.commit()


def get_ball_contact_player_options(db: Session, video_id: int) -> dict:
    """Get player assignment options for ball contact creation."""
    video_players = get_players_in_video(db, video_id)

    if len(video_players) == 1:
        return {
            "auto_assign": video_players[0].player_id,
            "player_name": video_players[0].player.name,
            "options": [video_players[0].player],
            "message": f"Auto-assigning to {video_players[0].player.name}",
        }
    elif len(video_players) > 1:
        return {
            "auto_assign": None,
            "options": [vp.player for vp in video_players],
            "message": "Multiple players in video - select one",
        }
    else:
        # No players in video, return all players as options
        all_players = db.query(Player).all()
        return {
            "auto_assign": None,
            "options": all_players,
            "message": "No players assigned to video",
        }
