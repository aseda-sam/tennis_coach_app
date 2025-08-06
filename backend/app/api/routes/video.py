from pathlib import Path
from typing import List, Optional

import cv2
from fastapi import APIRouter, File, HTTPException, UploadFile
from pydantic import BaseModel

from app.core.config import settings

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


def get_video_files() -> List[Path]:
    """Get list of video files in upload directory."""
    upload_dir = Path(settings.UPLOAD_DIR)
    if not upload_dir.exists():
        return []

    video_files = []
    for file_path in upload_dir.iterdir():
        if file_path.is_file() and file_path.suffix.lower() in settings.SUPPORTED_FORMATS:
            video_files.append(file_path)

    return sorted(video_files, key=lambda x: x.stat().st_mtime, reverse=True)


@router.get("/", response_model=List[VideoListItem])
async def list_videos() -> List[VideoListItem]:
    """List all uploaded videos."""
    video_files = get_video_files()
    videos = []

    for file_path in video_files:
        file_size = file_path.stat().st_size
        metadata = extract_video_metadata(file_path)

        videos.append(VideoListItem(
            filename=file_path.name,
            file_size=file_size,
            duration=metadata.get("duration"),
            width=metadata.get("width"),
            height=metadata.get("height")
        ))

    return videos


@router.get("/{filename}", response_model=VideoInfo)
async def get_video_details(filename: str) -> VideoInfo:
    """Get detailed information about a specific video."""
    upload_dir = Path(settings.UPLOAD_DIR)
    file_path = upload_dir / filename

    if not file_path.exists():
        raise HTTPException(status_code=404, detail=f"Video {filename} not found")

    if not file_path.is_file():
        raise HTTPException(status_code=400, detail=f"{filename} is not a file")

    if file_path.suffix.lower() not in settings.SUPPORTED_FORMATS:
        raise HTTPException(status_code=400, detail=f"Unsupported format: {file_path.suffix}")

    file_size = file_path.stat().st_size
    metadata = extract_video_metadata(file_path)

    return VideoInfo(
        filename=filename,
        file_size=file_size,
        content_type="video/mp4",  # Default, could be enhanced
        duration=metadata.get("duration"),
        fps=metadata.get("fps"),
        width=metadata.get("width"),
        height=metadata.get("height"),
        frame_count=metadata.get("frame_count"),
        message="Video details retrieved successfully"
    )


@router.delete("/{filename}")
async def delete_video(filename: str) -> dict:
    """Delete a video file."""
    upload_dir = Path(settings.UPLOAD_DIR)
    file_path = upload_dir / filename

    if not file_path.exists():
        raise HTTPException(status_code=404, detail=f"Video {filename} not found")

    if not file_path.is_file():
        raise HTTPException(status_code=400, detail=f"{filename} is not a file")

    try:
        file_path.unlink()
        return {"message": f"Video {filename} deleted successfully"}
    except OSError as e:
        raise HTTPException(status_code=500, detail=f"Failed to delete video: {e}") from e


@router.post("/upload", response_model=VideoInfo)
async def upload_video(file: UploadFile = File(...)) -> VideoInfo:
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

    return VideoInfo(
        filename=file.filename,
        file_size=file_size,
        content_type=file.content_type,
        duration=metadata.get("duration"),
        fps=metadata.get("fps"),
        width=metadata.get("width"),
        height=metadata.get("height"),
        frame_count=metadata.get("frame_count"),
        message="Video uploaded successfully",
    )
