"""Unified analysis API routes with RQ background task support."""

import logging
from typing import Any, Dict, Optional

from fastapi import APIRouter, Depends, HTTPException, status
from redis.exceptions import ConnectionError as RedisConnectionError
from redis.exceptions import TimeoutError as RedisTimeoutError
from rq import Retry
from rq.job import Job, NoSuchJobError
from sqlalchemy.orm import Session

from app.api.schemas.background_tasks import (
    AnalysisRequest,
    AnalysisResponse,
    TaskListResponse,
    TaskStatsResponse,
    TaskStatus,
)
from app.core.database import get_db
from app.core.redis_config import analysis_queue, redis_conn
from app.dependencies.auth import get_current_user
from app.services import video_service
from app.services.rq_monitoring import get_queue_stats
from app.services.rq_tasks import analyze_pose_detection_rq
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

        # Select RQ task function based on analysis type
        task_function_map = {
            "pose_only": analyze_pose_detection_rq,
        }

        task_function = task_function_map.get(request.analysis_type)
        if not task_function:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid analysis type: {request.analysis_type}",
            )

        # Configure retry based on analysis type
        retry_config = {
            "pose_only": Retry(max=2, interval=60),
        }

        # Configure timeout based on analysis type
        timeout_config = {
            "pose_only": 300,  # 5 minutes
        }

        try:
            logger.info(
                f"Starting analysis request: video_id={video_id}, "
                f"analysis_type={request.analysis_type}, "
                f"confidence_threshold={request.confidence_threshold}"
            )

            # Redis connection is already checked in redis_config.py on module load
            # If Redis is unavailable, the connection will fail when enqueueing, which is handled below

            # Enqueue RQ job
            logger.info(f"Enqueueing {request.analysis_type} job to Redis queue...")
            try:
                job = analysis_queue.enqueue(
                    task_function,
                    video_id=video_id,
                    video_path=video.file_path,
                    confidence_threshold=request.confidence_threshold,
                    retry=retry_config[request.analysis_type],
                    job_timeout=timeout_config[request.analysis_type],
                    result_ttl=3600,  # Keep results for 1 hour
                )
                logger.info(
                    f"Successfully enqueued {request.analysis_type} analysis job {job.id} "
                    f"for video {video_id} to queue '{analysis_queue.name}'"
                )
            except (RedisConnectionError, RedisTimeoutError) as e:
                logger.error(f"Failed to enqueue job to Redis: {e}")
                raise HTTPException(
                    status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                    detail=f"Failed to enqueue job to Redis: {e!s}",
                ) from e

            return AnalysisResponse(
                job_id=job.id,
                video_id=video_id,
                analysis_type=request.analysis_type,
                status="queued",
                message=f"{request.analysis_type} analysis started successfully",
                estimated_duration=_get_estimated_duration(request.analysis_type),
            )

        except HTTPException:
            raise
        except (RedisConnectionError, RedisTimeoutError) as e:
            logger.exception("Redis error while enqueueing job for video %s", video_id)
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="Redis service error. Cannot start analysis. Please check Redis connection.",
            ) from e
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


