"""Admin-only API routes for maintenance and cleanup."""

import logging
from datetime import datetime
from typing import List, Optional

from fastapi import APIRouter, Depends, File, HTTPException, Query, UploadFile, status
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.api.schemas.background_tasks import AnalysisResponse
from app.api.schemas.video import VideoInfo, VideoMetadata, VideoUploadResponse
from app.core.database import get_db
from app.dependencies.auth import get_current_user
from app.services import admin_service, demo_service, video_service
from app.utils.authorization import is_admin, require_admin
from app.utils.error_handling import handle_not_found_error, log_and_raise_error

logger = logging.getLogger(__name__)

router = APIRouter(tags=["admin"])


class CleanupResponse(BaseModel):
    """Response model for cleanup operations."""

    orphaned_user_count: int
    videos_deleted: int
    players_deleted: int
    files_deleted: int
    errors: list[str]
    dry_run: bool
    message: str


class AdminStatusResponse(BaseModel):
    """Response model for admin status check."""

    is_admin: bool


class DemoVideoListItem(BaseModel):
    """Demo video list item with status information."""

    id: int
    filename: str
    file_path: str
    is_active_demo: bool
    has_pose_analysis: bool
    serve_attempt_count: int
    created_at: datetime

    model_config = {"from_attributes": True}


@router.get("/status", response_model=AdminStatusResponse)
async def check_admin_status(
    current_user: dict = Depends(get_current_user),
) -> AdminStatusResponse:
    """Check if current user is an admin.

    Returns:
        Admin status
    """
    return AdminStatusResponse(is_admin=is_admin(current_user))


@router.get("/demos", response_model=List[DemoVideoListItem])
async def list_demo_videos(
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> List[DemoVideoListItem]:
    """List all demo videos (admin only).

    Returns:
        List of demo videos with status information
    """
    require_admin(current_user)

    try:
        demo_list = demo_service.list_demo_videos_with_status(db)
        return [DemoVideoListItem(**item) for item in demo_list]
    except Exception as e:  # noqa: BLE001 - Catch all unexpected errors for API endpoint
        log_and_raise_error(e, "list_demo_videos")


@router.post("/demos/{video_id}/set-active", response_model=VideoInfo)
async def set_active_demo(
    video_id: int,
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> VideoInfo:
    """Set a demo video as the active demo (admin only).

    Args:
        video_id: ID of the demo video to set as active

    Returns:
        Updated video information
    """
    require_admin(current_user)

    try:
        video = demo_service.set_active_demo_video(db, video_id)
        return VideoInfo.model_validate(video)
    except ValueError as e:
        error_msg = str(e).lower()
        if "not found" in error_msg:
            raise handle_not_found_error("video", str(video_id)) from e
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
        log_and_raise_error(e, "set_active_demo", {"video_id": video_id})


@router.post("/demos/{video_id}/analyze-pose", response_model=AnalysisResponse)
async def analyze_demo_pose(
    video_id: int,
    confidence_threshold: float = Query(0.7, ge=0.0, le=1.0),
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> AnalysisResponse:
    """Trigger pose analysis for a demo video (admin only).

    Args:
        video_id: ID of the demo video to analyze
        confidence_threshold: Confidence threshold for pose detection

    Returns:
        Analysis response with task ID
    """
    require_admin(current_user)

    try:
        video_job = demo_service.enqueue_demo_pose_analysis(
            db=db,
            video_id=video_id,
            user_id=current_user["id"],
            confidence_threshold=confidence_threshold,
        )

        return AnalysisResponse(
            job_id=str(video_job.id),
            video_id=video_id,
            analysis_type="pose_only",
            status="queued",
            message="Pose analysis started successfully",
            estimated_duration=120.0,
        )
    except ValueError as e:
        error_msg = str(e).lower()
        if "not found" in error_msg:
            raise handle_not_found_error("video", str(video_id)) from e
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        ) from e
    except RuntimeError as e:
        error_msg = str(e).lower()
        if "redis" in error_msg:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="Failed to enqueue job to Redis. Please check Redis connection.",
            ) from e
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to start analysis. Please try again later.",
        ) from e
    except HTTPException:
        raise
    except Exception as e:  # noqa: BLE001 - Catch all unexpected errors for API endpoint
        log_and_raise_error(e, "analyze_demo_pose", {"video_id": video_id})


