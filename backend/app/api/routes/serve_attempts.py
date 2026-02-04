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
from app.dependencies.auth import get_current_user
from app.services import serve_attempt_service, video_service
from app.utils.authorization import require_video_access, require_video_not_demo
from app.utils.error_handling import handle_not_found_error, log_and_raise_error

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
            raise handle_not_found_error("video", str(serve_attempt.video_id))

        # Check authorization
        require_video_access(video, current_user)

        # Prevent modification of demo videos
        require_video_not_demo(video, current_user)

        db_serve_attempt = serve_attempt_service.create_serve_attempt(
            db=db,
            serve_attempt_data=serve_attempt,
            user_id=current_user["id"],
        )

        return ServeAttemptInfo.model_validate(db_serve_attempt)

    except ValueError as e:
        error_msg = str(e).lower()
        if "not found" in error_msg:
            raise handle_not_found_error("video", str(serve_attempt.video_id)) from e
        if "access denied" in error_msg or "forbidden" in error_msg:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=str(e),
            ) from e
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        ) from e
    except HTTPException:
        raise
    except Exception as e:  # noqa: BLE001 - Catch all unexpected errors for API endpoint
        log_and_raise_error(e, "create_serve_attempt", {"video_id": serve_attempt.video_id})


@router.put("/{serve_attempt_id}", response_model=ServeAttemptInfo)
async def update_serve_attempt(
    serve_attempt_id: int,
    updates: ServeAttemptUpdate,
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> ServeAttemptInfo:
    """Update a serve attempt (e.g., adjust timestamps)."""
    try:
        # Get serve attempt to check demo status
        serve_attempt = serve_attempt_service.get_serve_attempt_by_id(
            db=db,
            serve_attempt_id=serve_attempt_id,
            user_id=current_user["id"],
        )

        # Get video to check demo status
        video = video_service.get_video_by_id(db, serve_attempt.video_id)
        if video:
            require_video_not_demo(video, current_user)

        updated_serve_attempt = serve_attempt_service.update_serve_attempt(
            db=db,
            serve_attempt_id=serve_attempt_id,
            updates=updates,
            user_id=current_user["id"],
        )

        return ServeAttemptInfo.model_validate(updated_serve_attempt)

    except ValueError as e:
        error_msg = str(e).lower()
        if "not found" in error_msg:
            raise handle_not_found_error("serve_attempt", str(serve_attempt_id)) from e
        if "access denied" in error_msg or "forbidden" in error_msg:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=str(e),
            ) from e
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        ) from e
    except HTTPException:
        raise
    except Exception as e:  # noqa: BLE001 - Catch all unexpected errors for API endpoint
        log_and_raise_error(e, "update_serve_attempt", {"serve_attempt_id": serve_attempt_id})


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
        serve_attempts = serve_attempt_service.list_user_serve_attempts(
            db=db,
            user_id=current_user["id"],
            player_id=player_id,
            court_side=court_side,
            start_date=start_date,
            end_date=end_date,
            video_id=video_id,
        )

        return [ServeAttemptInfo.model_validate(sa) for sa in serve_attempts]

    except ValueError as e:
        error_msg = str(e).lower()
        if "access denied" in error_msg or "forbidden" in error_msg:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=str(e),
            ) from e
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        ) from e
    except HTTPException:
        raise
    except Exception as e:  # noqa: BLE001 - Catch all unexpected errors for API endpoint
        log_and_raise_error(e, "get_my_serve_attempts", {})


@router.get("/{serve_attempt_id}", response_model=ServeAttemptDetail)
async def get_serve_attempt(
    serve_attempt_id: int,
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> ServeAttemptDetail:
    """Get details of a specific serve attempt."""
    try:
        serve_attempt = serve_attempt_service.get_serve_attempt_by_id(
            db=db,
            serve_attempt_id=serve_attempt_id,
            user_id=current_user["id"],
        )

        return ServeAttemptDetail.model_validate(serve_attempt)

    except ValueError as e:
        error_msg = str(e).lower()
        if "not found" in error_msg:
            raise handle_not_found_error("serve_attempt", str(serve_attempt_id)) from e
        if "access denied" in error_msg or "forbidden" in error_msg:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=str(e),
            ) from e
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        ) from e
    except HTTPException:
        raise
    except Exception as e:  # noqa: BLE001 - Catch all unexpected errors for API endpoint
        log_and_raise_error(e, "get_serve_attempt", {"serve_attempt_id": serve_attempt_id})


@router.delete("/{serve_attempt_id}")
async def delete_serve_attempt(
    serve_attempt_id: int,
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> Dict[str, str]:
    """Delete a serve attempt."""
    try:
        # Get serve attempt to check demo status
        serve_attempt = serve_attempt_service.get_serve_attempt_by_id(
            db=db,
            serve_attempt_id=serve_attempt_id,
            user_id=current_user["id"],
        )

        # Get video to check demo status
        video = video_service.get_video_by_id(db, serve_attempt.video_id)
        if video:
            require_video_not_demo(video, current_user)

        serve_attempt_service.delete_serve_attempt(
            db=db,
            serve_attempt_id=serve_attempt_id,
            user_id=current_user["id"],
        )

        return {"message": f"Serve attempt {serve_attempt_id} deleted successfully"}

    except ValueError as e:
        error_msg = str(e).lower()
        if "not found" in error_msg:
            raise handle_not_found_error("serve_attempt", str(serve_attempt_id)) from e
        if "access denied" in error_msg or "forbidden" in error_msg:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=str(e),
            ) from e
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        ) from e
    except HTTPException:
        raise
    except Exception as e:  # noqa: BLE001 - Catch all unexpected errors for API endpoint
        log_and_raise_error(e, "delete_serve_attempt", {"serve_attempt_id": serve_attempt_id})