@router.get("/status/{job_id}", response_model=TaskStatus)
async def get_task_status(
    job_id: str,
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> TaskStatus:
    """
    Get the status of a background analysis job (RQ).

    Args:
        job_id: UUID string identifier of the job to check

    Returns:
        Current job status with progress information
    """
    try:
        # Fetch job from Redis
        try:
            job = Job.fetch(job_id, connection=redis_conn)
        except Exception as e:
            logger.warning(f"Job {job_id} not found in Redis: {e}")
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Job {job_id} not found",
            ) from e

        # Get job status and map RQ statuses to frontend-friendly values
        rq_status = job.get_status()
        mapped_status = _map_rq_status_to_frontend(rq_status)

        # Get job result if available
        job_result = None
        if job.is_finished:
            try:
                job_result = job.result
            except (NoSuchJobError, AttributeError, TypeError) as e:
                # Result may have expired (TTL), job may not exist, or result may be None
                logger.warning(f"Job {job_id} result expired or unavailable: {e}")
                job_result = None

        # Extract video_id from job arguments for authorization
        video_id = _extract_video_id_from_job(job)

        # Require video_id for authorization (fail secure)
        if not video_id:
            logger.warning(
                f"Unable to extract video_id from job {job_id} for authorization check"
            )
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Unable to determine video ownership for authorization",
            )

        # Check authorization via video access
        video = video_service.get_video_by_id(db, video_id)
        if not video:
            logger.warning(f"Job {job_id} references non-existent video {video_id}")
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Video {video_id} not found",
            )

        require_video_access(video, current_user)

        # Build response
        task_status = TaskStatus(
            job_id=job_id,
            video_id=video_id or 0,
            analysis_type=_get_analysis_type_from_job(job),
            status=mapped_status,
            progress=0,  # Client calculates from elapsed time
            error=str(job.exc_info) if job.is_failed else None,
            result=job_result,
            started_at=job.started_at
            if hasattr(job, "started_at") and job.started_at
            else None,
            completed_at=job.ended_at
            if hasattr(job, "ended_at") and job.ended_at
            else None,
            estimated_duration=_get_estimated_duration(
                _get_analysis_type_from_job(job)
            ),
        )

        return task_status

    except HTTPException:
        raise
    except Exception as e:
        logger.exception("Error getting job status for job %s", job_id)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to get job status. Please try again later.",
        ) from e


@router.get("/tasks", response_model=TaskListResponse)
async def list_tasks(
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> TaskListResponse:
    """
    List all active background jobs (RQ) for the current user.

    Returns:
        Dictionary of all active jobs with their status
    """
    try:
        from rq import Queue

        from app.utils.authorization import is_admin

        # Get all jobs from analysis queue
        queue = Queue("analysis", connection=redis_conn)
        job_ids = queue.job_ids

        # Filter jobs by user's videos unless admin
        user_video_ids = None

        if not is_admin(current_user):
            from app.models.video import Video

            user_video_ids = {
                video.id
                for video in db.query(Video)
                .filter(Video.user_id == current_user["id"])
                .all()
            }

        # Fetch and filter jobs
        task_statuses = {}
        status_counts = {}

        for job_id in job_ids:
            try:
                job = Job.fetch(job_id, connection=redis_conn)
                video_id = _extract_video_id_from_job(job)

                # Skip jobs without valid video_id (can't verify ownership)
                if not video_id:
                    logger.debug(
                        f"Skipping job {job_id}: unable to extract video_id for filtering"
                    )
                    continue

                # Filter by user's videos unless admin
                if not is_admin(current_user) and video_id not in user_video_ids:
                    continue

                # Map RQ status to frontend status
                rq_status = job.get_status()
                mapped_status = _map_rq_status_to_frontend(rq_status)

                # Build task status
                task_status = TaskStatus(
                    job_id=job_id,
                    video_id=video_id or 0,
                    analysis_type=_get_analysis_type_from_job(job),
                    status=mapped_status,
                    progress=0,
                    error=str(job.exc_info) if job.is_failed else None,
                    result=job.result if job.is_finished else None,
                    started_at=job.started_at
                    if hasattr(job, "started_at") and job.started_at
                    else None,
                    completed_at=job.ended_at
                    if hasattr(job, "ended_at") and job.ended_at
                    else None,
                    estimated_duration=_get_estimated_duration(
                        _get_analysis_type_from_job(job)
                    ),
                )

                task_statuses[job_id] = task_status
                status_counts[mapped_status] = status_counts.get(mapped_status, 0) + 1

            except (
                NoSuchJobError,
                RedisConnectionError,
                RedisTimeoutError,
                AttributeError,
            ) as e:
                logger.warning(f"Failed to fetch job {job_id}: {e}")
                continue

        return TaskListResponse(
            tasks=task_statuses,
            total_tasks=len(task_statuses),
            status_counts=status_counts,
        )

    except Exception as e:
        logger.exception("Error listing jobs")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to list jobs. Please try again later.",
        ) from e


