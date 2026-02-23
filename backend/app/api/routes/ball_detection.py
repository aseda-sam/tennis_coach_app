"""Ball detection API routes."""

import logging
import time

from fastapi import APIRouter, Depends, HTTPException, status
from rq import Retry
from sqlalchemy.orm import Session

from app.api.schemas.ball_detection import BallDetectionJobResponse
from app.core.config import settings
from app.core.database import get_db
from app.core.redis_config import analysis_queue
from app.dependencies.auth import get_current_user
from app.models.serve_window import ServeWindow
from app.services import video_job_service, video_service
from app.services.rq_tasks import run_ball_detection_rq
from app.utils.authorization import require_video_access, require_video_not_demo

logger = logging.getLogger(__name__)

router = APIRouter()


@router.post(
    "/videos/{video_id}/ball-detection",
    response_model=BallDetectionJobResponse,
)
async def start_ball_detection(
    video_id: int,
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> BallDetectionJobResponse:
    """
    Start ball detection for a video's accepted serve windows.

    Runs YOLO + ByteTrack ball detection, auto-detects contact timestamps,
    and recomputes biomechanics to populate toss metrics.

    Args:
        video_id: ID of the video to run ball detection on

    Returns:
        Job status with tracking ID
    """
    # Verify video exists
    video = video_service.get_video_by_id(db, video_id)
    if not video:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Video with ID {video_id} not found",
        )

    require_video_access(video, current_user)
    require_video_not_demo(video, current_user)

    # Validate: video must have accepted serve windows
    accepted_count = (
        db.query(ServeWindow)
        .filter(
            ServeWindow.video_id == video_id,
            ServeWindow.status == "accepted",
        )
        .count()
    )
    if accepted_count == 0:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Video has no accepted serve windows. Run analysis first.",
        )

    # Create VideoJob for status tracking
    video_job = video_job_service.create_video_job(
        db=db,
        video_id=video_id,
        user_id=current_user["id"],
        job_type="ball_detection",
        status="queued",
    )

    # Enqueue RQ job
    try:
        rq_job = analysis_queue.enqueue(
            run_ball_detection_rq,
            video_id=video_id,
            user_id=current_user["id"],
            video_job_id=str(video_job.id),
            retry=Retry(max=2, interval=0),
            job_timeout=settings.POSE_DETECTION_JOB_TIMEOUT_SECONDS,
            result_ttl=3600,
            meta={"enqueued_at": time.time()},
        )
    except Exception as e:
        video_job.status = "failed"
        video_job.error = f"Failed to enqueue: {e}"
        db.commit()
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Failed to enqueue ball detection job. Check Redis connection.",
        ) from e

    video_job.rq_job_id = rq_job.id
    db.commit()

    logger.info(
        "Enqueued ball detection job %s (RQ: %s) for video %s",
        video_job.id,
        rq_job.id,
        video_id,
    )

    return BallDetectionJobResponse(
        job_id=str(video_job.id),
        video_id=video_id,
        status="queued",
        message=f"Ball detection started for {accepted_count} serve window(s)",
        estimated_duration=60.0,
    )
