"""
Service layer for VideoPlayer operations.
"""

import logging
from typing import List, Optional

from sqlalchemy.orm import Session

from app.models.player import Player
from app.models.video import Video
from app.models.video_player import VideoPlayer

logger = logging.getLogger(__name__)


def create_video_player_association(
    db: Session,
    video_id: int,
    player_id: int,
    pose_detection_id: Optional[int] = None,
) -> VideoPlayer:
    """Create a new video-player association."""
    logger.info(
        f"Creating video-player association: video_id={video_id}, player_id={player_id}, pose_detection_id={pose_detection_id}"
    )

    # Check if video exists
    video = db.query(Video).filter(Video.id == video_id).first()
    if not video:
        logger.warning(
            f"Video-player association failed: video with ID {video_id} not found"
        )
        raise ValueError(f"Video with ID {video_id} not found")

    # Check if player exists
    player = db.query(Player).filter(Player.id == player_id).first()
    if not player:
        logger.warning(
            f"Video-player association failed: player with ID {player_id} not found"
        )
        raise ValueError(f"Player with ID {player_id} not found")

    # Check if association already exists
    existing = (
        db.query(VideoPlayer)
        .filter(VideoPlayer.video_id == video_id, VideoPlayer.player_id == player_id)
        .first()
    )
    if existing:
        logger.warning(
            f"Video-player association failed: player {player_id} is already associated with video {video_id}"
        )
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

    logger.info(
        f"✅ Successfully created video-player association: ID={video_player.id}, video='{video.filename}', player='{player.name}'"
    )
    return video_player


def get_video_player_association(
    db: Session, video_id: int, player_id: int
) -> Optional[VideoPlayer]:
    """Get a specific video-player association."""
    logger.debug(
        f"Retrieving video-player association: video_id={video_id}, player_id={player_id}"
    )

    association = (
        db.query(VideoPlayer)
        .filter(VideoPlayer.video_id == video_id, VideoPlayer.player_id == player_id)
        .first()
    )

    if association:
        logger.debug(f"Found video-player association: ID={association.id}")
    else:
        logger.debug(
            f"Video-player association not found: video_id={video_id}, player_id={player_id}"
        )

    return association


def get_players_in_video(db: Session, video_id: int) -> List[VideoPlayer]:
    """Get all players associated with a specific video."""
    logger.debug(f"Retrieving players in video: video_id={video_id}")

    players = db.query(VideoPlayer).filter(VideoPlayer.video_id == video_id).all()
    logger.debug(f"Found {len(players)} players in video {video_id}")

    return players


def get_videos_for_player(db: Session, player_id: int) -> List[VideoPlayer]:
    """Get all videos where a specific player appears."""
    logger.debug(f"Retrieving videos for player: player_id={player_id}")

    videos = db.query(VideoPlayer).filter(VideoPlayer.player_id == player_id).all()
    logger.debug(f"Found {len(videos)} videos for player {player_id}")

    return videos


def update_video_player_association(
    db: Session,
    video_id: int,
    player_id: int,
    pose_detection_id: Optional[int] = None,
) -> VideoPlayer:
    """Update a video-player association."""
    logger.info(
        f"Updating video-player association: video_id={video_id}, player_id={player_id}, pose_detection_id={pose_detection_id}"
    )

    video_player = get_video_player_association(db, video_id, player_id)
    if not video_player:
        logger.warning(
            f"Video-player association update failed: player {player_id} is not associated with video {video_id}"
        )
        raise ValueError(f"Player {player_id} is not associated with video {video_id}")

    old_pose_detection_id = video_player.pose_detection_id
    video_player.pose_detection_id = pose_detection_id
    db.commit()
    db.refresh(video_player)

    logger.info(
        f"✅ Successfully updated video-player association: ID={video_player.id}, pose_detection_id: {old_pose_detection_id} -> {pose_detection_id}"
    )
    return video_player


def delete_video_player_association(db: Session, video_id: int, player_id: int) -> None:
    """Delete a video-player association."""
    logger.info(
        f"Deleting video-player association: video_id={video_id}, player_id={player_id}"
    )

    video_player = get_video_player_association(db, video_id, player_id)
    if not video_player:
        logger.warning(
            f"Video-player association deletion failed: player {player_id} is not associated with video {video_id}"
        )
        raise ValueError(f"Player {player_id} is not associated with video {video_id}")

    logger.info(f"Deleting video-player association: ID={video_player.id}")
    db.delete(video_player)
    db.commit()

    logger.info(
        f"✅ Successfully deleted video-player association: video_id={video_id}, player_id={player_id}"
    )
