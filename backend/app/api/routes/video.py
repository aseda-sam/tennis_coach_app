from pathlib import Path
from typing import Optional

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
