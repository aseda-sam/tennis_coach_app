"""Overlay data API routes for client-side rendering."""

import logging
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.api.schemas.overlay_data import PoseOverlayData
from app.core.database import get_db
from app.dependencies.auth import get_optional_user
from app.services import overlay_data_service, video_service
from app.utils.authorization import require_video_access_or_public_demo
from app.utils.error_handling import handle_not_found_error, log_and_raise_error

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/v0/videos", tags=["overlay-data"])


@router.get("/{video_id}/overlay-data", response_model=PoseOverlayData)
async def get_overlay_data(
    video_id: int,
    current_user: Optional[dict] = Depends(get_optional_user),
    db: Session = Depends(get_db),
) -> PoseOverlayData:
    """
    Get overlay data for client-side rendering.

    Formats existing pose detection data for frontend overlay rendering.
    No new analysis - just formatting existing data.

    Args:
        video_id: Video ID to get overlay data for

    Returns:
        PoseOverlayData with frame-by-frame pose keypoints
    """
    try:
        # Verify video exists and check authorization
        video = video_service.get_video_by_id(db, video_id)
        if not video:
            raise handle_not_found_error("video", str(video_id))

        require_video_access_or_public_demo(video, current_user)

        overlay_data = overlay_data_service.format_overlay_data(db, video_id)
        return overlay_data

    except ValueError as e:
        error_msg = str(e).lower()
        # Map "no pose detection/data" errors to 404
        if "no pose detection" in error_msg or "no pose data" in error_msg:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=str(e),
            ) from e
        # Map "exceeds" errors to 400 (validation error)
        if "exceeds" in error_msg:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=str(e),
            ) from e
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        ) from e
    except RuntimeError as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e),
        ) from e
    except HTTPException:
        raise
    except Exception as e:  # noqa: BLE001 - Catch all unexpected errors for API endpoint
        log_and_raise_error(e, "get_overlay_data", {"video_id": video_id})
