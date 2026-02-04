"""Video API routes with proper REST patterns and error handling."""

import logging
from datetime import datetime
from typing import Dict, List, Optional
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
    FileResponse,
    RedirectResponse,
    Response,
    StreamingResponse,
)
from pydantic import BaseModel, Field, field_serializer
from sqlalchemy.orm import Session

from app.api.schemas.common import PaginationParams
from app.api.schemas.serve_attempt import ServeAnalysisSummary
from app.api.schemas.video import (
    VideoDeleteResponse,
    VideoInfo,
    VideoListItem,
    VideoMetadataUpdateRequest,
    VideoSignedUrlResponse,
    VideoUploadResponse,
)
from app.core.config import settings
from app.core.database import get_db
from app.core.redis_config import analysis_queue
from app.dependencies.auth import get_current_user, get_optional_user
from app.models.video_job import VideoJob
from app.services import video_service
from app.services.storage_service import storage_service
from app.utils.authorization import (
    is_admin,
    require_upload_limit,
    require_video_access,
    require_video_access_or_public_demo,
    require_video_deletable,
    require_video_not_demo,
)
from app.utils.error_handling import (
    handle_file_error,
    handle_not_found_error,
    log_and_raise_error,
)
from app.utils.file_validation import get_safe_filename, validate_file_exists


class VideoAnalysisStatus(BaseModel):
    """Response model for video analysis status check."""

    video_id: int
    has_analysis: bool
    analysis_types: List[str] = []


class BulkAnalysisStatusRequest(BaseModel):
    """Request model for bulk analysis status check."""

    video_ids: List[int] = Field(
        description="List of video IDs to check analysis status for",
        min_length=1,
        max_length=100,  # Limit to prevent abuse
    )


class BulkAnalysisStatusResponse(BaseModel):
    """Response model for bulk analysis status check."""

    statuses: List[VideoAnalysisStatus] = Field(
        description="Analysis status for each requested video"
    )


class BallContactTimestampsResponse(BaseModel):
    """Response model for ball contact timestamps in a video (serve contact points)."""

    ball_contact_timestamps: List[float] = Field(
        default_factory=list,
        description="Sorted list of ball contact timestamps in seconds (unique, ascending)",
    )


class VideoJobResponse(BaseModel):
    """Response schema for video job status."""

    id: UUID
    video_id: int
    job_type: str
    status: str
    error: Optional[str] = None
    stage: Optional[str] = (
        None  # "transcoding", "scout", "detecting_serves", "refining", "complete"
    )
    progress_percent: int = 0
    serve_windows_found: Optional[int] = (
        None  # Number of serve windows found (after scout pass)
    )
    created_at: datetime
    started_at: Optional[datetime] = None
    finished_at: Optional[datetime] = None

    model_config = {"from_attributes": True}

    @field_serializer("id")
    def serialize_id(self, id: UUID) -> str:
        """Convert UUID to string for JSON serialization."""
        return str(id)


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
        query = db.query(VideoJob).filter(VideoJob.user_id == current_user["id"])

        if job_status:
            status_list = [s.strip() for s in job_status.split(",")]
            query = query.filter(VideoJob.status.in_(status_list))

        jobs = query.order_by(VideoJob.created_at.desc()).limit(50).all()

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
        from uuid import UUID

        from app.utils.authorization import is_admin

        job_uuid = UUID(job_id)
        query = db.query(VideoJob).filter(VideoJob.id == job_uuid)
        if not is_admin(current_user):
            query = query.filter(VideoJob.user_id == current_user["id"])

        job = query.first()
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
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> List[VideoListItem]:
    """
    List all uploaded videos for the current user.

    Returns a paginated list of videos with basic information.
    """
    try:
        from app.models.video import Video
        from app.utils.authorization import is_admin

        # Filter by user_id unless admin
        # Exclude demo videos from user's library
        query = db.query(Video).filter(~Video.is_demo)
        if not is_admin(current_user):
            query = query.filter(Video.user_id == current_user["id"])

        # Order by creation date
        db_videos = query.order_by(Video.created_at.desc()).all()

        # Apply pagination
        start_idx = (pagination.page - 1) * pagination.size
        end_idx = start_idx + pagination.size
        paginated_videos = db_videos[start_idx:end_idx]

        return [VideoListItem.model_validate(video) for video in paginated_videos]
    except (OSError, ValueError) as e:
        log_and_raise_error(e, "list_videos")


