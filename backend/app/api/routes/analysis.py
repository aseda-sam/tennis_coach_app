"""Analysis API routes with proper REST patterns and error handling."""

import logging
from typing import Any, Dict, List

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.api.schemas.analysis import (
    AnalysisDeleteResponse,
    AnalysisInfo,
    AnalysisListItem,
    AnalysisRequest,
    AnalysisStartResponse,
    AnalysisStatus,
    AnalysisTypes,
    TaskListResponse,
    TaskStatsResponse,
    TaskStatus,
)
from app.api.schemas.common import PaginationParams
from app.core.database import get_db
from app.services.analysis_service import (
    delete_analysis,
    get_all_analyses,
    get_analysis_by_id,
    get_analysis_by_video,
    get_analysis_by_video_id,
)
from app.services.background_service import background_service
from app.services.video_service import get_video_by_id
from app.utils.error_handling import (
    handle_not_found_error,
    handle_processing_error,
    log_and_raise_error,
)

logger = logging.getLogger(__name__)

router = APIRouter()


@router.get("/", response_model=List[AnalysisListItem])
async def list_analyses(
    pagination: PaginationParams = Depends(), db: Session = Depends(get_db)
) -> List[AnalysisListItem]:
    """
    List all analysis results.

    Returns a paginated list of analyses with basic information.
    """
    try:
        analyses = get_all_analyses(db)

        # Apply pagination
        start_idx = (pagination.page - 1) * pagination.size
        end_idx = start_idx + pagination.size
        paginated_analyses = analyses[start_idx:end_idx]

        return [
            AnalysisListItem.model_validate(analysis) for analysis in paginated_analyses
        ]
    except (OSError, ValueError) as e:
        log_and_raise_error(e, "list_analyses")


@router.get("/{analysis_id}", response_model=AnalysisInfo)
async def get_analysis(analysis_id: int, db: Session = Depends(get_db)) -> AnalysisInfo:
    """
    Get detailed analysis results.

    Args:
        analysis_id: Unique analysis identifier

    Returns:
        Complete analysis information including results
    """
    try:
        analysis = get_analysis_by_id(db, analysis_id)
        if not analysis:
            raise handle_not_found_error("analysis", str(analysis_id))

        return AnalysisInfo.model_validate(analysis)
    except (OSError, ValueError) as e:
        log_and_raise_error(e, "get_analysis", {"analysis_id": analysis_id})


@router.post("/videos/{video_id}", response_model=AnalysisStartResponse)
async def start_analysis(
    video_id: int, request: AnalysisRequest, db: Session = Depends(get_db)
) -> AnalysisStartResponse:
    """
    Start analysis for a specific video in the background.

    Args:
        video_id: Unique video identifier
        request: Analysis configuration

    Returns:
        Analysis start confirmation with task ID for tracking
    """
    try:
        # Verify video exists
        video = get_video_by_id(db, video_id)
        if not video:
            raise handle_not_found_error("video", str(video_id))

        # Validate analysis type
        valid_types = [
            AnalysisTypes.BALL_ONLY,
            AnalysisTypes.RACKET_ONLY,
            AnalysisTypes.POSE_ONLY,
            AnalysisTypes.COMPREHENSIVE,
            AnalysisTypes.CUSTOM,
        ]
        if request.analysis_type not in valid_types:
            raise handle_processing_error(
                "analysis_start",
                f"Invalid analysis type. Valid types: {', '.join(valid_types)}",
            )

        # Check if analysis already exists and is completed
        existing_analysis = get_analysis_by_video_id(db, video_id)
        if existing_analysis and existing_analysis.status == "completed":
            return AnalysisStartResponse(
                analysis_id=existing_analysis.id,
                video_filename=video.filename,
                status=AnalysisStatus.COMPLETED,
                message="Analysis already exists",
                estimated_duration=0,
                task_id=None,
            )

        # Check if there's an active background task processing this video
        if existing_analysis and existing_analysis.status == "processing":
            active_task = background_service.get_active_task_for_video(video_id)
            if active_task:
                return AnalysisStartResponse(
                    analysis_id=existing_analysis.id,
                    video_filename=video.filename,
                    status=AnalysisStatus.PROCESSING,
                    message="Analysis already in progress",
                    estimated_duration=300,  # 5 minutes estimate
                    task_id=active_task["task_id"],
                )

        # If analysis exists but failed or processing without active task, delete it and start fresh
        if existing_analysis:
            db.delete(existing_analysis)
            db.commit()

        # Don't create analysis record yet - let background task do it
        # This prevents the background task from finding an empty record

        # Check if synchronous mode is requested
        if request.synchronous:
            # Run analysis synchronously (for testing)
            from app.services.analysis_service import analyze_video

            analysis_result = analyze_video(
                db=db,
                video_id=video_id,
                analysis_type=request.analysis_type,
                confidence_threshold=request.confidence_threshold,
                include_pose_detection=request.include_pose_detection,
            )

            # Check for errors in synchronous mode
            if isinstance(analysis_result, dict) and "error" in analysis_result:
                raise handle_processing_error("analysis", analysis_result["error"])

            # Get the analysis record created by analyze_video
            analysis_record = get_analysis_by_video_id(db, video_id)
            if not analysis_record:
                raise handle_processing_error(
                    "analysis", "Failed to create analysis record"
                )

            return AnalysisStartResponse(
                analysis_id=analysis_record.id,
                video_filename=video.filename,
                status=AnalysisStatus.COMPLETED,
                message="Analysis completed synchronously",
                estimated_duration=analysis_result.get("processing_time", 0.0),
                task_id=None,
            )
        else:
            # Start background task
            task_id = background_service.start_analysis_task(
                video_id=video_id,
                analysis_type=request.analysis_type,
                confidence_threshold=request.confidence_threshold,
                include_pose_detection=request.include_pose_detection,
            )

            return AnalysisStartResponse(
                analysis_id=None,  # Will be created by background task
                video_filename=video.filename,
                status=AnalysisStatus.PROCESSING,
                message="Analysis started in background",
                estimated_duration=300,  # 5 minutes estimate
                task_id=task_id,
            )
    except (OSError, ValueError, RuntimeError) as e:
        log_and_raise_error(e, "start_analysis", {"video_id": video_id})


