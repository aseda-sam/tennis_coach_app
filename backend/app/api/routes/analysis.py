"""Unified analysis API routes with RQ background task support."""

import logging
import uuid
from datetime import datetime
from typing import Dict, Optional

from fastapi import APIRouter, Depends, HTTPException, status
from rq.job import Job
from sqlalchemy.orm import Session

from app.api.schemas.background_tasks import AnalysisRequest, AnalysisResponse
from app.core.database import get_db
from app.core.redis_config import analysis_queue, redis_conn
from app.dependencies.auth import get_current_user
from app.models.video_job import VideoJob
from app.services import video_service
from app.services.rq_tasks import enqueue_pose_analysis
from app.utils.authorization import require_video_access, require_video_not_demo

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/v0/analysis", tags=["analysis"])


@router.post("/videos/{video_id}", response_model=AnalysisResponse)
async def start_analysis(
    video_id: int,
    request: AnalysisRequest,
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> AnalysisResponse:
    """
    Start a background analysis task for a video.

    This endpoint provides a unified interface for starting different types of analysis:
    - pose_only: Extract player pose keypoints using MediaPipe

    Args:
        video_id: ID of the video to analyze
        request: Analysis configuration including type and confidence threshold

    Returns:
        Analysis response with task ID and status
    """
    try:
        # Verify video exists
        video = video_service.get_video_by_id(db, video_id)
        if not video:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Video with ID {video_id} not found",
            )

        # Check authorization (only video owner can start analysis)
        require_video_access(video, current_user)

        # Prevent re-running analysis on demo videos
        require_video_not_demo(video, current_user)

        # Validate analysis type
        if request.analysis_type != "pose_only":
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid analysis type: {request.analysis_type}",
            )

        try:
            logger.info(
                f"Starting analysis request: video_id={video_id}, "
                f"analysis_type={request.analysis_type}, "
                f"confidence_threshold={request.confidence_threshold}"
            )

            # Redis connection is already checked in redis_config.py on module load
            # If Redis is unavailable, the connection will fail when enqueueing, which is handled below

            # Create VideoJob record BEFORE enqueuing (status='queued')
            video_job = VideoJob(
                video_id=video_id,
                user_id=current_user["id"],
                job_type=request.analysis_type,
                status="queued",
            )
            db.add(video_job)
            db.commit()
            db.refresh(video_job)

            # Enqueue RQ job using shared helper
            logger.info(f"Enqueueing {request.analysis_type} job to Redis queue...")
            try:
                job = enqueue_pose_analysis(
                    video_id=video_id,
                    video_path=video.file_path,
                    confidence_threshold=request.confidence_threshold,
                    video_job_id=str(
                        video_job.id
                    ),  # Pass VideoJob ID for status updates
                )
                if not job:
                    # Helper returned None (Redis unavailable)
                    # Update VideoJob status to failed
                    video_job.status = "failed"
                    video_job.error = "Failed to enqueue job to Redis"
                    db.commit()
                    raise HTTPException(
                        status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                        detail="Failed to enqueue job to Redis. Please check Redis connection.",
                    )

                # Store RQ job ID for debugging correlation
                video_job.rq_job_id = job.id
                db.commit()

                logger.info(
                    f"Successfully enqueued {request.analysis_type} analysis job {job.id} "
                    f"for video {video_id} to queue '{analysis_queue.name}'"
                )
            except HTTPException:
                raise

            return AnalysisResponse(
                job_id=str(video_job.id),  # Return VideoJob ID, not RQ job ID
                video_id=video_id,
                analysis_type=request.analysis_type,
                status="queued",
                message=f"{request.analysis_type} analysis started successfully",
                estimated_duration=_get_estimated_duration(request.analysis_type),
            )

        except HTTPException:
            raise
        except Exception as e:
            logger.exception("Failed to enqueue job for video %s", video_id)
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to start analysis. Please try again later.",
            ) from e

    except HTTPException:
        raise
    except Exception as e:
        logger.exception("Error starting analysis for video %s", video_id)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to start analysis. Please try again later.",
        ) from e


