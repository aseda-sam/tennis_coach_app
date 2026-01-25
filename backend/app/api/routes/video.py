"""Video API routes with proper REST patterns and error handling."""

import logging
import tempfile
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional

import cv2
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
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.api.schemas.common import PaginationParams
from app.api.schemas.serve_attempt import ServeAnalysisSummary
from app.api.schemas.video import (
    VideoDeleteResponse,
    VideoInfo,
    VideoListItem,
    VideoMetadata,
    VideoMetrics,
    VideoSignedUrlResponse,
    VideoUploadResponse,
)
from app.core.config import settings
from app.core.database import get_db
from app.dependencies.auth import get_current_user
from app.services import video_service
from app.services.storage_service import storage_service
from app.utils.authorization import (
    is_admin,
    is_demo_editor,
    require_upload_limit,
    require_video_access,
    require_video_deletable,
    require_video_not_demo,
)
from app.utils.error_handling import (
    handle_file_error,
    handle_not_found_error,
    log_and_raise_error,
)
from app.utils.file_validation import (
    ensure_unique_filename,
    get_safe_filename,
    validate_file_exists,
    validate_video_file,
)


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


router = APIRouter()
logger = logging.getLogger(__name__)


def _create_temp_file_for_processing(file_content: bytes, filename: str) -> Path:
    """
    Create a temporary file for video processing (metadata extraction, quality assessment).

    Args:
        file_content: File content as bytes
        filename: Original filename (for extension)

    Returns:
        Path to temporary file (caller must clean up)
    """
    with tempfile.NamedTemporaryFile(
        delete=False, suffix=Path(filename).suffix
    ) as tmp_file:
        tmp_file.write(file_content)
        tmp_path = Path(tmp_file.name)
    return tmp_path


def extract_video_metadata(video_path: Path) -> VideoMetadata:
    """Extract metadata from video file using OpenCV."""
    try:
        cap = cv2.VideoCapture(str(video_path))
        if not cap.isOpened():
            return VideoMetadata()

        # Get video properties
        fps = cap.get(cv2.CAP_PROP_FPS)
        frame_count = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
        width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
        height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))

        # Calculate duration
        duration = frame_count / fps if fps > 0 else None

        cap.release()

        return VideoMetadata(
            fps=fps,
            frame_count=frame_count,
            width=width,
            height=height,
            duration=duration,
        )
    except (cv2.error, OSError, ValueError):
        # Return empty metadata if extraction fails
        return VideoMetadata()


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
    current_user: dict = Depends(get_current_user),
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
    current_user: dict = Depends(get_current_user),
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

        # Check authorization
        require_video_access(db_video, current_user)

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
            # For local storage, use FileResponse
            file_path = Path(db_video.file_path)
            validate_file_exists(file_path, db_video.filename)

            return FileResponse(
                path=str(file_path),
                media_type=db_video.content_type or "video/mp4",
                filename=get_safe_filename(db_video.filename),
            )
    except (OSError, ValueError) as e:
        log_and_raise_error(e, "stream_video", {"video_id": video_id})


