from pathlib import Path
from typing import List, Optional

import cv2
from fastapi import APIRouter, Depends, File, HTTPException, UploadFile
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.database import get_db
from app.services.video_service import (
    create_video_record,
    delete_video_record,
    get_all_videos,
    get_video_by_filename,
)

router = APIRouter()


class VideoInfo(BaseModel):
    """Video information including metadata."""

    filename: str
    file_size: int
    content_type: Optional[str] = None
    duration: Optional[float] = None  # seconds
    fps: Optional[float] = None
    width: Optional[int] = None
    height: Optional[int] = None
    frame_count: Optional[int] = None
    message: str


class VideoListItem(BaseModel):
    """Video information for list endpoint."""

    filename: str
    file_size: int
    duration: Optional[float] = None
    width: Optional[int] = None
    height: Optional[int] = None


def extract_video_metadata(video_path: Path) -> dict:
    """Extract metadata from video file using OpenCV."""
    try:
        cap = cv2.VideoCapture(str(video_path))
        if not cap.isOpened():
            return {}

        # Get video properties
        fps = cap.get(cv2.CAP_PROP_FPS)
        frame_count = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
        width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
        height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))

        # Calculate duration
        duration = frame_count / fps if fps > 0 else None

        cap.release()

        return {
            "fps": fps,
            "frame_count": frame_count,
            "width": width,
            "height": height,
            "duration": duration,
        }
    except (cv2.error, OSError, ValueError):
        # Return empty dict if metadata extraction fails
        return {}





@router.get("/", response_model=List[VideoListItem])
async def list_videos(db: Session = Depends(get_db)) -> List[VideoListItem]:
    """List all uploaded videos from database."""
    db_videos = get_all_videos(db)
    videos = []

    for db_video in db_videos:
        videos.append(
            VideoListItem(
                filename=db_video.filename,
                file_size=db_video.file_size,
                duration=db_video.duration,
                width=db_video.width,
                height=db_video.height,
            )
        )

    return videos


@router.get("/{filename}", response_model=VideoInfo)
async def get_video_details(filename: str, db: Session = Depends(get_db)) -> VideoInfo:
    """Get detailed information about a specific video from database."""
    db_video = get_video_by_filename(db, filename)

    if not db_video:
        raise HTTPException(status_code=404, detail=f"Video {filename} not found")

    return VideoInfo(
        filename=db_video.filename,
        file_size=db_video.file_size,
        content_type=db_video.content_type,
        duration=db_video.duration,
        fps=db_video.fps,
        width=db_video.width,
        height=db_video.height,
        frame_count=db_video.frame_count,
        message="Video details retrieved successfully",
    )


@router.delete("/{filename}")
async def delete_video(filename: str, db: Session = Depends(get_db)) -> dict:
    """Delete a video file and database record."""
    # Check if video exists in database
    db_video = get_video_by_filename(db, filename)
    if not db_video:
        raise HTTPException(status_code=404, detail=f"Video {filename} not found")

    # Delete from file system
    upload_dir = Path(settings.UPLOAD_DIR)
    file_path = upload_dir / filename

    if file_path.exists() and file_path.is_file():
        try:
            file_path.unlink()
        except OSError as e:
            raise HTTPException(
                status_code=500, detail=f"Failed to delete video file: {e}"
            ) from e

    # Delete from database
    if not delete_video_record(db, filename):
        raise HTTPException(status_code=500, detail="Failed to delete video record")

    return {"message": f"Video {filename} deleted successfully"}


@router.post("/upload", response_model=VideoInfo)
async def upload_video(file: UploadFile = File(...), db: Session = Depends(get_db)) -> VideoInfo:
    """Upload a video file and return basic information with metadata."""

    # Validate file
    if not file.filename:
        raise HTTPException(status_code=400, detail="No file provided")

    # Check file size
    file.file.seek(0, 2)  # Seek to end
    file_size = file.file.tell()
    file.file.seek(0)  # Reset to beginning

    if file_size > settings.MAX_FILE_SIZE:
        raise HTTPException(
            status_code=400,
            detail=f"File size {file_size} exceeds maximum {settings.MAX_FILE_SIZE}",
        )

    # Check file format
    file_ext = Path(file.filename).suffix.lower()
    if file_ext not in settings.SUPPORTED_FORMATS:
        raise HTTPException(
            status_code=400,
            detail=f"Unsupported format {file_ext}. Supported: {settings.SUPPORTED_FORMATS}",
        )

    # Create upload directory if it doesn't exist
    upload_dir = Path(settings.UPLOAD_DIR)
    upload_dir.mkdir(parents=True, exist_ok=True)

    # Save file
    file_path = upload_dir / file.filename
    try:
        with open(file_path, "wb") as buffer:
            content = file.file.read()
            buffer.write(content)
    except OSError as e:
        raise HTTPException(
            status_code=500, detail=f"Failed to save file: {e!s}"
        ) from e

    # Extract video metadata
    metadata = extract_video_metadata(file_path)

    # Save to database
    db_video = create_video_record(
        db=db,
        filename=file.filename,
        file_path=str(file_path),
        file_size=file_size,
        content_type=file.content_type,
        duration=metadata.get("duration"),
        fps=metadata.get("fps"),
        width=metadata.get("width"),
        height=metadata.get("height"),
        frame_count=metadata.get("frame_count"),
    )

    return VideoInfo(
        filename=db_video.filename,
        file_size=db_video.file_size,
        content_type=db_video.content_type,
        duration=db_video.duration,
        fps=db_video.fps,
        width=db_video.width,
        height=db_video.height,
        frame_count=db_video.frame_count,
        message="Video uploaded successfully",
    )