@router.delete("/tasks/{job_id}")
async def cancel_task(
    job_id: str,
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> Dict[str, str]:
    """
    Cancel a running background job.

    Supports both VideoJob UUIDs (new) and RQ job IDs (legacy).

    Args:
        job_id: VideoJob UUID (new) or RQ job ID (legacy)

    Returns:
        Cancellation confirmation
    """
    try:
        # Try to interpret as VideoJob UUID first (new system)
        video_job = None
        rq_job_id = None

        try:
            job_uuid = uuid.UUID(job_id)
            video_job = db.query(VideoJob).filter(VideoJob.id == job_uuid).first()
            if video_job:
                # Check authorization via video access
                video = video_service.get_video_by_id(db, video_job.video_id)
                if not video:
                    raise HTTPException(
                        status_code=status.HTTP_404_NOT_FOUND,
                        detail=f"Video {video_job.video_id} not found",
                    )
                require_video_access(video, current_user)

                # Get RQ job ID from VideoJob
                if video_job.rq_job_id:
                    rq_job_id = video_job.rq_job_id
                else:
                    raise HTTPException(
                        status_code=status.HTTP_400_BAD_REQUEST,
                        detail=f"Job {job_id} has no associated RQ job to cancel",
                    )
        except (ValueError, TypeError):
            # Not a UUID, treat as legacy RQ job ID
            rq_job_id = job_id

        # Fetch RQ job
        if not rq_job_id:
            rq_job_id = job_id

        try:
            job = Job.fetch(rq_job_id, connection=redis_conn)
        except Exception as e:
            logger.warning(f"RQ job {rq_job_id} not found in Redis: {e}")
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Job {job_id} not found",
            ) from e

        # For legacy RQ job IDs, check authorization via job arguments
        if not video_job:
            video_id = _extract_video_id_from_job(job)
            if not video_id:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="Unable to determine video ownership for authorization",
                )
            video = video_service.get_video_by_id(db, video_id)
            if not video:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail=f"Video {video_id} not found",
                )
            require_video_access(video, current_user)

        # Cancel job (only if queued or started)
        job_status = job.get_status()
        if job_status in ["queued", "started"]:
            job.cancel()

            # Update VideoJob status if it exists
            if video_job:
                video_job.status = "failed"
                video_job.error = "Cancelled by user"
                video_job.finished_at = datetime.utcnow()
                db.commit()

            logger.info(f"Cancelled job {job_id} (RQ: {rq_job_id})")
            return {"message": f"Job {job_id} cancelled successfully"}
        else:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Job {job_id} cannot be cancelled (status: {job_status})",
            )

    except HTTPException:
        raise
    except Exception as e:
        logger.exception("Error cancelling job %s", job_id)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to cancel job. Please try again later.",
        ) from e


def _extract_video_id_from_job(job: Job) -> Optional[int]:
    """
    Extract video_id from RQ job arguments.

    RQ jobs can have arguments in either:
    - job.args (positional arguments) - legacy support
    - job.kwargs (keyword arguments) - current implementation

    Args:
        job: RQ Job object

    Returns:
        video_id if found and valid (positive integer), None otherwise
    """
    video_id = None

    # Check positional arguments first (legacy support)
    if job.args and len(job.args) > 0:
        video_id = job.args[0]

    # Check keyword arguments (current implementation)
    elif job.kwargs and "video_id" in job.kwargs:
        video_id = job.kwargs["video_id"]

    # Validate that video_id is a positive integer
    if video_id is not None:
        if not isinstance(video_id, int):
            logger.warning(
                f"Invalid video_id type in job {job.id}: {type(video_id)}, expected int"
            )
            return None
        if video_id <= 0:
            logger.warning(
                f"Invalid video_id value in job {job.id}: {video_id}, "
                f"expected positive integer"
            )
            return None

    return video_id


def _get_estimated_duration(analysis_type: str) -> float:
    """Get estimated duration for different analysis types."""
    estimates = {
        "pose_only": 120.0,  # 2 minutes
    }
    return estimates.get(analysis_type, 120.0)
