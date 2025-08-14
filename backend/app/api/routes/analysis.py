"""Analysis API routes with proper REST patterns and error handling."""

from typing import List

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
)
from app.api.schemas.common import PaginationParams
from app.core.database import get_db
from app.services.analysis_service import (
    analyze_video,
    delete_analysis,
    get_all_analyses,
    get_analysis_by_id,
    get_analysis_by_video,
)
from app.services.video_service import get_video_by_id
from app.utils.error_handling import (
    handle_not_found_error,
    handle_processing_error,
    log_and_raise_error,
)

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

        return [AnalysisListItem.from_orm(analysis) for analysis in paginated_analyses]
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

        return AnalysisInfo.from_orm(analysis)
    except (OSError, ValueError) as e:
        log_and_raise_error(e, "get_analysis", {"analysis_id": analysis_id})


@router.post("/videos/{video_id}", response_model=AnalysisStartResponse)
async def start_analysis(
    video_id: int, request: AnalysisRequest, db: Session = Depends(get_db)
) -> AnalysisStartResponse:
    """
    Start analysis for a specific video.

    Args:
        video_id: Unique video identifier
        request: Analysis configuration

    Returns:
        Analysis start confirmation with estimated duration
    """
    try:
        # Verify video exists
        video = get_video_by_id(db, video_id)
        if not video:
            raise handle_not_found_error("video", str(video_id))

        # Validate analysis type
        valid_types = [
            AnalysisTypes.BALL_TRACKING,
            AnalysisTypes.POSE_DETECTION,
            AnalysisTypes.COMPREHENSIVE,
        ]
        if request.analysis_type not in valid_types:
            raise handle_processing_error(
                "analysis_start",
                f"Invalid analysis type. Valid types: {', '.join(valid_types)}",
            )

        # Start analysis
        result = analyze_video(
            db=db,
            video_id=video_id,
            analysis_type=request.analysis_type,
            confidence_threshold=request.confidence_threshold,
            include_pose_detection=request.include_pose_detection,
        )

        # Propagate processing failures with consistent error shape
        if isinstance(result, dict) and "error" in result:
            raise handle_processing_error("analysis_start", result["error"])

        return AnalysisStartResponse(
            analysis_id=result.get("analysis_id"),
            video_filename=video.filename,
            status=AnalysisStatus.PROCESSING,
            message="Analysis started successfully",
            estimated_duration=result.get("estimated_duration"),
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
        analysis = get_analysis_by_video(db, video.filename)
        if not analysis:
            raise handle_not_found_error("analysis", f"for video {video_id}")

        return AnalysisInfo.from_orm(analysis)
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

        # Delete analysis
        if delete_analysis(db, video.filename):
            return AnalysisDeleteResponse(
                message=f"Analysis for video {video_id} deleted successfully",
                analysis_id=None,  # We don't know the specific analysis ID
                video_filename=video.filename,
            )
        else:
            raise handle_not_found_error("analysis", f"for video {video_id}")
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
            "progress": analysis.progress if hasattr(analysis, "progress") else None,
            "created_at": analysis.created_at,
            "completed_at": analysis.completed_at,
        }
    except (OSError, ValueError) as e:
        log_and_raise_error(e, "get_analysis_status", {"analysis_id": analysis_id})
