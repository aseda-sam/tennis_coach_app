"""Video API routes with proper REST patterns and error handling."""

import logging
import tempfile
import time
from pathlib import Path
from typing import List

import cv2
from fastapi import APIRouter, Depends, File, HTTPException, UploadFile
from fastapi.responses import (
    FileResponse,
    RedirectResponse,
    Response,
    StreamingResponse,
)
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.api.schemas.common import PaginationParams
from app.api.schemas.video import (
    VideoDeleteResponse,
    VideoInfo,
    VideoListItem,
    VideoMetadata,
    VideoQualityAssessmentResponse,
    VideoQualityMetrics,
    VideoUploadResponse,
)
from app.core.config import settings
from app.core.database import get_db
from app.services import video_service
from app.services.storage_service import storage_service
from app.services.video_quality import VideoQualityService
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
    has_annotated_video: bool
    analysis_types: List[str] = []
    annotated_video_available: bool = False


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
    pagination: PaginationParams = Depends(), db: Session = Depends(get_db)
) -> List[VideoListItem]:
    """
    List all uploaded videos.

    Returns a paginated list of videos with basic information.
    """
    try:
        db_videos = video_service.get_all_videos(db)

        # Apply pagination
        start_idx = (pagination.page - 1) * pagination.size
        end_idx = start_idx + pagination.size
        paginated_videos = db_videos[start_idx:end_idx]

        return [VideoListItem.model_validate(video) for video in paginated_videos]
    except (OSError, ValueError) as e:
        log_and_raise_error(e, "list_videos")


@router.get("/{video_id}", response_model=VideoInfo)
async def get_video(video_id: int, db: Session = Depends(get_db)) -> VideoInfo:
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

        return VideoInfo.model_validate(db_video)
    except (OSError, ValueError) as e:
        log_and_raise_error(e, "get_video", {"video_id": video_id})


@router.get("/{video_id}/stream", response_model=None)
async def stream_video(video_id: int, db: Session = Depends(get_db)) -> Response:
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

        # Use storage service to get file
        if settings.STORAGE_TYPE == "supabase":
            # For Supabase, use file_path which contains 'raw/filename.mp4'
            # For local, file_path is the full path, but for Supabase it's the storage path
            storage_path = db_video.file_path
            try:
                file_url = storage_service.get_file_url(storage_path)
                # Redirect to Supabase public URL
                return RedirectResponse(url=file_url)
            except (ValueError, RuntimeError, OSError) as e:
                logger.error(f"Failed to get Supabase URL: {e}")
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


@router.get("/{video_id}/annotated/stream")
async def stream_annotated_video(
    video_id: int, db: Session = Depends(get_db)
) -> Response:
    """
    Stream an annotated video file.

    Args:
        video_id: Unique video identifier

    Returns:
        Annotated video file stream or redirect to storage URL
    """
    try:
        # Get video from database
        db_video = video_service.get_video_by_id(db, video_id)
        if not db_video:
            raise handle_not_found_error("video", str(video_id))

        # Look for annotated video using the new video annotation system
        from app.models.video_annotation import VideoAnnotation

        # First try to find a video annotation record
        video_annotation = (
            db.query(VideoAnnotation)
            .filter(VideoAnnotation.video_id == video_id)
            .order_by(VideoAnnotation.created_at.desc())
            .first()
        )

        annotated_storage_path = None
        annotated_filename = None

        if video_annotation and video_annotation.annotated_video_path:
            # Use the video annotation system
            annotated_storage_path = video_annotation.annotated_video_path
            # Extract filename from path (handles both local paths and Supabase paths)
            annotated_filename = Path(annotated_storage_path).name
            logger.info(f"Using video annotation: {annotated_filename}")
        else:
            # Fallback: Handle cases where filename has suffixes (legacy support)
            base_name = Path(db_video.filename).stem
            processed_dir = Path(settings.PROCESSED_DIR)

            # First try the standard naming pattern
            annotated_filename = f"{base_name}_annotated.mp4"
            annotated_path = processed_dir / annotated_filename

            # If not found, search for files with suffixes (e.g., _2_annotated.mp4)
            if not annotated_path.exists():
                pattern = f"{base_name}_*_annotated.mp4"
                matching_files = list(processed_dir.glob(pattern))
                if matching_files:
                    # Use the most recent file (in case there are multiple)
                    annotated_path = max(
                        matching_files, key=lambda p: p.stat().st_mtime
                    )
                    annotated_filename = annotated_path.name
                    logger.info(
                        f"Found annotated video with suffix: {annotated_filename}"
                    )
                else:
                    # Fallback: search for any file containing the base name
                    # and "annotated"
                    pattern = f"*{base_name}*annotated*.mp4"
                    matching_files = list(processed_dir.glob(pattern))
                    if matching_files:
                        annotated_path = max(
                            matching_files, key=lambda p: p.stat().st_mtime
                        )
                        annotated_filename = annotated_path.name
                        logger.info(
                            f"Found annotated video with flexible pattern: "
                            f"{annotated_filename}"
                        )
                    else:
                        raise handle_not_found_error(
                            "annotated_video", f"for video {video_id}"
                        )

            annotated_storage_path = str(annotated_path)
            validate_file_exists(annotated_path, annotated_filename)

        # Handle Supabase vs local storage
        if settings.STORAGE_TYPE == "supabase":
            # For Supabase, redirect to public URL or stream from Supabase
            try:
                file_url = storage_service.get_file_url(annotated_storage_path)
                # Redirect to Supabase public URL
                return RedirectResponse(url=file_url)
            except (ValueError, RuntimeError, OSError) as e:
                logger.error(f"Failed to get Supabase URL: {e}")
                # Fallback: download and stream
                file_data = storage_service.download_file(annotated_storage_path)
                return StreamingResponse(
                    iter([file_data]),
                    media_type="video/mp4",
                    headers={
                        "Content-Disposition": f'inline; filename="{get_safe_filename(annotated_filename)}"'
                    },
                )
        else:
            # For local storage, use FileResponse
            annotated_path = Path(annotated_storage_path)
            validate_file_exists(annotated_path, annotated_filename)
            return FileResponse(
                path=str(annotated_path),
                media_type="video/mp4",
                filename=get_safe_filename(annotated_filename),
            )
    except (OSError, ValueError) as e:
        log_and_raise_error(e, "stream_annotated_video", {"video_id": video_id})