@router.get("/videos/{video_id}", response_model=AnalysisInfo)
async def get_video_analysis(
    video_id: int, db: Session = Depends(get_db)
) -> AnalysisInfo:
    """
    Get analysis results for a specific video.

    Args:
        video_id: Unique video identifier

    Returns:
        Analysis results for the video
    """
    try:
        # Verify video exists
        video = get_video_by_id(db, video_id)
        if not video:
            raise handle_not_found_error("video", str(video_id))

        # Get analysis
        # Prefer lookup by strong ID if available
        analysis = get_analysis_by_video_id(db, video_id)
        if not analysis:
            analysis = get_analysis_by_video(db, video.filename)
        if not analysis:
            raise handle_not_found_error("analysis", f"for video {video_id}")

        return AnalysisInfo.model_validate(analysis)
    except (OSError, ValueError) as e:
        log_and_raise_error(e, "get_video_analysis", {"video_id": video_id})


@router.delete("/{analysis_id}", response_model=AnalysisDeleteResponse)
async def delete_analysis_results(
    analysis_id: int, db: Session = Depends(get_db)
) -> AnalysisDeleteResponse:
    """
    Delete analysis results.

    Args:
        analysis_id: Unique analysis identifier

    Returns:
        Deletion confirmation
    """
    try:
        # Get analysis to verify it exists
        analysis = get_analysis_by_id(db, analysis_id)
        if not analysis:
            raise handle_not_found_error("analysis", str(analysis_id))

        # Delete analysis
        if delete_analysis(db, analysis.video_filename):
            return AnalysisDeleteResponse(
                message=f"Analysis {analysis_id} deleted successfully",
                analysis_id=analysis_id,
                video_filename=analysis.video_filename,
            )
        else:
            raise handle_processing_error("delete_analysis", "Database deletion failed")
    except (OSError, ValueError) as e:
        log_and_raise_error(e, "delete_analysis_results", {"analysis_id": analysis_id})


@router.delete("/videos/{video_id}")
async def delete_video_analysis(
    video_id: int, db: Session = Depends(get_db)
) -> AnalysisDeleteResponse:
    """
    Delete analysis results for a specific video.

    Args:
        video_id: Unique video identifier

    Returns:
        Deletion confirmation
    """
    try:
        # Verify video exists
        video = get_video_by_id(db, video_id)
        if not video:
            raise handle_not_found_error("video", str(video_id))

        # Get analysis to retrieve its ID before deletion
        analysis = get_analysis_by_video_id(db, video_id)
        if not analysis:
            raise handle_not_found_error("analysis", f"for video {video_id}")

        analysis_id = analysis.id
        video_filename = video.filename

        # Delete analysis
        if delete_analysis(db, video.filename):
            return AnalysisDeleteResponse(
                message=f"Analysis for video {video_id} deleted successfully",
                analysis_id=analysis_id,
                video_filename=video_filename,
            )
        else:
            raise handle_processing_error("delete_analysis", "Database deletion failed")
    except (OSError, ValueError) as e:
        log_and_raise_error(e, "delete_video_analysis", {"video_id": video_id})


