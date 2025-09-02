"""Video quality assessment API routes."""

import logging
import time
from pathlib import Path
from typing import Any, Dict

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.api.schemas.video_quality import (
    VideoQualityAssessmentResponse,
    VideoQualityMetrics,
)
from app.core.database import get_db
from app.services.video_quality import VideoQualityService
from app.services.video_service import get_video_by_id

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/v0/video-quality", tags=["video-quality"])


@router.post("/assess/{video_id}", response_model=VideoQualityAssessmentResponse)
async def assess_video_quality(
    video_id: int,
    db: Session = Depends(get_db),
) -> VideoQualityAssessmentResponse:
    """
    Perform independent video quality assessment.

    This endpoint allows triggering quality assessment independently of upload,
    useful for re-assessment or when quality metrics need updating.

    Args:
        video_id: ID of the video to assess
        db: Database session

    Returns:
        Video quality assessment results

    Raises:
        HTTPException: If video not found or assessment fails
    """
    start_time = time.time()

    try:
        # Get video record
        video = get_video_by_id(db, video_id)
        if not video:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Video with ID {video_id} not found",
            )

        # Check if video file exists
        video_path = Path(video.file_path)
        if not video_path.exists():
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Video file not found at {video.file_path}",
            )

        # Perform quality assessment
        quality_service = VideoQualityService()
        metrics = quality_service.quick_assess(video_path)

        processing_time = time.time() - start_time

        logger.info(f"Independent quality assessment completed for video {video_id}")

        return VideoQualityAssessmentResponse(
            video_id=video_id,
            metrics=VideoQualityMetrics(**metrics),
            assessment_type="quick",
            processing_time_seconds=processing_time,
        )

    except HTTPException:
        # Re-raise HTTP exceptions as-is
        raise
    except (OSError, RuntimeError, ValueError) as e:
        logger.error(f"Error assessing video quality for video {video_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Video quality assessment failed: {e!s}",
        ) from e


@router.get("/{video_id}", response_model=Dict[str, Any])
async def get_video_quality_info(
    video_id: int,
    db: Session = Depends(get_db),
) -> Dict[str, Any]:
    """
    Get current video quality information.

    Returns the quality metrics stored in the video record, if available.

    Args:
        video_id: ID of the video
        db: Database session

    Returns:
        Current video quality information

    Raises:
        HTTPException: If video not found
    """
    try:
        # Get video record
        video = get_video_by_id(db, video_id)
        if not video:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Video with ID {video_id} not found",
            )

        # Extract quality information from video record
        quality_info = {
            "video_id": video_id,
            "filename": video.filename,
            "quality_level": video.quality_level,
            "quality_score": video.quality_score,
            "blur_score": video.blur_score,
            "lighting_score": video.lighting_score,
            "resolution_score": video.resolution_score,
            "recommended_confidence_threshold": video.recommended_confidence_threshold,
            "has_quality_assessment": bool(
                video.quality_level and video.quality_level != "unknown"
            ),
            "assessed_at": video.created_at.isoformat() if video.created_at else None,
        }

        return quality_info

    except HTTPException:
        # Re-raise HTTP exceptions as-is
        raise
    except (OSError, RuntimeError, ValueError) as e:
        logger.error(f"Error retrieving video quality info for video {video_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to retrieve video quality information: {e!s}",
        ) from e