@router.get("/{video_id}/url", response_model=VideoSignedUrlResponse)
async def get_video_url(
    video_id: int,
    request: Request,
    current_user: dict = Depends(get_current_user),
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

        # Check authorization
        require_video_access(db_video, current_user)

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

        # Check for ball detection
        from app.models.ball_detection import BallDetection

        ball_detection = (
            db.query(BallDetection).filter(BallDetection.video_id == video_id).first()
        )
        if ball_detection and ball_detection.status == "completed":
            has_analysis = True
            if "ball_detection" not in analysis_types:
                analysis_types.append("ball_detection")

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
        from app.models.ball_detection import BallDetection
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

        # Fetch all ball detections in one query
        ball_detections = (
            db.query(BallDetection)
            .filter(
                BallDetection.video_id.in_(video_ids),
                BallDetection.status == "completed",
            )
            .all()
        )

        # Build lookup maps for O(1) access
        pose_map: Dict[int, PoseDetection] = {pd.video_id: pd for pd in pose_detections}
        ball_map: Dict[int, BallDetection] = {bd.video_id: bd for bd in ball_detections}

        # Build response for each video
        statuses = []
        for video_id in video_ids:
            analysis_types = []
            has_analysis = False

            if video_id in pose_map:
                has_analysis = True
                analysis_types.append("pose_detection")

            if video_id in ball_map:
                has_analysis = True
                if "ball_detection" not in analysis_types:
                    analysis_types.append("ball_detection")

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


@router.get("/{video_id}/metrics", response_model=VideoMetrics)
async def get_video_metrics(
    video_id: int,
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> VideoMetrics:
    """
    Get aggregated performance metrics for a video.

    Calculates metrics from ball contacts including serve count,
    average elbow angle, and other performance indicators.

    Args:
        video_id: Unique video identifier

    Returns:
        VideoMetrics with aggregated performance data
    """
    try:
        from app.services.ball_contact_service import get_ball_contacts_by_video_id

        # Verify video exists and check authorization
        db_video = video_service.get_video_by_id(db, video_id)
        if not db_video:
            raise handle_not_found_error("video", str(video_id))

        require_video_access(db_video, current_user)

        # Get all ball contacts for the video
        contacts = get_ball_contacts_by_video_id(db, video_id)

        # Filter serves
        serves = [c for c in contacts if c.stroke_type == "serve"]
        serve_count = len(serves)

        # Calculate average elbow angle from serves
        elbow_angles = [s.elbow_angle for s in serves if s.elbow_angle is not None]
        avg_elbow = (
            round(sum(elbow_angles) / len(elbow_angles)) if elbow_angles else None
        )

        return VideoMetrics(
            video_id=video_id,
            serve_count=serve_count,
            avg_elbow_angle=avg_elbow,
            total_contacts=len(contacts),
            toss_height=None,  # Placeholder for future implementation
            contact_height=None,  # Placeholder for future implementation
        )

    except (OSError, ValueError) as e:
        log_and_raise_error(e, "get_video_metrics", {"video_id": video_id})


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


@router.post("/upload", response_model=VideoUploadResponse)
async def upload_video(
    file: UploadFile = File(...),
    is_demo: bool = Query(False, description="Upload as demo video"),
    session_type: Optional[str] = Query(
        None, description="Session type: 'serve_drill', 'match', 'practice', 'other'"
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
        if is_demo and settings.PROFILE != "local" and not is_demo_editor(current_user):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Only authorized users can upload demo videos",
            )

        # Check daily upload limit (skip for admins and local profile)
        if settings.PROFILE != "local" and not is_admin(current_user):
            require_upload_limit(db, current_user, settings.MAX_VIDEO_UPLOADS_PER_DAY)

        # Validate file
        if not file.filename:
            raise handle_file_error("invalid", "", "No file provided")

        # Get file size
        file.file.seek(0, 2)  # Seek to end
        file_size = file.file.tell()
        file.file.seek(0)  # Reset to beginning

        # Validate video file
        validate_video_file(file.filename, file_size, file.content_type)

        # Ensure safe and unique filename
        safe_filename = get_safe_filename(file.filename)

        # Determine storage path prefix (demo/ or raw/)
        path_prefix = "demo/" if is_demo else "raw/"

        # For local storage, check uniqueness in local directory before upload
        # For Supabase, storage service will handle uniqueness automatically (appends counter)
        if settings.STORAGE_TYPE == "local":
            # For local storage, UPLOAD_DIR is the base (e.g., ../data/videos/raw)
            # For demo videos, we need to create a demo subdirectory
            base_upload_dir = Path(settings.UPLOAD_DIR).parent  # ../data/videos
            upload_dir = base_upload_dir / path_prefix.rstrip(
                "/"
            )  # ../data/videos/demo or ../data/videos/raw
            upload_dir.mkdir(parents=True, exist_ok=True)
            unique_filename = ensure_unique_filename(safe_filename, upload_dir)
            # For local storage, store the full path relative to base directory
            # This avoids double-nesting when _resolve_local_path is called later
            storage_file_path = str(
                Path(path_prefix.rstrip("/")) / unique_filename
            )  # raw/video.mp4 or demo/video.mp4
        else:
            unique_filename = safe_filename
            # For Supabase, add prefix to match directory structure
            # Storage service will automatically append counter if file exists
            storage_file_path = f"{path_prefix}{unique_filename}"

        # Read file content
        file_content = file.file.read()

        # Upload to storage (local or Supabase)
        try:
            if (
                is_demo
                and settings.STORAGE_TYPE == "supabase"
                and settings.SUPABASE_DEMO_BUCKET
            ):
                # Upload to demo bucket for demo videos
                storage_path = storage_service.upload_demo_object(
                    file_path=storage_file_path,
                    file_content=file_content,
                    content_type=file.content_type,
                )
            else:
                # Upload to regular storage (private bucket or local)
                storage_path = storage_service.upload_file(
                    file_content=file_content,
                    file_path=storage_file_path,
                    content_type=file.content_type,
                )
            # Extract actual filename from storage path (may have counter appended)
            # Storage service returns the actual path used, which may include counter
            actual_filename = Path(storage_path).name
            unique_filename = actual_filename
        except (ValueError, RuntimeError, OSError) as e:
            raise handle_file_error("upload_failed", unique_filename, str(e)) from e

        # For metadata extraction, we need the file locally
        # If using Supabase, use temp file. For local, use actual file path.
        if settings.STORAGE_TYPE == "supabase":
            tmp_path = _create_temp_file_for_processing(file_content, unique_filename)
            try:
                metadata = extract_video_metadata(tmp_path)
            finally:
                tmp_path.unlink()
        else:
            # For local storage, use the actual file path
            file_path = Path(storage_path)
            metadata = extract_video_metadata(file_path)

        # Validate video metadata
        metadata_dict = {
            "width": metadata.width,
            "height": metadata.height,
            "fps": metadata.fps,
            "duration": metadata.duration,
        }
        validate_video_file(file.filename, file_size, file.content_type, metadata_dict)

        # Save to database
        # For storage path, use the storage path returned by storage service
        # For Supabase, this is 'raw/filename.mp4' or 'demo/filename.mp4'. For local, it's the full path.
        db_video = video_service.create_video_record(
            db=db,
            filename=unique_filename,
            file_path=storage_path,  # Use storage path ('raw/filename.mp4' or 'demo/filename.mp4' for Supabase, full path for local)
            file_size=file_size,
            user_id=current_user["id"],  # Associate video with authenticated user
            content_type=file.content_type,
            duration=metadata.duration,
            fps=metadata.fps,
            width=metadata.width,
            height=metadata.height,
            frame_count=metadata.frame_count,
            is_demo=is_demo,
            session_type=session_type,
            camera_angle=camera_angle,
            recorded_at=recorded_at,
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
    Triggers RQ task to calculate elbow angles.
    """
    try:
        from rq import Retry
        from rq.exceptions import RedisConnectionError, RedisTimeoutError

        from app.core.redis_config import analysis_queue
        from app.models.serve_attempt import ServeAttempt
        from app.services.rq_tasks import analyze_serve_attempts_rq

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
            db.query(ServeAttempt)
            .filter(ServeAttempt.video_id == video_id)
            .all()
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

        # Enqueue analysis task
        try:
            job = analysis_queue.enqueue(
                analyze_serve_attempts_rq,
                video_id=video_id,
                retry=Retry(max=2, interval=60),
                job_timeout=300,  # 5 minutes
                result_ttl=3600,  # Keep results for 1 hour
            )
            logger.info(
                f"Enqueued serve analysis job {job.id} for video {video_id}"
            )
        except (RedisConnectionError, RedisTimeoutError) as e:
            logger.error(f"Failed to enqueue job to Redis: {e}")
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail=f"Failed to enqueue analysis job: {e!s}",
            ) from e

        # Return summary (will be updated when analysis completes)
        # Note: Actual results will be available via job status endpoint
        return ServeAnalysisSummary(
            video_id=video_id,
            total_serves=len(serve_attempts),
            serves_with_contact=serves_with_contact,
            avg_elbow_angle=None,  # Will be calculated by RQ task
            recommendations=[],  # Will be populated by recommendation engine when task completes
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.exception("Error starting serve analysis")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to start serve analysis. Please try again later.",
        ) from e
