"""Serve attempt API routes."""

import logging
from datetime import datetime
from typing import Dict, List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.api.schemas.serve_attempt import (
    ServeAttemptCreate,
    ServeAttemptDetail,
    ServeAttemptInfo,
    ServeAttemptUpdate,
)
from app.core.database import get_db
from app.core.shot_types import SERVE_SUBTYPES, is_valid_serve_subtype
from app.dependencies.auth import get_current_user
from app.models.player import Player
from app.models.serve_attempt import ServeAttempt
from app.services import player_service, video_service
from app.utils.authorization import require_video_access, require_video_not_demo

logger = logging.getLogger(__name__)

router = APIRouter(tags=["serve-attempts"])


@router.post("/", response_model=ServeAttemptInfo, status_code=status.HTTP_201_CREATED)
async def create_serve_attempt(
    serve_attempt: ServeAttemptCreate,
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> ServeAttemptInfo:
    """
    Create a manually-tagged serve attempt (start/end/optional contact).

    If player_id is omitted, automatically assigns user's default player.
    Validates player ownership (player.user_id == current_user.user_id).
    """
    try:
        # Get video to check authorization
        video = video_service.get_video_by_id(db, serve_attempt.video_id)
        if not video:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Video with ID {serve_attempt.video_id} not found",
            )

        # Check authorization
        require_video_access(video, current_user)

        # Prevent modification of demo videos
        require_video_not_demo(video, current_user)

        # Validate timestamps
        if serve_attempt.start_timestamp >= serve_attempt.end_timestamp:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="start_timestamp must be less than end_timestamp",
            )

        if serve_attempt.contact_timestamp is not None and (
            serve_attempt.contact_timestamp < serve_attempt.start_timestamp
            or serve_attempt.contact_timestamp > serve_attempt.end_timestamp
        ):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="contact_timestamp must be between start_timestamp and end_timestamp",
            )

        # Validate serve subtype
        if serve_attempt.serve_subtype and not is_valid_serve_subtype(
            serve_attempt.serve_subtype
        ):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid serve_subtype: {serve_attempt.serve_subtype}. "
                f"Valid options: {', '.join(SERVE_SUBTYPES)}",
            )

        # Auto-assign default player if not provided
        player_id = serve_attempt.player_id
        if not player_id:
            default_player = player_service.get_or_create_default_player(
                db, current_user["id"]
            )
            player_id = default_player.id
            logger.debug(f"Auto-assigned default player {player_id} for serve attempt")

        # Validate player ownership
        player = db.query(Player).filter(Player.id == player_id).first()
        if not player or player.user_id != current_user["id"]:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Player not found or access denied",
            )

        # Create serve attempt with user_id from auth
        db_serve_attempt = ServeAttempt(
            video_id=serve_attempt.video_id,
            user_id=current_user["id"],
            player_id=player_id,
            start_timestamp=serve_attempt.start_timestamp,
            end_timestamp=serve_attempt.end_timestamp,
            contact_timestamp=serve_attempt.contact_timestamp,
            court_side=serve_attempt.court_side,
            serve_number=serve_attempt.serve_number,
            serve_subtype=serve_attempt.serve_subtype,
            in_out=serve_attempt.in_out,
        )
        db.add(db_serve_attempt)
        db.commit()
        db.refresh(db_serve_attempt)

        logger.info(
            f"Created serve attempt {db_serve_attempt.id} for video {serve_attempt.video_id}"
        )

        return ServeAttemptInfo.model_validate(db_serve_attempt)

    except HTTPException:
        raise
    except Exception as e:
        logger.exception("Error creating serve attempt")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to create serve attempt. Please try again later.",
        ) from e


