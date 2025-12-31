"""Unified analysis API routes with background task support."""

import logging
from typing import Dict

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.api.schemas.background_tasks import (
    AnalysisRequest,
    AnalysisResponse,
    TaskListResponse,
    TaskStatsResponse,
    TaskStatus,
)
from app.core.database import get_db
from app.dependencies.auth import get_current_user
from app.services import video_service
from app.services.background_service import background_service
from app.utils.authorization import require_video_access

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
    - ball_only: Detect tennis balls using YOLO
    - video_annotation_only: Create annotated videos with detection overlays
    - pose_with_annotation: Extract pose keypoints AND create annotated video

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

        # Start background task
        task_id = background_service.start_analysis_task(
            video_id=video_id,
            analysis_type=request.analysis_type,
            confidence_threshold=request.confidence_threshold,
        )

        logger.info(
            f"Started {request.analysis_type} analysis task {task_id} for video {video_id}"
        )

        # Get initial task status
        task_status = background_service.get_task_status(task_id)
        if not task_status:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to create analysis task",
            )

        return AnalysisResponse(
            task_id=task_id,
            video_id=video_id,
            analysis_type=request.analysis_type,
            status=task_status["status"],
            message=f"{request.analysis_type} analysis started successfully",
            estimated_duration=_get_estimated_duration(request.analysis_type),
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error starting analysis for video {video_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to start analysis: {e!s}",
        ) from e


@router.get("/status/{task_id}", response_model=TaskStatus)
async def get_task_status(
    task_id: int,
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> TaskStatus:
    """
    Get the status of a background analysis task.

    Args:
        task_id: ID of the task to check

    Returns:
        Current task status with progress information
    """
    try:
        task_status = background_service.get_task_status(task_id)
        if not task_status:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Task {task_id} not found",
            )

        # Check authorization via video access
        video_id = task_status.get("video_id")
        if video_id:
            video = video_service.get_video_by_id(db, video_id)
            if video:
                require_video_access(video, current_user)

        return TaskStatus.model_validate(task_status)

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting task status for task {task_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get task status: {e!s}",
        ) from e


@router.get("/tasks", response_model=TaskListResponse)
async def list_tasks(
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> TaskListResponse:
    """
    List all active background tasks for the current user.

    Returns:
        Dictionary of all active tasks with their status
    """
    try:
        from app.utils.authorization import is_admin

        all_tasks = background_service.get_all_tasks()

        # Filter tasks by user's videos unless admin
        filtered_tasks = {}
        if not is_admin(current_user):
            from app.models.video import Video

            user_video_ids = {
                video.id
                for video in db.query(Video)
                .filter(Video.user_id == current_user["id"])
                .all()
            }
            for task_id, task_data in all_tasks.items():
                if task_data.get("video_id") in user_video_ids:
                    filtered_tasks[task_id] = task_data
        else:
            filtered_tasks = all_tasks

        # Convert to TaskStatus objects
        task_statuses = {}
        status_counts = {}

        for task_id, task_data in filtered_tasks.items():
            task_status = TaskStatus.model_validate(task_data)
            task_statuses[task_id] = task_status

            # Count statuses
            status = task_data.get("status", "unknown")
            status_counts[status] = status_counts.get(status, 0) + 1

        return TaskListResponse(
            tasks=task_statuses,
            total_tasks=len(filtered_tasks),
            status_counts=status_counts,
        )

    except Exception as e:
        logger.error(f"Error listing tasks: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to list tasks: {e!s}",
        ) from e


@router.get("/stats", response_model=TaskStatsResponse)
async def get_task_stats(
    current_user: dict = Depends(get_current_user),
) -> TaskStatsResponse:
    """
    Get background task system statistics.

    Returns:
        Task system statistics including worker counts and queue status
    """
    try:
        stats = background_service.get_task_stats()
        return TaskStatsResponse.model_validate(stats)

    except Exception as e:
        logger.error(f"Error getting task stats: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get task stats: {e!s}",
        ) from e


@router.delete("/tasks/{task_id}")
async def cancel_task(
    task_id: int,
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> Dict[str, str]:
    """
    Cancel a running background task.

    Args:
        task_id: ID of the task to cancel

    Returns:
        Cancellation confirmation
    """
    try:
        # Check authorization via video access
        task_status = background_service.get_task_status(task_id)
        if not task_status:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Task {task_id} not found",
            )

        video_id = task_status.get("video_id")
        if video_id:
            video = video_service.get_video_by_id(db, video_id)
            if video:
                require_video_access(video, current_user)

        success = background_service.cancel_task(task_id)
        if not success:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Task {task_id} cannot be cancelled",
            )

        return {"message": f"Task {task_id} cancelled successfully"}

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error cancelling task {task_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to cancel task: {e!s}",
        ) from e


def _get_estimated_duration(analysis_type: str) -> float:
    """Get estimated duration for different analysis types."""
    estimates = {
        "pose_only": 120.0,  # 2 minutes
        "ball_only": 180.0,  # 3 minutes
        "video_annotation_only": 90.0,  # 1.5 minutes
        "pose_with_annotation": 210.0,  # 3.5 minutes (pose + annotation)
    }
    return estimates.get(analysis_type, 180.0)
