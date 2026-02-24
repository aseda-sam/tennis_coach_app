"""Video API routes with proper REST patterns and error handling."""

import logging
from datetime import datetime
from typing import List, Literal, Optional
from uuid import UUID

from fastapi import (
    APIRouter,
    Body,
    Depends,
    File,
    HTTPException,
    Query,
    Request,
    UploadFile,
    status,
)
from fastapi.responses import (
    Response,
)
from sqlalchemy.orm import Session

from app.api.schemas.common import PaginationParams
from app.api.schemas.video import (
    BallContactTimestampsResponse,
    BulkAnalysisStatusRequest,
    BulkAnalysisStatusResponse,
    VideoAnalysisStatus,
    VideoDeleteResponse,
    VideoInfo,
    VideoJobResponse,
    VideoListItem,
    VideoMetadataUpdateRequest,
    VideoSignedUrlResponse,
    VideoUploadResponse,
)
from app.core.config import settings
from app.core.database import get_db
from app.dependencies.auth import get_current_user, get_optional_user
from app.services import (
    player_service,
    serve_window_service,
    video_auto_enqueue_service,
    video_job_service,
    video_service,
    video_streaming_service,
)
from app.services.storage_service import storage_service
from app.utils.authorization import (
    is_admin,
    require_upload_limit,
    require_video_access,
    require_video_access_or_public_demo,
    require_video_deletable,
)
from app.utils.error_handling import (
    handle_file_error,
    handle_not_found_error,
    log_and_raise_error,
)
from app.utils.rate_limit import limiter

router = APIRouter()
logger = logging.getLogger(__name__)


@router.get("/jobs", response_model=List[VideoJobResponse])
async def get_video_jobs(
    current_user: dict = Depends(get_current_user),
    job_status: Optional[str] = Query(
        default=None,
        description="Filter by status (comma-separated, e.g., 'queued,processing')",
        alias="status",
    ),
    db: Session = Depends(get_db),
) -> List[VideoJobResponse]:
    """
    Get jobs for user's videos. UI polls this every 30s.

    Args:
        status: Optional filter - comma-separated list (e.g., "queued,processing")

    Returns:
        List of video jobs for the authenticated user
    """
    try:
        status_list = None
        if job_status:
            status_list = [s.strip() for s in job_status.split(",")]

        jobs = video_job_service.get_user_jobs(
            db=db,
            user_id=current_user["id"],
            status_filter=status_list,
            limit=50,
        )

        return [VideoJobResponse.model_validate(job) for job in jobs]

    except (ValueError, RuntimeError) as e:
        log_and_raise_error(e, "get_video_jobs", {"user_id": current_user["id"]})