@router.put("/{serve_attempt_id}", response_model=ServeAttemptInfo)
async def update_serve_attempt(
    serve_attempt_id: int,
    updates: ServeAttemptUpdate,
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> ServeAttemptInfo:
    """Update a serve attempt (e.g., adjust timestamps)."""
    try:
        # Get serve attempt
        serve_attempt = (
            db.query(ServeAttempt).filter(ServeAttempt.id == serve_attempt_id).first()
        )

        if not serve_attempt:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Serve attempt with ID {serve_attempt_id} not found",
            )

        # Check authorization
        if serve_attempt.user_id != current_user["id"]:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Access denied",
            )

        # Get video to check demo status
        video = video_service.get_video_by_id(db, serve_attempt.video_id)
        if video:
            require_video_not_demo(video, current_user)

        # Validate player ownership if player_id is being updated
        if updates.player_id is not None:
            player = db.query(Player).filter(Player.id == updates.player_id).first()
            if not player or player.user_id != current_user["id"]:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="Player not found or access denied",
                )

        # Validate timestamps if being updated
        start_ts = updates.start_timestamp or serve_attempt.start_timestamp
        end_ts = updates.end_timestamp or serve_attempt.end_timestamp
        contact_ts = (
            updates.contact_timestamp
            if updates.contact_timestamp is not None
            else serve_attempt.contact_timestamp
        )

        if start_ts >= end_ts:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="start_timestamp must be less than end_timestamp",
            )

        if contact_ts is not None and (contact_ts < start_ts or contact_ts > end_ts):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="contact_timestamp must be between start_timestamp and end_timestamp",
            )

        # Validate serve subtype if being updated
        if updates.serve_subtype is not None and not is_valid_serve_subtype(
            updates.serve_subtype
        ):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid serve_subtype: {updates.serve_subtype}. "
                f"Valid options: {', '.join(SERVE_SUBTYPES)}",
            )

        # Update fields
        update_dict = updates.model_dump(exclude_unset=True)
        for key, value in update_dict.items():
            setattr(serve_attempt, key, value)

        db.commit()
        db.refresh(serve_attempt)

        logger.info(f"Updated serve attempt {serve_attempt_id}")

        return ServeAttemptInfo.model_validate(serve_attempt)

    except HTTPException:
        raise
    except Exception as e:
        logger.exception("Error updating serve attempt")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to update serve attempt. Please try again later.",
        ) from e


@router.get("/me", response_model=List[ServeAttemptInfo])
async def get_my_serve_attempts(
    player_id: Optional[int] = Query(None, description="Filter by specific player"),
    court_side: Optional[str] = Query(None, description="Filter by court side"),
    start_date: Optional[datetime] = Query(None, description="Filter by start date"),
    end_date: Optional[datetime] = Query(None, description="Filter by end date"),
    video_id: Optional[int] = Query(None, description="Filter by video ID"),
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> List[ServeAttemptInfo]:
    """
    Get my serve attempts with optional filters (enables analytics).

    If player_id provided, returns serves for that specific player.
    Otherwise returns all serves for user's players.
    """
    try:
        query = db.query(ServeAttempt).filter(
            ServeAttempt.user_id == current_user["id"]
        )

        # Apply filters
        if player_id is not None:
            # Validate player ownership
            player = db.query(Player).filter(Player.id == player_id).first()
            if not player or player.user_id != current_user["id"]:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="Player not found or access denied",
                )
            query = query.filter(ServeAttempt.player_id == player_id)

        if court_side is not None:
            query = query.filter(ServeAttempt.court_side == court_side)

        if video_id is not None:
            query = query.filter(ServeAttempt.video_id == video_id)

        if start_date is not None:
            query = query.filter(ServeAttempt.created_at >= start_date)

        if end_date is not None:
            query = query.filter(ServeAttempt.created_at <= end_date)

        # Order by creation date (newest first)
        serve_attempts = query.order_by(ServeAttempt.created_at.desc()).all()

        return [ServeAttemptInfo.model_validate(sa) for sa in serve_attempts]

    except HTTPException:
        raise
    except Exception as e:
        logger.exception("Error getting serve attempts")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to get serve attempts. Please try again later.",
        ) from e


@router.get("/{serve_attempt_id}", response_model=ServeAttemptDetail)
async def get_serve_attempt(
    serve_attempt_id: int,
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> ServeAttemptDetail:
    """Get details of a specific serve attempt."""
    try:
        serve_attempt = (
            db.query(ServeAttempt).filter(ServeAttempt.id == serve_attempt_id).first()
        )

        if not serve_attempt:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Serve attempt with ID {serve_attempt_id} not found",
            )

        # Check authorization
        if serve_attempt.user_id != current_user["id"]:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Access denied",
            )

        return ServeAttemptDetail.model_validate(serve_attempt)

    except HTTPException:
        raise
    except Exception as e:
        logger.exception("Error getting serve attempt")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to get serve attempt. Please try again later.",
        ) from e


@router.delete("/{serve_attempt_id}")
async def delete_serve_attempt(
    serve_attempt_id: int,
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> Dict[str, str]:
    """Delete a serve attempt."""
    try:
        # Get serve attempt
        serve_attempt = (
            db.query(ServeAttempt).filter(ServeAttempt.id == serve_attempt_id).first()
        )

        if not serve_attempt:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Serve attempt with ID {serve_attempt_id} not found",
            )

        # Check authorization
        if serve_attempt.user_id != current_user["id"]:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Access denied",
            )

        # Get video to check demo status
        video = video_service.get_video_by_id(db, serve_attempt.video_id)
        if video:
            require_video_not_demo(video, current_user)

        # Delete serve attempt
        db.delete(serve_attempt)
        db.commit()

        logger.info(f"Deleted serve attempt {serve_attempt_id}")

        return {"message": f"Serve attempt {serve_attempt_id} deleted successfully"}

    except HTTPException:
        raise
    except Exception as e:
        logger.exception("Error deleting serve attempt")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to delete serve attempt. Please try again later.",
        ) from e
