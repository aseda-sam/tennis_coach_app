from typing import List, Optional

from sqlalchemy.orm import Session

from app.models.video import Video


def create_video_record(
    db: Session,
    filename: str,
    file_path: str,
    file_size: int,
    content_type: Optional[str] = None,
    duration: Optional[float] = None,
    fps: Optional[float] = None,
    width: Optional[int] = None,
    height: Optional[int] = None,
    frame_count: Optional[int] = None,
) -> Video:
    """Create a new video record in the database."""
    db_video = Video(
        filename=filename,
        file_path=file_path,
        file_size=file_size,
        content_type=content_type,
        duration=duration,
        fps=fps,
        width=width,
        height=height,
        frame_count=frame_count,
        status="uploaded",
    )
    db.add(db_video)
    db.commit()
    db.refresh(db_video)
    return db_video


def get_video_by_id(db: Session, video_id: int) -> Optional[Video]:
    """Get video by ID."""
    return db.query(Video).filter(Video.id == video_id).first()


def get_video_by_filename(db: Session, filename: str) -> Optional[Video]:
    """Get video by filename."""
    return db.query(Video).filter(Video.filename == filename).first()


def get_all_videos(db: Session) -> List[Video]:
    """Get all videos ordered by creation date."""
    return db.query(Video).order_by(Video.created_at.desc()).all()


def delete_video_record(db: Session, filename: str) -> bool:
    """Delete video record from database."""
    video = db.query(Video).filter(Video.filename == filename).first()
    if video:
        db.delete(video)
        db.commit()
        return True
    return False


def update_video_status(
    db: Session, filename: str, status: str, error_message: Optional[str] = None
) -> Optional[Video]:
    """Update video processing status."""
    video = db.query(Video).filter(Video.filename == filename).first()
    if video:
        video.status = status
        if error_message:
            video.error_message = error_message
        db.commit()
        db.refresh(video)
        return video
    return None


def update_video_quality(
    db: Session,
    video_id: int,
    quality_score: float,
    blur_score: float,
    lighting_score: float,
    resolution_score: float,
    quality_level: str,
) -> Optional[Video]:
    """Update video quality metrics."""
    video = db.query(Video).filter(Video.id == video_id).first()
    if video:
        video.quality_score = quality_score
        video.blur_score = blur_score
        video.lighting_score = lighting_score
        video.resolution_score = resolution_score
        video.quality_level = quality_level
        # Set quality_assessed_at to current timestamp
        from sqlalchemy.sql import func

        video.quality_assessed_at = func.now()
        db.commit()
        db.refresh(video)
        return video
    return None