@router.get("/stats", response_model=TaskStatsResponse)
async def get_task_stats(
    current_user: dict = Depends(get_current_user),
) -> TaskStatsResponse:
    """
    Get background job system statistics (RQ).

    Returns:
        Job system statistics including worker counts and queue status
    """
    try:
        stats = get_queue_stats()

        # Map RQ statuses to frontend statuses
        mapped_status_counts = {}
        for rq_status, count in stats.get("status_counts", {}).items():
            mapped_status = _map_rq_status_to_frontend(rq_status)
            mapped_status_counts[mapped_status] = (
                mapped_status_counts.get(mapped_status, 0) + count
            )

        response_stats = {
            "total_tasks": stats.get("total_jobs", 0),
            "status_counts": mapped_status_counts,
            "active_workers": stats.get("active_workers", 0),
            "max_workers": 1,  # Default for free tier
            "queue_size": stats.get("total_queued", 0),
        }

        return TaskStatsResponse.model_validate(response_stats)

    except Exception as e:
        logger.exception("Error getting job stats")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to get job stats. Please try again later.",
        ) from e


@router.delete("/tasks/{job_id}")
async def cancel_task(
    job_id: str,
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> Dict[str, str]:
    """
    Cancel a running background job (RQ).

    Args:
        job_id: UUID string identifier of the job to cancel

    Returns:
        Cancellation confirmation
    """
    try:
        # Fetch job from Redis
        try:
            job = Job.fetch(job_id, connection=redis_conn)
        except Exception as e:
            logger.warning(f"Job {job_id} not found in Redis: {e}")
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Job {job_id} not found",
            ) from e

        # Extract video_id from job arguments for authorization
        video_id = _extract_video_id_from_job(job)

        # Require video_id for authorization (fail secure)
        if not video_id:
            logger.warning(
                f"Unable to extract video_id from job {job_id} for authorization check"
            )
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Unable to determine video ownership for authorization",
            )

        # Check authorization via video access
        video = video_service.get_video_by_id(db, video_id)
        if not video:
            logger.warning(f"Job {job_id} references non-existent video {video_id}")
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Video {video_id} not found",
            )

        require_video_access(video, current_user)

        # Cancel job (only if queued or started)
        if job.get_status() in ["queued", "started"]:
            job.cancel()
            logger.info(f"Cancelled job {job_id}")
            return {"message": f"Job {job_id} cancelled successfully"}
        else:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Job {job_id} cannot be cancelled (status: {job.get_status()})",
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


def _map_rq_status_to_frontend(rq_status: str) -> str:
    """
    Map RQ job statuses to frontend-friendly status values.

    Args:
        rq_status: RQ job status ('queued', 'started', 'finished', 'failed')

    Returns:
        Frontend-friendly status ('queued', 'processing', 'completed', 'failed', 'cancelled')
    """
    status_map = {
        "queued": "queued",
        "started": "processing",
        "finished": "completed",
        "failed": "failed",
        "deferred": "queued",
        "scheduled": "queued",
    }
    return status_map.get(rq_status, "queued")


def _get_analysis_type_from_job(job: Job) -> str:
    """
    Extract analysis type from RQ job function name.

    Args:
        job: RQ Job object

    Returns:
        Analysis type string
    """
    func_name = job.func_name if hasattr(job, "func_name") else str(job.func)

    if "analyze_pose_detection_rq" in func_name:
        return "pose_only"
    else:
        return "pose_only"  # Default fallback


def _get_estimated_duration(analysis_type: str) -> float:
    """Get estimated duration for different analysis types."""
    estimates = {
        "pose_only": 120.0,  # 2 minutes
    }
    return estimates.get(analysis_type, 120.0)
