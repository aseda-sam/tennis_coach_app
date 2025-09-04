"""Ball detection API routes."""

import json
import logging
from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.api.schemas.ball_detection import (
    BallDetectionRequest,
    BallDetectionResponse,
)
from app.core.database import get_db
from app.models.ball_detection import BallDetection
from app.services.ball_detection import BallDetectionService
from app.services.video_service import get_video_by_id

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/v0/ball-detection", tags=["ball-detection"])


@router.post("/analyze/{video_id}", response_model=BallDetectionResponse)
async def analyze_video_ball_detection(
    video_id: int,
    request: BallDetectionRequest = BallDetectionRequest(),
    db: Session = Depends(get_db),
) -> BallDetectionResponse:
    """
    Perform ball detection analysis on a video.

    This endpoint analyzes a video for tennis ball detection using YOLO models.
    The appropriate model is selected based on video quality.
    """
    try:
        # Verify video exists
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
                detail=f"Video file not found: {video.file_path}",
            )

        # Check if ball detection already exists
        ball_detection_service = BallDetectionService()
        existing_detection = ball_detection_service.get_detection_by_video_id(
            db, video_id
        )

        if existing_detection:
            logger.info(
                f"Ball detection already exists for video {video_id}, "
                f"returning existing results"
            )
            return _convert_to_response(
                existing_detection, request.include_detection_data
            )

        # Route through background service for proper task management
        from app.services.background_service import background_service

        # Start background task for ball detection
        task_id = background_service.start_analysis_task(
            video_id=video_id,
            analysis_type="ball_only",
            confidence_threshold=request.confidence_threshold,
        )

        logger.info(
            f"Ball detection analysis started in background for video {video_id}"
        )
        return BallDetectionResponse(
            ball_detection_id=None,  # Will be created by background task
            video_filename=video.filename,
            status="processing",
            message="Ball detection analysis started in background",
            estimated_duration=180,  # 3 minutes estimate
            task_id=task_id,
        )

    except HTTPException:
        # Re-raise HTTP exceptions as-is
        raise
    except (OSError, RuntimeError, ValueError) as e:
        logger.error(f"Error analyzing ball detection for video {video_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Ball detection analysis failed: {e!s}",
        ) from e


@router.get("/{video_id}", response_model=BallDetectionResponse)
async def get_ball_detection_results(
    video_id: int,
    include_detection_data: bool = False,
    db: Session = Depends(get_db),
) -> BallDetectionResponse:
    """
    Get ball detection results for a video.

    Returns existing ball detection results if available.
    Use the analyze endpoint to trigger new detection analysis.
    """
    try:
        # Verify video exists
        video = get_video_by_id(db, video_id)
        if not video:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Video with ID {video_id} not found",
            )

        # Get ball detection results
        ball_detection_service = BallDetectionService()
        ball_detection = ball_detection_service.get_detection_by_video_id(db, video_id)

        if not ball_detection:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=(
                    f"No ball detection results found for video {video_id}. "
                    f"Use the analyze endpoint to trigger detection."
                ),
            )

        return _convert_to_response(ball_detection, include_detection_data)

    except HTTPException:
        # Re-raise HTTP exceptions as-is
        raise
    except (OSError, RuntimeError, ValueError) as e:
        logger.error(
            f"Error retrieving ball detection results for video {video_id}: {e}"
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to retrieve ball detection results: {e!s}",
        ) from e


def _convert_to_response(
    ball_detection: BallDetection, include_detection_data: bool = False
) -> BallDetectionResponse:
    """
    Convert BallDetection model to API response.

    Args:
        ball_detection: BallDetection database model
        include_detection_data: Whether to include raw detection data

    Returns:
        BallDetectionResponse with formatted data
    """
    from app.api.schemas.ball_detection import BallDetectionMetrics

    # Create metrics object
    metrics = BallDetectionMetrics(
        total_frames=ball_detection.total_frames,
        frames_with_balls=ball_detection.frames_with_balls,
        total_detections=ball_detection.total_ball_detections,
        detection_rate=ball_detection.detection_rate,
        average_detections_per_frame=ball_detection.average_detections_per_frame,
        model_used=ball_detection.model_used,
        confidence_threshold=ball_detection.confidence_threshold,
        model_selection_reason=ball_detection.model_selection_reason,
        average_confidence=ball_detection.average_confidence,
        min_confidence=ball_detection.min_confidence,
        max_confidence=ball_detection.max_confidence,
        processing_time_seconds=ball_detection.processing_time_seconds,
        frame_processing_rate=ball_detection.frame_processing_rate,
    )

    # Parse detection data if requested
    detection_data = None
    if include_detection_data and ball_detection.detection_data:
        try:
            detection_data = json.loads(ball_detection.detection_data)
        except json.JSONDecodeError:
            logger.warning(
                f"Failed to parse detection data for detection {ball_detection.id}"
            )

    return BallDetectionResponse(
        id=ball_detection.id,
        video_id=ball_detection.video_id,
        status=ball_detection.status,
        metrics=metrics,
        detection_data=detection_data,
        created_at=ball_detection.created_at,
        completed_at=ball_detection.completed_at,
    )
