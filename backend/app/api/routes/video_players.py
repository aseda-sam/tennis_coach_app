"""
API routes for video-player associations.
"""

from typing import List

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.api.schemas.video_player import (
    BallContactPlayerOptions,
    PlayerWithVideos,
    VideoPlayerCreate,
    VideoPlayerInfo,
    VideoPlayerUpdate,
    VideoWithPlayers,
)
from app.core.database import get_db
from app.models.player import Player
from app.models.video import Video
from app.services.video_player_service import (
    create_video_player_association,
    delete_video_player_association,
    get_ball_contact_player_options,
    get_players_in_video,
    get_videos_for_player,
    update_video_player_association,
)
from app.utils.error_handling import log_and_raise_error

router = APIRouter(prefix="/v0", tags=["video-players"])


def _create_video_player_info(db: Session, video_player) -> VideoPlayerInfo:
    """Create VideoPlayerInfo from VideoPlayer model."""
    return VideoPlayerInfo(
        id=video_player.id,
        video_id=video_player.video_id,
        player_id=video_player.player_id,
        player=video_player.player,
        pose_detection_id=video_player.pose_detection_id,
        created_at=video_player.created_at,
    )


@router.post("/videos/{video_id}/players/", response_model=VideoPlayerInfo)
def associate_player_with_video(
    video_id: int,
    video_player_data: VideoPlayerCreate,
    db: Session = Depends(get_db),
) -> VideoPlayerInfo:
    """Associate a player with a video."""
    try:
        video_player = create_video_player_association(
            db=db,
            video_id=video_id,
            player_id=video_player_data.player_id,
            pose_detection_id=video_player_data.pose_detection_id,
        )
        return _create_video_player_info(db, video_player)
    except ValueError as e:
        if "not found" in str(e).lower():
            raise HTTPException(status_code=404, detail=str(e)) from e
        elif "already associated" in str(e).lower():
            raise HTTPException(status_code=409, detail=str(e)) from e
        else:
            log_and_raise_error(
                e, "associate_player_with_video", {"video_id": video_id}
            )


@router.get("/videos/{video_id}/players/", response_model=List[VideoPlayerInfo])
def get_video_players(
    video_id: int, db: Session = Depends(get_db)
) -> List[VideoPlayerInfo]:
    """Get all players associated with a video."""
    try:
        video_players = get_players_in_video(db, video_id)
        return [_create_video_player_info(db, vp) for vp in video_players]
    except Exception as e:
        log_and_raise_error(e, "get_video_players", {"video_id": video_id})


@router.get("/videos/{video_id}/players-summary/", response_model=VideoWithPlayers)
def get_video_players_summary(
    video_id: int, db: Session = Depends(get_db)
) -> VideoWithPlayers:
    """Get video with associated players summary."""
    try:
        video_players = get_players_in_video(db, video_id)
        if not video_players:
            # Check if video exists
            video = db.query(Video).filter(Video.id == video_id).first()
            if not video:
                raise HTTPException(status_code=404, detail="Video not found")
            return VideoWithPlayers(
                id=video.id,
                filename=video.filename,
                players=[],
                total_players=0,
            )

        video = video_players[0].video
        return VideoWithPlayers(
            id=video.id,
            filename=video.filename,
            players=[vp.player for vp in video_players],
            total_players=len(video_players),
        )
    except HTTPException:
        raise
    except Exception as e:
        log_and_raise_error(e, "get_video_players_summary", {"video_id": video_id})


@router.put("/videos/{video_id}/players/{player_id}/", response_model=VideoPlayerInfo)
def update_video_player_association(
    video_id: int,
    player_id: int,
    video_player_data: VideoPlayerUpdate,
    db: Session = Depends(get_db),
) -> VideoPlayerInfo:
    """Update a video-player association."""
    try:
        video_player = update_video_player_association(
            db=db,
            video_id=video_id,
            player_id=player_id,
            pose_detection_id=video_player_data.pose_detection_id,
        )
        return _create_video_player_info(db, video_player)
    except ValueError as e:
        if "not associated" in str(e).lower():
            raise HTTPException(status_code=404, detail=str(e)) from e
        else:
            log_and_raise_error(
                e,
                "update_video_player_association",
                {"video_id": video_id, "player_id": player_id},
            )


@router.delete(
    "/videos/{video_id}/players/{player_id}/", status_code=status.HTTP_204_NO_CONTENT
)
def remove_player_from_video(
    video_id: int, player_id: int, db: Session = Depends(get_db)
) -> None:
    """Remove a player from a video."""
    try:
        delete_video_player_association(db, video_id, player_id)
    except ValueError as e:
        if "not associated" in str(e).lower():
            raise HTTPException(status_code=404, detail=str(e)) from e
        else:
            log_and_raise_error(
                e,
                "remove_player_from_video",
                {"video_id": video_id, "player_id": player_id},
            )


@router.get("/players/{player_id}/videos/", response_model=PlayerWithVideos)
def get_player_videos(
    player_id: int, db: Session = Depends(get_db)
) -> PlayerWithVideos:
    """Get all videos where a player appears."""
    try:
        video_players = get_videos_for_player(db, player_id)
        if not video_players:
            # Check if player exists
            player = db.query(Player).filter(Player.id == player_id).first()
            if not player:
                raise HTTPException(status_code=404, detail="Player not found")
            return PlayerWithVideos(
                id=player.id,
                name=player.name,
                videos=[],
                total_videos=0,
            )

        player = video_players[0].player
        videos_data = [
            {
                "id": vp.video.id,
                "filename": vp.video.filename,
                "created_at": vp.video.created_at,
            }
            for vp in video_players
        ]
        return PlayerWithVideos(
            id=player.id,
            name=player.name,
            videos=videos_data,
            total_videos=len(video_players),
        )
    except HTTPException:
        raise
    except Exception as e:
        log_and_raise_error(e, "get_player_videos", {"player_id": player_id})


@router.get(
    "/videos/{video_id}/player-options/", response_model=BallContactPlayerOptions
)
def get_ball_contact_player_options(
    video_id: int, db: Session = Depends(get_db)
) -> BallContactPlayerOptions:
    """Get player assignment options for ball contact creation."""
    try:
        options = get_ball_contact_player_options(db, video_id)
        return BallContactPlayerOptions(**options)
    except Exception as e:
        log_and_raise_error(
            e, "get_ball_contact_player_options", {"video_id": video_id}
        )