@router.get("/status/{analysis_id}")
async def get_analysis_status(analysis_id: int, db: Session = Depends(get_db)) -> dict:
    """
    Get the current status of an analysis.

    Args:
        analysis_id: Unique analysis identifier

    Returns:
        Analysis status information
    """
    try:
        analysis = get_analysis_by_id(db, analysis_id)
        if not analysis:
            raise handle_not_found_error("analysis", str(analysis_id))

        return {
            "analysis_id": analysis_id,
            "status": analysis.status,
            "progress": analysis.progress,
            "created_at": analysis.created_at,
            "completed_at": analysis.completed_at,
        }
    except (OSError, ValueError) as e:
        log_and_raise_error(e, "get_analysis_status", {"analysis_id": analysis_id})


# Background task management endpoints
@router.get("/tasks/{task_id}/status", response_model=TaskStatus)
async def get_task_status(task_id: int) -> TaskStatus:
    """
    Get the status of a background analysis task.

    Args:
        task_id: Background task ID

    Returns:
        Task status and progress information
    """
    try:
        task_status = background_service.get_task_status(task_id)
        if not task_status:
            raise handle_not_found_error("task", str(task_id))

        return TaskStatus(**task_status)
    except (OSError, ValueError) as e:
        log_and_raise_error(e, "get_task_status", {"task_id": task_id})


@router.get("/tasks/", response_model=TaskListResponse)
async def list_tasks() -> TaskListResponse:
    """
    List all background tasks.

    Returns:
        All active background tasks with their status
    """
    try:
        tasks = background_service.get_all_tasks()
        return TaskListResponse(
            tasks={task_id: TaskStatus(**task) for task_id, task in tasks.items()},
            total=len(tasks),
        )
    except (OSError, ValueError) as e:
        log_and_raise_error(e, "list_tasks")


@router.get("/tasks/stats", response_model=TaskStatsResponse)
async def get_task_stats() -> TaskStatsResponse:
    """
    Get background task statistics.

    Returns:
        Task statistics including counts and worker information
    """
    try:
        stats = background_service.get_task_stats()
        return TaskStatsResponse(**stats)
    except (OSError, ValueError) as e:
        log_and_raise_error(e, "get_task_stats")


@router.get("/tasks/{task_id}/logs")
async def get_task_logs(task_id: int) -> Dict[str, Any]:
    """
    Get detailed logs for a specific task.

    Args:
        task_id: Task ID

    Returns:
        Task logs and status information
    """
    try:
        task_info = background_service.get_task_status(task_id)
        if not task_info:
            raise handle_not_found_error("task", str(task_id))
        
        # Get additional task details
        all_tasks = background_service.get_all_tasks()
        task_details = all_tasks.get(task_id, {})
        
        return {
            "task_id": task_id,
            "status": task_info.status,
            "progress": task_info.progress,
            "current_stage": task_info.current_stage,
            "stage_message": task_info.stage_message,
            "error": task_info.error,
            "started_at": task_info.started_at,
            "completed_at": task_info.completed_at,
            "include_pose_detection": task_details.get("include_pose_detection", False),
            "analysis_type": task_details.get("analysis_type", "unknown"),
            "confidence_threshold": task_details.get("confidence_threshold", 0.0),
        }
    except (OSError, ValueError) as e:
        log_and_raise_error(e, "get_task_logs", {"task_id": task_id})


@router.delete("/tasks/{task_id}")
async def cancel_task(task_id: int) -> Dict[str, Any]:
    """
    Cancel a background analysis task.

    Args:
        task_id: Background task ID

    Returns:
        Cancellation confirmation
    """
    try:
        success = background_service.cancel_task(task_id)
        if not success:
            raise handle_not_found_error("task", str(task_id))

        return {
            "message": "Task cancelled successfully",
            "task_id": task_id,
        }
    except (OSError, ValueError) as e:
        log_and_raise_error(e, "cancel_task", {"task_id": task_id})