@router.get("/demo", response_model=VideoInfo)
async def get_demo_video(
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
        from app.models.video import Video

        # Query for active demo video
        demo = db.query(Video).filter(Video.is_active_demo).first()

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

    Returns sorted, unique ball contact timestamps from serve attempts that have a contact point.
    """
    from app.models.serve_attempt import ServeAttempt

    db_video = video_service.get_video_by_id(db, video_id)
    if not db_video:
        raise handle_not_found_error("video", str(video_id))
    require_video_access(db_video, current_user)

    rows = (
        db.query(ServeAttempt.contact_timestamp)
        .filter(
            ServeAttempt.video_id == video_id,
            ServeAttempt.user_id == current_user["id"],
            ServeAttempt.contact_timestamp.isnot(None),
        )
        .all()
    )
    timestamps = sorted({r[0] for r in rows if r[0] is not None})
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

        # Use storage service to get file
        if settings.STORAGE_TYPE == "supabase":
            # For active demo videos, use public demo bucket URL
            if db_video.is_active_demo and settings.SUPABASE_DEMO_BUCKET:
                try:
                    # Demo videos should be stored with 'demo/' prefix in demo bucket
                    demo_path = db_video.file_path
                    if not demo_path.startswith("demo/"):
                        demo_path = f"demo/{db_video.id}_{db_video.filename}"
                    demo_url = storage_service.get_demo_public_url(demo_path)
                    logger.info(
                        f"Redirecting to demo bucket URL for active demo video {video_id}: {demo_url}"
                    )
                    return RedirectResponse(url=demo_url)
                except (ValueError, RuntimeError) as e:
                    logger.error(
                        f"Failed to get demo bucket URL for video {video_id}: {e}"
                    )
                    # Fallback to regular flow

            # For regular videos, use private bucket with signed URL or public URL
            # For Supabase, use file_path which contains 'raw/filename.mp4'
            # For local, file_path is the full path, but for Supabase it's the storage path
            storage_path = db_video.file_path
            try:
                file_url = storage_service.get_file_url(storage_path)
                logger.info(
                    f"Redirecting to Supabase URL for video {video_id}: {file_url}"
                )
                # Redirect to Supabase public URL
                return RedirectResponse(url=file_url)
            except (ValueError, RuntimeError, OSError) as e:
                logger.error(
                    f"Failed to get Supabase URL for video {video_id}, storage_path={storage_path}: {e}"
                )
                # Fallback: download and stream
                file_data = storage_service.download_file(storage_path)
                return StreamingResponse(
                    iter([file_data]),
                    media_type=db_video.content_type or "video/mp4",
                    headers={
                        "Content-Disposition": f'inline; filename="{get_safe_filename(db_video.filename)}"'
                    },
                )
        else:
            # For local storage, resolve the storage path to actual file system path
            resolved_path = storage_service.get_local_file_path(db_video.file_path)
            validate_file_exists(resolved_path, db_video.filename)

            return FileResponse(
                path=str(resolved_path),
                media_type=db_video.content_type or "video/mp4",
                filename=get_safe_filename(db_video.filename),
            )
    except (OSError, ValueError) as e:
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
                        f"Generated demo bucket public URL for active demo video {video_id}"
                    )
                    # Return with max expiration since it's a public URL
                    return VideoSignedUrlResponse(url=demo_url, expires_in=86400 * 365)
                except (ValueError, RuntimeError) as e:
                    logger.error(
                        f"Failed to get demo bucket URL for video {video_id}: {e}"
                    )
                    # Fallback to regular flow

            # For regular videos, use private bucket with signed URL
            storage_path = db_video.file_path
            try:
                signed_url = storage_service.create_signed_url(
                    storage_path, expires_in=expires_in
                )
                logger.info(
                    f"Generated signed URL for video {video_id}, expires in {expires_in}s"
                )
                return VideoSignedUrlResponse(url=signed_url, expires_in=expires_in)
            except (ValueError, RuntimeError) as e:
                logger.error(
                    f"Failed to create signed URL for video {video_id}, storage_path={storage_path}: {e}"
                )
                raise HTTPException(
                    status_code=500,
                    detail=f"Failed to generate video URL: {e!s}",
                ) from e
        else:
            # For local storage, construct full URL to the stream endpoint
            # Use the request's base URL to ensure it works with any deployment
            # Note: Router is mounted at /v0/videos, so include /v0 prefix
            base_url = str(request.base_url).rstrip("/")
            stream_url = f"{base_url}/v0/videos/{video_id}/stream"
            logger.debug(
                f"Returning stream URL for local video {video_id}: {stream_url}"
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
        # Verify video exists
        db_video = video_service.get_video_by_id(db, video_id)
        if not db_video:
            raise handle_not_found_error("video", str(video_id))

        # Check authorization
        require_video_access(db_video, current_user)

        analysis_types = []
        has_analysis = False

        # Check for pose detection
        from app.models.pose_detection import PoseDetection

        pose_detection = (
            db.query(PoseDetection).filter(PoseDetection.video_id == video_id).first()
        )
        if pose_detection and pose_detection.status == "completed":
            has_analysis = True
            analysis_types.append("pose_detection")

        return VideoAnalysisStatus(
            video_id=video_id,
            has_analysis=has_analysis,
            analysis_types=analysis_types,
        )

    except (OSError, ValueError) as e:
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
        from app.models.pose_detection import PoseDetection
        from app.models.video import Video
        from app.utils.authorization import is_admin

        video_ids = request.video_ids

        # Verify all videos exist and user has access
        query = db.query(Video).filter(Video.id.in_(video_ids))
        if not is_admin(current_user):
            query = query.filter(Video.user_id == current_user["id"])

        accessible_videos = {video.id for video in query.all()}

        # Check for unauthorized access
        unauthorized_ids = set(video_ids) - accessible_videos
        if unauthorized_ids:
            raise HTTPException(
                status_code=404,
                detail=f"Videos not found or access denied: {list(unauthorized_ids)}",
            )

        # Fetch all pose detections in one query
        pose_detections = (
            db.query(PoseDetection)
            .filter(
                PoseDetection.video_id.in_(video_ids),
                PoseDetection.status == "completed",
            )
            .all()
        )

        # Build lookup maps for O(1) access
        pose_map: Dict[int, PoseDetection] = {pd.video_id: pd for pd in pose_detections}

        # Build response for each video
        statuses = []
        for video_id in video_ids:
            analysis_types = []
            has_analysis = False

            if video_id in pose_map:
                has_analysis = True
                analysis_types.append("pose_detection")

            statuses.append(
                VideoAnalysisStatus(
                    video_id=video_id,
                    has_analysis=has_analysis,
                    analysis_types=analysis_types,
                )
            )

        return BulkAnalysisStatusResponse(statuses=statuses)

    except HTTPException:
        raise
    except (OSError, ValueError) as e:
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
    Update video metadata (session_type and camera_angle).

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

        # Update metadata
        updated_video = video_service.update_video_metadata(
            db=db,
            video_id=video_id,
            session_type=metadata_update.session_type,
            camera_angle=metadata_update.camera_angle,
        )

        if not updated_video:
            raise handle_not_found_error("video", str(video_id))

        return VideoInfo.model_validate(updated_video)
    except (OSError, ValueError) as e:
        log_and_raise_error(e, "update_video_metadata", {"video_id": video_id})


@router.post("/upload", response_model=VideoUploadResponse)
async def upload_video(
    file: UploadFile = File(...),
    is_demo: bool = Query(False, description="Upload as demo video"),
    session_type: Optional[str] = Query(
        None, description="Session type: 'serve_practice', 'match', 'other'"
    ),
    camera_angle: Optional[str] = Query(
        None, description="Camera angle: 'behind', 'profile', 'diagonal', 'unknown'"
    ),
    recorded_at: Optional[datetime] = Query(
        None, description="When video was recorded (UTC; optional override)"
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
        camera_angle: Camera angle for serve analysis
        recorded_at: When video was recorded (for trends)

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
        )

        # Auto-enqueue transcoding and pose detection (opt-in via setting)
        # Disabled by default to prevent unintended background jobs during tests
        # or in environments where Redis should not be used.
        # When enabled, ALL uploads (regular and demo) are auto-enqueued.
        # Pytest tests are unaffected because they mock enqueue functions.
        if settings.AUTO_ENQUEUE_ON_UPLOAD:
            from rq import Retry

            from app.services.rq_tasks import transcode_video_rq

            # Create pose detection job record (will be started after transcode if needed)
            pose_job = VideoJob(
                video_id=db_video.id,
                user_id=current_user["id"],
                job_type="pose_only",
                status="queued",
            )
            db.add(pose_job)
            db.commit()
            db.refresh(pose_job)

            # Enqueue transcoding first if file is large enough, otherwise go straight to pose detection
            try:
                if (
                    settings.TRANSCODE_ENABLED
                    and db_video.file_size >= settings.TRANSCODE_THRESHOLD_BYTES
                ):
                    # Create transcode job record
                    transcode_job = VideoJob(
                        video_id=db_video.id,
                        user_id=current_user["id"],
                        job_type="transcode",
                        status="queued",
                    )
                    db.add(transcode_job)
                    db.commit()
                    db.refresh(transcode_job)

                    # Enqueue transcode job (will chain to pose detection on completion)
                    rq_job = analysis_queue.enqueue(
                        transcode_video_rq,
                        video_id=db_video.id,
                        video_path=db_video.file_path,
                        video_job_id=str(transcode_job.id),
                        retry=Retry(max=2, interval=60),
                        job_timeout=600,  # 10 minutes for transcoding
                        result_ttl=3600,
                    )
                    if rq_job:
                        transcode_job.rq_job_id = rq_job.id
                        db.commit()
                        logger.info(
                            "Auto-enqueued transcoding for video %d (is_demo=%s)",
                            db_video.id,
                            is_demo,
                        )
                    else:
                        transcode_job.status = "failed"
                        transcode_job.error = "Failed to enqueue transcode job to Redis"
                        db.commit()
                else:
                    # File is small enough, skip transcoding and go straight to scout/refine pipeline
                    from app.services.rq_tasks import (
                        analyze_pose_detection_scout_refine_rq,
                    )

                    rq_job = analysis_queue.enqueue(
                        analyze_pose_detection_scout_refine_rq,
                        video_id=db_video.id,
                        video_path=db_video.file_path,
                        video_job_id=str(pose_job.id),
                        confidence_threshold=0.7,
                        retry=Retry(max=2, interval=60),
                        job_timeout=settings.POSE_DETECTION_JOB_TIMEOUT_SECONDS,
                        result_ttl=3600,
                    )
                    job = rq_job
                    if not job:
                        pose_job.status = "failed"
                        pose_job.error = "Failed to enqueue job to Redis"
                        db.commit()
                        logger.debug(
                            "Auto-enqueue failed for video %d (is_demo=%s)",
                            db_video.id,
                            is_demo,
                        )
                    else:
                        pose_job.rq_job_id = job.id
                        db.commit()
                        logger.info(
                            "Auto-enqueued pose analysis for video %d (is_demo=%s, skipped transcode)",
                            db_video.id,
                            is_demo,
                        )
            except Exception:  # noqa: BLE001 - Intentionally catch all to ensure upload succeeds
                # Enqueue functions already log errors internally, just ensure upload doesn't fail
                if "transcode_job" in locals():
                    transcode_job.status = "failed"
                    transcode_job.error = "Failed to enqueue job to Redis"
                pose_job.status = "failed"
                pose_job.error = "Failed to enqueue job to Redis"
                db.commit()
                logger.debug("Failed to enqueue jobs, but upload succeeded")
        else:
            logger.debug(
                "Auto-enqueue disabled (AUTO_ENQUEUE_ON_UPLOAD=False). "
                "Set AUTO_ENQUEUE_ON_UPLOAD=True in .env to enable."
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


@router.post("/{video_id}/analyze-serves", response_model=ServeAnalysisSummary)
async def analyze_serve_attempts(
    video_id: int,
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> ServeAnalysisSummary:
    """
    Batch analyze all serve attempts for a video.
    Calculates elbow angles synchronously (no RQ).
    """
    try:
        from app.models.serve_attempt import ServeAttempt
        from app.services.serve_analysis_service import ServeAnalysisService

        # Get video to check authorization
        video = video_service.get_video_by_id(db, video_id)
        if not video:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Video with ID {video_id} not found",
            )

        # Check authorization
        require_video_access(video, current_user)

        # Prevent modification of demo videos
        require_video_not_demo(video, current_user)

        # Check if there are serve attempts to analyze
        serve_attempts = (
            db.query(ServeAttempt).filter(ServeAttempt.video_id == video_id).all()
        )

        if not serve_attempts:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="No serve attempts found for this video. Please tag serve attempts first.",
            )

        # Count serves with contact
        serves_with_contact = sum(
            1 for sa in serve_attempts if sa.contact_timestamp is not None
        )

        # Run analysis inline (fast: uses already-computed pose detections)
        analysis_service = ServeAnalysisService()
        results = analysis_service.analyze_serve_attempts(
            db=db, video_id=video_id, serve_attempts=serve_attempts
        )

        avg_elbow_angle = results.get("avg_elbow_angle")
        if avg_elbow_angle is not None and not (0.0 <= avg_elbow_angle <= 180.0):
            logger.warning(
                "Serve analysis returned invalid avg_elbow_angle=%s for video_id=%s",
                avg_elbow_angle,
                video_id,
            )
            avg_elbow_angle = None

        return ServeAnalysisSummary(
            video_id=video_id,
            total_serves=len(serve_attempts),
            serves_with_contact=serves_with_contact,
            avg_elbow_angle=avg_elbow_angle,
        )

    except HTTPException:
        raise
    except ValueError as e:
        # Common expected error cases (e.g., missing pose detection)
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        ) from e
    except Exception as e:
        logger.exception("Error starting serve analysis")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to start serve analysis. Please try again later.",
        ) from e