@router.get("/{video_id}/analysis-status", response_model=VideoAnalysisStatus)
async def get_video_analysis_status(
    video_id: int, db: Session = Depends(get_db)
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

        analysis_types = []
        has_analysis = False
        has_annotated_video = False
        annotated_video_available = False

        # Check for pose detection
        from app.models.pose_detection import PoseDetection

        pose_detection = (
            db.query(PoseDetection).filter(PoseDetection.video_id == video_id).first()
        )
        if pose_detection and pose_detection.status == "completed":
            has_analysis = True
            analysis_types.append("pose_detection")

            # Check if annotated video file exists
            if pose_detection.annotated_video_path:
                annotated_path = Path(pose_detection.annotated_video_path)
                if annotated_path.exists():
                    has_annotated_video = True
                    annotated_video_available = True

        # Check for video annotations
        from app.models.video_annotation import VideoAnnotation

        video_annotation = (
            db.query(VideoAnnotation)
            .filter(VideoAnnotation.video_id == video_id)
            .order_by(VideoAnnotation.created_at.desc())
            .first()
        )

        if video_annotation and video_annotation.annotated_video_path:
            has_annotated_video = True
            annotated_path = Path(video_annotation.annotated_video_path)
            if annotated_path.exists():
                annotated_video_available = True

        return VideoAnalysisStatus(
            video_id=video_id,
            has_analysis=has_analysis,
            has_annotated_video=has_annotated_video,
            analysis_types=analysis_types,
            annotated_video_available=annotated_video_available,
        )

    except (OSError, ValueError) as e:
        log_and_raise_error(e, "get_video_analysis_status", {"video_id": video_id})


@router.delete("/{video_id}", response_model=VideoDeleteResponse)
async def delete_video(
    video_id: int, db: Session = Depends(get_db)
) -> VideoDeleteResponse:
    """
    Delete a video file and database record.

    Args:
        video_id: Unique video identifier

    Returns:
        Deletion confirmation
    """
    try:
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
    db: Session = Depends(get_db),
) -> VideoUploadResponse:
    """
    Upload a video file.

    Args:
        file: Video file to upload

    Returns:
        Upload confirmation with video information
    """
    try:
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

        # For local storage, check uniqueness in local directory
        # For Supabase, we'll use the filename directly (Supabase handles uniqueness)
        if settings.STORAGE_TYPE == "local":
            upload_dir = Path(settings.UPLOAD_DIR)
            upload_dir.mkdir(parents=True, exist_ok=True)
            unique_filename = ensure_unique_filename(safe_filename, upload_dir)
            # For local storage, use filename directly (UPLOAD_DIR already contains 'raw')
            storage_file_path = unique_filename
        else:
            unique_filename = safe_filename
            # For Supabase, add 'raw/' prefix to match local directory structure
            storage_file_path = f"raw/{unique_filename}"

        # Read file content
        file_content = file.file.read()

        # Upload to storage (local or Supabase)
        try:
            storage_path = storage_service.upload_file(
                file_content=file_content,
                file_path=storage_file_path,
                content_type=file.content_type,
            )
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
        # For Supabase, this is 'raw/filename.mp4'. For local, it's the full path.
        db_video = video_service.create_video_record(
            db=db,
            filename=unique_filename,
            file_path=storage_path,  # Use storage path ('raw/filename.mp4' for Supabase, full path for local)
            file_size=file_size,
            content_type=file.content_type,
            duration=metadata.duration,
            fps=metadata.fps,
            width=metadata.width,
            height=metadata.height,
            frame_count=metadata.frame_count,
        )

        # Perform quick quality assessment
        # Reuse file_content already in memory (no need to download from Supabase)
        quality_metrics = None
        try:
            logger.info(f"Starting quality assessment for {unique_filename}")
            quality_service = VideoQualityService()

            if settings.STORAGE_TYPE == "supabase":
                # Reuse file_content already in memory (no download needed)
                tmp_path = _create_temp_file_for_processing(
                    file_content, unique_filename
                )
                try:
                    quality_metrics = quality_service.quick_assess(tmp_path)
                finally:
                    tmp_path.unlink()
            else:
                quality_metrics = quality_service.quick_assess(Path(storage_path))

            # Update video record with quality metrics
            video_service.update_video_quality(
                db=db,
                video_id=db_video.id,
                quality_score=quality_metrics["quality_score"],
                blur_score=quality_metrics["blur_score"],
                lighting_score=quality_metrics["lighting_score"],
                resolution_score=quality_metrics["resolution_score"],
                quality_level=quality_metrics["quality_level"],
            )

            logger.info(
                f"Quality assessment completed: "
                f"{quality_metrics['quality_level']} quality"
            )

        except (OSError, RuntimeError, ValueError) as e:
            logger.warning(f"Quality assessment failed for {unique_filename}: {e}")
            # Continue with upload even if quality assessment fails

        # Create quality metrics response if available
        quality_metrics_response = None
        if quality_metrics:
            quality_metrics_response = VideoQualityMetrics(
                quality_score=quality_metrics["quality_score"],
                blur_score=quality_metrics["blur_score"],
                lighting_score=quality_metrics["lighting_score"],
                resolution_score=quality_metrics["resolution_score"],
                quality_level=quality_metrics["quality_level"],
                recommended_confidence_threshold=quality_metrics[
                    "recommended_confidence_threshold"
                ],
                frame_count_analyzed=quality_metrics["frame_count_analyzed"],
            )

        return VideoUploadResponse(
            video_id=db_video.id,
            filename=db_video.filename,
            file_size=db_video.file_size,
            status="uploaded",
            message="Video uploaded successfully",
            metadata=metadata,
            quality_metrics=quality_metrics_response,
        )
    except (OSError, ValueError) as e:
        log_and_raise_error(
            e, "upload_video", {"filename": file.filename if file else "unknown"}
        )


