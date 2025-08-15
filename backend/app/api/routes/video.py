"""Video API routes with proper REST patterns and error handling."""

from pathlib import Path
from typing import List

import cv2
from fastapi import APIRouter, Depends, File, Form, UploadFile
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session

from app.api.schemas.common import PaginationParams
from app.api.schemas.video import (
    VideoDeleteResponse,
    VideoInfo,
    VideoListItem,
    VideoMetadata,
    VideoUploadResponse,
)
from app.core.config import settings
from app.core.database import get_db
from app.services.video_service import (
    create_video_record,
    delete_video_record,
    get_all_videos,
    get_video_by_id,
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

router = APIRouter()


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
        db_videos = get_all_videos(db)

        # Apply pagination
        start_idx = (pagination.page - 1) * pagination.size
        end_idx = start_idx + pagination.size
        paginated_videos = db_videos[start_idx:end_idx]

        return [VideoListItem.from_orm(video) for video in paginated_videos]
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
        db_video = get_video_by_id(db, video_id)
        if not db_video:
            raise handle_not_found_error("video", str(video_id))

        return VideoInfo.from_orm(db_video)
    except (OSError, ValueError) as e:
        log_and_raise_error(e, "get_video", {"video_id": video_id})


@router.get("/{video_id}/stream")
async def stream_video(video_id: int, db: Session = Depends(get_db)) -> FileResponse:
    """
    Stream a video file.

    Args:
        video_id: Unique video identifier

    Returns:
        Video file stream
    """
    try:
        # Get video from database
        db_video = get_video_by_id(db, video_id)
        if not db_video:
            raise handle_not_found_error("video", str(video_id))

        # Check if file exists on disk
        upload_dir = Path(settings.UPLOAD_DIR)
        file_path = upload_dir / db_video.filename

        validate_file_exists(file_path, db_video.filename)

        # Return the video file with safe filename to prevent header injection
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
) -> FileResponse:
    """
    Stream an annotated video file.

    Args:
        video_id: Unique video identifier

    Returns:
        Annotated video file stream
    """
    try:
        # Get video from database
        db_video = get_video_by_id(db, video_id)
        if not db_video:
            raise handle_not_found_error("video", str(video_id))

        # Look for annotated video
        annotated_filename = f"{Path(db_video.filename).stem}_annotated.mp4"
        processed_dir = Path(settings.PROCESSED_DIR)
        annotated_path = processed_dir / annotated_filename

        validate_file_exists(annotated_path, annotated_filename)

        return FileResponse(
            path=str(annotated_path),
            media_type="video/mp4",
            filename=get_safe_filename(annotated_filename),
        )
    except (OSError, ValueError) as e:
        log_and_raise_error(e, "stream_annotated_video", {"video_id": video_id})


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
        # Get video from database
        db_video = get_video_by_id(db, video_id)
        if not db_video:
            raise handle_not_found_error("video", str(video_id))

        # Delete from file system
        upload_dir = Path(settings.UPLOAD_DIR)
        file_path = upload_dir / db_video.filename

        if file_path.exists() and file_path.is_file():
            try:
                file_path.unlink()
            except OSError as e:
                raise handle_file_error(
                    "delete_failed", db_video.filename, str(e)
                ) from e

        # Delete from database
        if not delete_video_record(db, db_video.filename):
            raise handle_file_error(
                "delete_failed", db_video.filename, "Database deletion failed"
            )

        return VideoDeleteResponse(
            message=f"Video {db_video.filename} deleted successfully",
            video_id=video_id,
            filename=db_video.filename,
        )
    except (OSError, ValueError) as e:
        log_and_raise_error(e, "delete_video", {"video_id": video_id})


@router.post("/upload", response_model=VideoUploadResponse)
async def upload_video(
    file: UploadFile = File(...),
    description: str = Form(None),
    db: Session = Depends(get_db),
) -> VideoUploadResponse:
    """
    Upload a video file.

    Args:
        file: Video file to upload
        description: Optional description of the video

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

        # Create upload directory if it doesn't exist
        upload_dir = Path(settings.UPLOAD_DIR)
        upload_dir.mkdir(parents=True, exist_ok=True)

        # Ensure safe and unique filename
        safe_filename = get_safe_filename(file.filename)
        unique_filename = ensure_unique_filename(safe_filename, upload_dir)

        # Save file
        file_path = upload_dir / unique_filename
        try:
            with open(file_path, "wb") as buffer:
                content = file.file.read()
                buffer.write(content)
        except OSError as e:
            raise handle_file_error("upload_failed", unique_filename, str(e)) from e

        # Extract video metadata
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
        db_video = create_video_record(
            db=db,
            filename=unique_filename,
            file_path=str(file_path),
            file_size=file_size,
            content_type=file.content_type,
            duration=metadata.duration,
            fps=metadata.fps,
            width=metadata.width,
            height=metadata.height,
            frame_count=metadata.frame_count,
        )

        return VideoUploadResponse(
            video_id=db_video.id,
            filename=db_video.filename,
            file_size=db_video.file_size,
            status="uploaded",
            message="Video uploaded successfully",
            metadata=metadata,
        )
    except (OSError, ValueError) as e:
        log_and_raise_error(
            e, "upload_video", {"filename": file.filename if file else "unknown"}
        )