@router.get("/jobs/{job_id}", response_model=VideoJobResponse)
async def get_video_job(
    job_id: str,
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> VideoJobResponse:
    """
    Get a single video job by ID (DB-backed).

    Args:
        job_id: VideoJob UUID

    Returns:
        Video job for the authenticated user
    """
    try:
        job_uuid = UUID(job_id)
        job = video_job_service.get_job_by_id(
            db=db,
            job_id=job_uuid,
            user_id=current_user["id"],
            is_admin=is_admin(current_user),
        )
        if not job:
            raise handle_not_found_error("job", job_id)

        return VideoJobResponse.model_validate(job)
    except (ValueError, TypeError):
        raise handle_not_found_error("job", job_id) from None
    except HTTPException:
        raise
    except (OSError, RuntimeError) as e:
        log_and_raise_error(e, "get_video_job", {"job_id": job_id})


@router.get("/", response_model=List[VideoListItem])
async def list_videos(
    pagination: PaginationParams = Depends(),
    camera_angle: Optional[Literal["behind", "profile"]] = Query(
        default=None, description="Filter by camera angle"
    ),
    player_id: Optional[int] = Query(default=None, description="Filter by player ID"),
    exclude_player_id: Optional[int] = Query(
        default=None, description="Exclude videos with this player ID"
    ),
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> List[VideoListItem]:
    """
    List all uploaded videos for the current user.

    Returns a paginated list of videos with basic information.
    Supports optional filters: camera_angle, player_id, exclude_player_id.
    """
    try:
        videos = video_service.list_user_videos(
            db=db,
            user_id=current_user["id"],
            is_admin=is_admin(current_user),
            skip=(pagination.page - 1) * pagination.size,
            limit=pagination.size,
            camera_angle=camera_angle,
            player_id=player_id,
            exclude_player_id=exclude_player_id,
        )

        return [VideoListItem.model_validate(video) for video in videos]
    except (OSError, ValueError) as e:
        log_and_raise_error(e, "list_videos")


@router.get("/demo", response_model=VideoInfo)
@limiter.limit("10/minute")
async def get_demo_video(
    request: Request,
    db: Session = Depends(get_db),
) -> VideoInfo:
    """
    Get the active demo video for showcase purposes.

    Returns the single video with is_active_demo=True.
    Only one demo video should be active at a time.

    IMPORTANT: This route must come BEFORE /{video_id} to avoid route conflicts.

    Returns:
        Demo video information

    Raises:
        HTTPException: 404 if no active demo video exists
    """
    try:
        demo = video_service.get_active_demo_video(db)

        if not demo:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="No active demo video available. Please contact support.",
            )

        return VideoInfo.model_validate(demo)
    except HTTPException:
        raise
    except (OSError, ValueError) as e:
        log_and_raise_error(e, "get_demo_video")


@router.get(
    "/{video_id}/ball-contact-timestamps",
    response_model=BallContactTimestampsResponse,
)
async def get_video_ball_contact_timestamps(
    video_id: int,
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> BallContactTimestampsResponse:
    """
    Get all ball contact timestamps for serves in a video (for prev/next contact navigation).

    Returns sorted, unique ball contact timestamps from serve windows that have a contact point.
    """
    db_video = video_service.get_video_by_id(db, video_id)
    if not db_video:
        raise handle_not_found_error("video", str(video_id))
    require_video_access(db_video, current_user)

    timestamps = serve_window_service.get_ball_contact_timestamps(
        db=db,
        video_id=video_id,
        user_id=current_user["id"],
    )
    return BallContactTimestampsResponse(ball_contact_timestamps=timestamps)


@router.get("/{video_id}", response_model=VideoInfo)
async def get_video(
    video_id: int,
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> VideoInfo:
    """
    Get detailed information about a specific video.

    Args:
        video_id: Unique video identifier

    Returns:
        Complete video information including metadata
    """
    try:
        db_video = video_service.get_video_by_id(db, video_id)
        if not db_video:
            raise handle_not_found_error("video", str(video_id))

        # Check authorization
        require_video_access(db_video, current_user)

        return VideoInfo.model_validate(db_video)
    except (OSError, ValueError) as e:
        log_and_raise_error(e, "get_video", {"video_id": video_id})


@router.get("/{video_id}/stream", response_model=None)
async def stream_video(
    video_id: int,
    current_user: Optional[dict] = Depends(get_optional_user),
    db: Session = Depends(get_db),
) -> Response:
    """
    Stream a video file.

    Args:
        video_id: Unique video identifier

    Returns:
        Video file stream or redirect to storage URL
    """
    try:
        # Get video from database
        db_video = video_service.get_video_by_id(db, video_id)
        if not db_video:
            raise handle_not_found_error("video", str(video_id))

        # Check authorization (allow public access for demo videos)
        require_video_access_or_public_demo(db_video, current_user)

        return video_streaming_service.get_video_stream_response(
            db=db,
            video_id=video_id,
            current_user=current_user,
        )
    except ValueError as e:
        error_msg = str(e).lower()
        if "not found" in error_msg:
            raise handle_not_found_error("video", str(video_id)) from e
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid video request",
        ) from e
    except RuntimeError as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Video streaming failed",
        ) from e
    except HTTPException:
        raise
    except OSError as e:
        log_and_raise_error(e, "stream_video", {"video_id": video_id})


@router.get("/{video_id}/url", response_model=VideoSignedUrlResponse)
async def get_video_url(
    video_id: int,
    request: Request,
    current_user: Optional[dict] = Depends(get_optional_user),
    db: Session = Depends(get_db),
    expires_in: int = 3600,
) -> VideoSignedUrlResponse:
    """
    Get a signed URL for video access (for cloud storage) or file path (for local).

    This endpoint returns a direct URL that can be used by the frontend without
    requiring redirect resolution, eliminating race conditions and error flashes.

    Args:
        video_id: Unique video identifier
        expires_in: Number of seconds the signed URL should remain valid (default: 3600)

    Returns:
        VideoSignedUrlResponse with signed URL and expiration time
    """
    try:
        # Get video from database
        db_video = video_service.get_video_by_id(db, video_id)
        if not db_video:
            raise handle_not_found_error("video", str(video_id))

        # Check authorization (allow public access for demo videos)
        require_video_access_or_public_demo(db_video, current_user)

        # Validate expires_in (reasonable range: 60 seconds to 24 hours)
        if expires_in < 60 or expires_in > 86400:
            raise ValueError("expires_in must be between 60 and 86400 seconds")

        # Use storage service to get signed URL or file path
        if settings.STORAGE_TYPE == "supabase":
            # For active demo videos, use public demo bucket URL (no expiration)
            if db_video.is_active_demo and settings.SUPABASE_DEMO_BUCKET:
                try:
                    # Demo videos should be stored with 'demo/' prefix in demo bucket
                    demo_path = db_video.file_path
                    if not demo_path.startswith("demo/"):
                        demo_path = f"demo/{db_video.id}_{db_video.filename}"
                    demo_url = storage_service.get_demo_public_url(demo_path)
                    logger.info(
                        "Generated demo bucket public URL for active demo video %s",
                        video_id,
                    )
                    # Return with max expiration since it's a public URL
                    return VideoSignedUrlResponse(url=demo_url, expires_in=86400 * 365)
                except (ValueError, RuntimeError) as e:
                    logger.error(
                        "Failed to get demo bucket URL for video %s: %s",
                        video_id,
                        e,
                    )
                    # Fallback to regular flow

            # For regular videos, use private bucket with signed URL
            storage_path = db_video.file_path
            try:
                signed_url = storage_service.create_signed_url(
                    storage_path, expires_in=expires_in
                )
                logger.info(
                    "Generated signed URL for video %s, expires in %ss",
                    video_id,
                    expires_in,
                )
                return VideoSignedUrlResponse(url=signed_url, expires_in=expires_in)
            except (ValueError, RuntimeError) as e:
                logger.error(
                    "Failed to create signed URL for video %s, storage_path=%s: %s",
                    video_id,
                    storage_path,
                    e,
                )
                raise HTTPException(
                    status_code=500,
                    detail="Failed to generate video URL",
                ) from e
        else:
            # For local storage, construct full URL to the stream endpoint
            # Use the request's base URL to ensure it works with any deployment
            # Note: Router is mounted at /v0/videos, so include /v0 prefix
            base_url = str(request.base_url).rstrip("/")
            stream_url = f"{base_url}/v0/videos/{video_id}/stream"
            logger.debug(
                "Returning stream URL for local video %s: %s",
                video_id,
                stream_url,
            )
            return VideoSignedUrlResponse(url=stream_url, expires_in=expires_in)

    except (OSError, ValueError) as e:
        log_and_raise_error(e, "get_video_url", {"video_id": video_id})


@router.get("/{video_id}/analysis-status", response_model=VideoAnalysisStatus)
async def get_video_analysis_status(
    video_id: int,
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> VideoAnalysisStatus:
    """
    Check if a video has any analysis or annotated video available.

    Args:
        video_id: Unique video identifier

    Returns:
        Analysis status information for the video
    """
    try:
        # Verify video exists and check authorization
        db_video = video_service.get_video_by_id(db, video_id)
        if not db_video:
            raise handle_not_found_error("video", str(video_id))

        require_video_access(db_video, current_user)

        status_dict = video_service.get_video_analysis_status(db, video_id)
        return VideoAnalysisStatus(**status_dict)

    except ValueError as e:
        error_msg = str(e).lower()
        if "not found" in error_msg:
            raise handle_not_found_error("video", str(video_id)) from e
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid analysis request",
        ) from e
    except HTTPException:
        raise
    except OSError as e:
        log_and_raise_error(e, "get_video_analysis_status", {"video_id": video_id})


@router.post("/analysis-status/bulk", response_model=BulkAnalysisStatusResponse)
async def get_bulk_analysis_status(
    request: BulkAnalysisStatusRequest = Body(...),
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> BulkAnalysisStatusResponse:
    """
    Get analysis status for multiple videos in a single request.

    This endpoint optimizes the N+1 query problem by fetching all analysis
    statuses in bulk using efficient database queries.

    Args:
        request: Bulk request containing list of video IDs

    Returns:
        Analysis status for each requested video
    """
    try:
        status_dicts = video_service.get_bulk_analysis_status(
            db=db,
            video_ids=request.video_ids,
            user_id=current_user["id"],
            is_admin=is_admin(current_user),
        )

        statuses = [VideoAnalysisStatus(**status_dict) for status_dict in status_dicts]
        return BulkAnalysisStatusResponse(statuses=statuses)

    except ValueError as e:
        raise HTTPException(
            status_code=404,
            detail="Invalid bulk analysis request",
        ) from e
    except HTTPException:
        raise
    except OSError as e:
        log_and_raise_error(
            e, "get_bulk_analysis_status", {"video_ids": request.video_ids}
        )


@router.delete("/{video_id}", response_model=VideoDeleteResponse)
async def delete_video(
    video_id: int,
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> VideoDeleteResponse:
    """
    Delete a video file and database record.

    Args:
        video_id: Unique video identifier

    Returns:
        Deletion confirmation
    """
    try:
        # Get video first to check authorization
        db_video = video_service.get_video_by_id(db, video_id)
        if not db_video:
            raise handle_not_found_error("video", str(video_id))

        # Check authorization (only owner can delete)
        require_video_access(db_video, current_user)

        # Prevent deletion of demo videos
        require_video_deletable(db_video)

        # Use service function to handle all deletion logic
        success, filename, deleted_video_id = video_service.delete_video_with_analyses(
            db, video_id
        )

        if not success:
            raise handle_file_error("delete_failed", filename, "Video deletion failed")

        return VideoDeleteResponse(
            message=f"Video {filename} deleted successfully",
            video_id=deleted_video_id,
            filename=filename,
        )
    except (OSError, ValueError) as e:
        log_and_raise_error(e, "delete_video", {"video_id": video_id})


@router.patch("/{video_id}/metadata", response_model=VideoInfo)
async def update_video_metadata(
    video_id: int,
    metadata_update: VideoMetadataUpdateRequest,
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> VideoInfo:
    """
    Update video metadata (session_type, camera_angle, default player).

    Args:
        video_id: Unique video identifier
        metadata_update: Metadata fields to update
        current_user: Authenticated user

    Returns:
        Updated video information
    """
    try:
        # Get video to check authorization
        db_video = video_service.get_video_by_id(db, video_id)
        if not db_video:
            raise handle_not_found_error("video", str(video_id))

        # Check authorization (only owner can update)
        require_video_access(db_video, current_user)

        primary_player_id = None
        if metadata_update.player_tag == "you":
            default_player = player_service.get_or_create_default_player(
                db, current_user["id"]
            )
            primary_player_id = default_player.id
        elif metadata_update.player_tag == "someone_else":
            other_player = player_service.get_or_create_other_player(
                db, current_user["id"]
            )
            primary_player_id = other_player.id

        # Update metadata
        updated_video = video_service.update_video_metadata(
            db=db,
            video_id=video_id,
            session_type=metadata_update.session_type,
            camera_angle=metadata_update.camera_angle,
            primary_player_id=primary_player_id,
        )

        if not updated_video:
            raise handle_not_found_error("video", str(video_id))

        if metadata_update.apply_to_existing_serves:
            target_player_id = updated_video.primary_player_id
            if not target_player_id:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Default player must be set before reassigning serves.",
                )
            serve_window_service.reassign_video_serve_windows(
                db=db,
                video_id=video_id,
                user_id=current_user["id"],
                player_id=target_player_id,
            )

        return VideoInfo.model_validate(updated_video)
    except (OSError, ValueError) as e:
        log_and_raise_error(e, "update_video_metadata", {"video_id": video_id})


@router.post("/upload", response_model=VideoUploadResponse)
@limiter.limit("10/minute")
async def upload_video(
    request: Request,
    file: UploadFile = File(...),
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
    client_recorded_at: Optional[datetime] = Query(
        None, description="Client-provided recording timestamp (from File.lastModified)"
    ),
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> VideoUploadResponse:
    """
    Upload a video file.

    Args:
        file: Video file to upload
        is_demo: If True, upload as demo video (requires authorization)
        session_type: Session type for serve-focused workflow
        camera_angle: Camera angle for serve biomechanics
        recorded_at: When video was recorded (for trends)
        client_recorded_at: Client-provided recording timestamp

    Returns:
        Upload confirmation with video information
    """
    try:
        # Check demo upload authorization
        if is_demo and settings.PROFILE != "local" and not is_admin(current_user):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Admin access required to upload demo videos",
            )

        # Check daily upload limit (skip for admins and local profile)
        if settings.PROFILE != "local" and not is_admin(current_user):
            require_upload_limit(db, current_user, settings.MAX_VIDEO_UPLOADS_PER_DAY)

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
            user_id=current_user["id"],
            session_type=session_type,
            camera_angle=camera_angle,
            recorded_at=recorded_at,
            client_recorded_at=client_recorded_at,
        )

        # Auto-enqueue transcoding and pose detection (opt-in via setting)
        # Disabled by default to prevent unintended background jobs during tests
        # or in environments where Redis should not be used.
        # When enabled, ALL uploads (regular and demo) are auto-enqueued.
        # Pytest tests are unaffected because they mock enqueue functions.
        video_auto_enqueue_service.auto_enqueue_video_analysis(
            db=db,
            video=db_video,
            user_id=current_user["id"],
        )

        return VideoUploadResponse(
            video_id=db_video.id,
            filename=db_video.filename,
            file_size=db_video.file_size,
            status="uploaded",
            message="Video uploaded successfully",
            metadata=metadata,
            quality_metrics=None,  # Video quality assessment removed for MVP
        )
    except (OSError, ValueError) as e:
        log_and_raise_error(
            e, "upload_video", {"filename": file.filename if file else "unknown"}
        )
