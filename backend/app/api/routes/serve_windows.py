"""Serve window API routes."""

import logging
from datetime import datetime
from typing import Dict, List, Optional

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.orm import Session

from app.api.schemas.serve_window import (
    ServeWindowCreate,
    ServeWindowInfo,
    ServeWindowUpdate,
)
from app.core.database import get_db
from app.dependencies.auth import get_current_user
from app.services import serve_window_service, video_service
from app.utils.authorization import require_video_access, require_video_not_demo
from app.utils.error_handling import handle_not_found_error, handle_service_error

logger = logging.getLogger(__name__)

router = APIRouter(tags=["serve-windows"])


@router.post("/", response_model=ServeWindowInfo, status_code=status.HTTP_201_CREATED)
async def create_serve_window(
    serve_window: ServeWindowCreate,
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> ServeWindowInfo:
    """
    Create a manually-tagged serve window (start/end/optional contact).

    If player_id is omitted, automatically assigns user's default player.
    Validates player ownership (player.user_id == current_user.user_id).
    """
    try:
        # Get video to check authorization
        video = video_service.get_video_by_id(db, serve_window.video_id)
        if not video:
            raise handle_not_found_error("video", str(serve_window.video_id))

        # Check authorization
        require_video_access(video, current_user)

        # Prevent modification of demo videos
        require_video_not_demo(video, current_user)

        db_serve_window = serve_window_service.create_serve_window(
            db=db,
            serve_window_data=serve_window,
            user_id=current_user["id"],
        )

        return ServeWindowInfo.model_validate(db_serve_window)

    except Exception as e:  # noqa: BLE001
        handle_service_error(
            e, "create_serve_window", {"video_id": serve_window.video_id}
        )


@router.put("/{serve_window_id}", response_model=ServeWindowInfo)
async def update_serve_window(
    serve_window_id: int,
    updates: ServeWindowUpdate,
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> ServeWindowInfo:
    """Update a serve window (e.g., adjust timestamps)."""
    try:
        # Get serve window to check demo status
        serve_window = serve_window_service.get_serve_window_by_id(
            db=db,
            serve_window_id=serve_window_id,
            user_id=current_user["id"],
        )

        # Get video to check demo status
        video = video_service.get_video_by_id(db, serve_window.video_id)
        if video:
            require_video_not_demo(video, current_user)

        updated_serve_window = serve_window_service.update_serve_window(
            db=db,
            serve_window_id=serve_window_id,
            updates=updates,
            user_id=current_user["id"],
        )

        return ServeWindowInfo.model_validate(updated_serve_window)

    except Exception as e:  # noqa: BLE001
        handle_service_error(
            e, "update_serve_window", {"serve_window_id": serve_window_id}
        )


@router.get("/me", response_model=List[ServeWindowInfo])
async def get_my_serve_windows(
    player_id: Optional[int] = Query(None, description="Filter by specific player"),
    court_side: Optional[str] = Query(None, description="Filter by court side"),
    start_date: Optional[datetime] = Query(None, description="Filter by start date"),
    end_date: Optional[datetime] = Query(None, description="Filter by end date"),
    video_id: Optional[int] = Query(None, description="Filter by video ID"),
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> List[ServeWindowInfo]:
    """
    Get my serve windows with optional filters (enables analytics).

    If player_id provided, returns serves for that specific player.
    Otherwise returns all serves for user's players.
    """
    try:
        serve_windows = serve_window_service.list_user_serve_windows(
            db=db,
            user_id=current_user["id"],
            player_id=player_id,
            court_side=court_side,
            start_date=start_date,
            end_date=end_date,
            video_id=video_id,
        )

        return [ServeWindowInfo.model_validate(sa) for sa in serve_windows]

    except Exception as e:  # noqa: BLE001
        handle_service_error(e, "get_my_serve_windows", {})


@router.get("/{serve_window_id}", response_model=ServeWindowInfo)
async def get_serve_window(
    serve_window_id: int,
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> ServeWindowInfo:
    """Get details of a specific serve window."""
    try:
        serve_window = serve_window_service.get_serve_window_by_id(
            db=db,
            serve_window_id=serve_window_id,
            user_id=current_user["id"],
        )

        return ServeWindowInfo.model_validate(serve_window)

    except Exception as e:  # noqa: BLE001
        handle_service_error(
            e, "get_serve_window", {"serve_window_id": serve_window_id}
        )


@router.delete("/{serve_window_id}")
async def delete_serve_window(
    serve_window_id: int,
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> Dict[str, str]:
    """Delete a serve window."""
    try:
        # Get serve window to check demo status
        serve_window = serve_window_service.get_serve_window_by_id(
            db=db,
            serve_window_id=serve_window_id,
            user_id=current_user["id"],
        )

        # Get video to check demo status
        video = video_service.get_video_by_id(db, serve_window.video_id)
        if video:
            require_video_not_demo(video, current_user)

        serve_window_service.delete_serve_window(
            db=db,
            serve_window_id=serve_window_id,
            user_id=current_user["id"],
        )

        return {"message": f"Serve window {serve_window_id} deleted successfully"}

    except Exception as e:  # noqa: BLE001
        handle_service_error(
            e, "delete_serve_window", {"serve_window_id": serve_window_id}
        )
