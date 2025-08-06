from fastapi import APIRouter, UploadFile, File, HTTPException
from pydantic import BaseModel
from typing import Optional
import os
from pathlib import Path

from app.core.config import settings

router = APIRouter()

class VideoInfo(BaseModel):
    """Basic video information."""
    filename: str
    file_size: int
    content_type: Optional[str] = None
    message: str

@router.post("/upload", response_model=VideoInfo)
async def upload_video(file: UploadFile = File(...)) -> VideoInfo:
    """Upload a video file and return basic information."""
    
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
            detail=f"File size {file_size} exceeds maximum {settings.MAX_FILE_SIZE}"
        )
    
    # Check file format
    file_ext = Path(file.filename).suffix.lower()
    if file_ext not in settings.SUPPORTED_FORMATS:
        raise HTTPException(
            status_code=400, 
            detail=f"Unsupported format {file_ext}. Supported: {settings.SUPPORTED_FORMATS}"
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
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to save file: {str(e)}")
    
    return VideoInfo(
        filename=file.filename,
        file_size=file_size,
        content_type=file.content_type,
        message="Video uploaded successfully"
    ) 