@router.post("/{video_id}/quality-check", response_model=VideoQualityAssessmentResponse)
async def assess_video_quality(
    video_id: int, db: Session = Depends(get_db)
) -> VideoQualityAssessmentResponse:
    """
    Perform quick quality assessment on a video.

    Args:
        video_id: ID of the video to assess
        db: Database session

    Returns:
        Quality assessment results with metrics and recommendations
    """
    try:
        # Get video from database
        db_video = video_service.get_video_by_id(db, video_id)
        if not db_video:
            raise HTTPException(status_code=404, detail=f"Video {video_id} not found")

        # Check if video file exists
        video_path = Path(db_video.file_path)
        if not video_path.exists():
            raise HTTPException(
                status_code=404, detail=f"Video file not found: {db_video.filename}"
            )

        # Perform quality assessment
        assessment_start = time.time()
        quality_service = VideoQualityService()
        quality_metrics = quality_service.quick_assess(video_path)
        assessment_time = time.time() - assessment_start

        # Update video record with quality metrics
        video_service.update_video_quality(
            db=db,
            video_id=video_id,
            quality_score=quality_metrics["quality_score"],
            blur_score=quality_metrics["blur_score"],
            lighting_score=quality_metrics["lighting_score"],
            resolution_score=quality_metrics["resolution_score"],
            quality_level=quality_metrics["quality_level"],
        )

        # Create response
        quality_metrics_response = VideoQualityMetrics(
            quality_score=quality_metrics["quality_score"],
            blur_score=quality_metrics["blur_score"],
            lighting_score=quality_metrics["lighting_score"],
            resolution_score=quality_metrics["resolution_score"],
            quality_level=quality_metrics["quality_level"],
            recommended_confidence_threshold=quality_metrics[
                "recommended_confidence_threshold"
            ],
            frame_count_analyzed=quality_metrics["frame_count_analyzed"],
        )

        return VideoQualityAssessmentResponse(
            video_id=video_id,
            filename=db_video.filename,
            quality_metrics=quality_metrics_response,
            assessment_time=assessment_time,
            message=(
                f"Quality assessment completed: "
                f"{quality_metrics['quality_level']} quality"
            ),
        )

    except HTTPException:
        raise
    except (OSError, ValueError) as e:
        log_and_raise_error(e, "assess_video_quality", {"video_id": video_id})