@router.post("/videos/upload-for-user", response_model=VideoUploadResponse)
async def upload_video_for_user(
    file: UploadFile = File(...),
    target_user_id: str = Query(
        ..., description="Supabase auth user ID to assign video to"
    ),
    is_demo: bool = Query(False, description="Upload as demo video"),
    session_type: Optional[str] = Query(
        None, description="Session type: 'serve_practice', 'match', 'other'"
    ),
    camera_angle: Optional[str] = Query(
        None, description="Camera angle: 'behind', 'profile', 'unknown'"
    ),
    recorded_at: Optional[datetime] = Query(
        None, description="When video was recorded (UTC; optional override)"
    ),
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> VideoUploadResponse:
    """Upload a video file on behalf of another user (admin only).

    Args:
        file: Video file to upload
        target_user_id: Supabase auth user ID to assign video ownership to
        is_demo: If True, upload as demo video
        session_type: Session type for serve-focused workflow
        camera_angle: Camera angle for serve biomechanics
        recorded_at: When video was recorded (for trends)

    Returns:
        Upload confirmation with video information
    """
    require_admin(current_user)

    try:
        # Validate target user exists in Supabase
        target_user = admin_service.validate_target_user_exists(target_user_id)

        logger.info(
            "Admin %s uploading video for user %s",
            current_user.get("email"),
            target_user.get("email"),
        )

        file.file.seek(0, 2)
        file_size = file.file.tell()
        file.file.seek(0)

        file_content = file.file.read()

        db_video, metadata = video_service.handle_video_upload(
            db=db,
            file_content=file_content,
            filename=file.filename,
            file_size=file_size,
            content_type=file.content_type,
            is_demo=is_demo,
            user_id=target_user_id,
            session_type=session_type,
            camera_angle=camera_angle,
            recorded_at=recorded_at,
        )

        logger.info(
            "Admin uploaded video %d for user %s",
            db_video.id,
            target_user_id,
        )

        return VideoUploadResponse(
            video_id=db_video.id,
            filename=db_video.filename,
            file_size=db_video.file_size,
            status="uploaded",
            message="Video uploaded successfully",
            metadata=VideoMetadata(**metadata) if metadata else None,
            quality_metrics=None,
        )
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        ) from e
    except HTTPException:
        raise
    except OSError as e:
        log_and_raise_error(
            e,
            "upload_video_for_user",
            {"filename": file.filename if file else "unknown"},
        )


@router.post("/cleanup/orphaned-data", response_model=CleanupResponse)
def cleanup_orphaned_user_data(
    dry_run: bool = Query(
        True, description="If True, only report what would be deleted"
    ),
    limit: Optional[int] = Query(
        None, description="Limit number of users to process (for safety)"
    ),
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> CleanupResponse:
    """Clean up orphaned data from deleted users (admin only).

    This endpoint finds and deletes videos and players belonging to users
    that no longer exist in Supabase auth.users table.

    Args:
        dry_run: If True, only report what would be deleted
        limit: Optional limit on number of users to process
        current_user: Current authenticated user (must be admin)
        db: Database session

    Returns:
        Cleanup statistics and results
    """
    require_admin(current_user)

    logger.info(
        "Admin cleanup requested by %s (dry_run=%s, limit=%s)",
        current_user.get("email"),
        dry_run,
        limit,
    )

    try:
        from app.services.cleanup_service import cleanup_orphaned_data

        stats = cleanup_orphaned_data(db, dry_run=dry_run, limit=limit)

        message = (
            f"{'Would delete' if dry_run else 'Deleted'} "
            f"{stats['videos_deleted']} videos, {stats['players_deleted']} players, "
            f"{stats['files_deleted']} files for {stats['orphaned_user_count']} orphaned users"
        )

        if stats["errors"]:
            message += f" ({len(stats['errors'])} errors occurred)"

        return CleanupResponse(
            orphaned_user_count=stats["orphaned_user_count"],
            videos_deleted=stats["videos_deleted"],
            players_deleted=stats["players_deleted"],
            files_deleted=stats["files_deleted"],
            errors=stats["errors"],
            dry_run=dry_run,
            message=message,
        )
    except HTTPException:
        raise
    except Exception as e:  # noqa: BLE001 - Catch all unexpected errors for admin endpoint
        log_and_raise_error(
            e, "cleanup_orphaned_user_data", {"dry_run": dry_run, "limit": limit}
        )


@router.get("/cleanup/orphaned-data/check", response_model=dict)
def check_orphaned_data(
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> dict:
    """Check for orphaned data without deleting (admin only).

    Args:
        current_user: Current authenticated user (must be admin)
        db: Database session

    Returns:
        Dictionary with orphaned user IDs and counts
    """
    require_admin(current_user)

    try:
        from app.services.cleanup_service import (
            find_orphaned_user_ids,
            get_orphaned_data_details,
        )

        orphaned_ids = find_orphaned_user_ids(db)
        details = get_orphaned_data_details(db, orphaned_ids)

        return {
            "orphaned_user_count": len(orphaned_ids),
            "orphaned_users": details,
        }
    except HTTPException:
        raise
    except Exception as e:  # noqa: BLE001 - Catch all unexpected errors for admin endpoint
        log_and_raise_error(e, "check_orphaned_data", {})
