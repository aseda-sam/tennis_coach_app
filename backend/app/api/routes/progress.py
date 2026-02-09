"""Progress overview API routes."""

import logging
from typing import Optional

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.api.schemas.progress import ProgressResponse
from app.core.database import get_db
from app.dependencies.auth import get_current_user
from app.services import progress_service
from app.utils.error_handling import log_and_raise_error

logger = logging.getLogger(__name__)

router = APIRouter(tags=["progress"])


@router.get("/me", response_model=ProgressResponse)
async def get_my_progress(
    time_period: str = Query(
        default="30d",
        description="Time window: '7d', '30d', or 'all'",
        pattern="^(7d|30d|all)$",
    ),
    player_id: Optional[int] = Query(
        default=None, description="Filter by specific player"
    ),
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> ProgressResponse:
    """Get aggregated progress overview for the authenticated user."""
    try:
        return progress_service.get_progress(
            db=db,
            user_id=current_user["id"],
            player_id=player_id,
            time_period=time_period,
        )
    except Exception as e:  # noqa: BLE001 - Catch all unexpected errors for API endpoint
        log_and_raise_error(e, "get_my_progress", {"time_period": time_period})
