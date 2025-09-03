import logging
from datetime import datetime
from typing import List, Optional

from sqlalchemy.orm import Session

from app.models.video import Video

logger = logging.getLogger(__name__)


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


def delete_video_record(db: Session, video_id: int) -> bool:
    """Delete video record from database by ID."""
    video = db.query(Video).filter(Video.id == video_id).first()
    if video:
        db.delete(video)
        db.commit()
        return True
    return False


def delete_video_by_filename(db: Session, filename: str) -> bool:
    """Delete video record from database by filename."""
    video = db.query(Video).filter(Video.filename == filename).first()
    if video:
        db.delete(video)
        db.commit()
        return True
    return False


def delete_video_with_analyses(db: Session, video_id: int) -> tuple[bool, str, int]:
    """
    Delete a video and all its associated analyses, including file cleanup.

    Args:
        db: Database session
        video_id: ID of the video to delete

    Returns:
        Tuple of (success: bool, filename: str, video_id: int)
    """
    from pathlib import Path

    from app.core.config import settings
    from app.models.analysis import Analysis

    # Get video from database
    video = get_video_by_id(db, video_id)
    if not video:
        from app.utils.error_handling import handle_not_found_error

        raise handle_not_found_error("Video", str(video_id))

    filename = video.filename

    try:
        # Delete associated analysis files first (before cascade deletion)
        analyses = db.query(Analysis).filter(Analysis.video_id == video_id).all()
        for analysis in analyses:
            # Delete annotated video files
            if analysis.annotated_video_path:
                annotated_path = Path(analysis.annotated_video_path)
                if annotated_path.exists():
                    try:
                        annotated_path.unlink()
                        logger.info(f"Deleted annotated video: {annotated_path}")
                    except OSError as e:
                        logger.warning(
                            f"Failed to delete annotated video {annotated_path}: {e}"
                        )

        # Delete video annotations
        from app.models.video_annotation import VideoAnnotation

        video_annotations = (
            db.query(VideoAnnotation).filter(VideoAnnotation.video_id == video_id).all()
        )
        for annotation in video_annotations:
            # Delete annotated video files
            if annotation.annotated_video_path:
                annotated_path = Path(annotation.annotated_video_path)
                if annotated_path.exists():
                    try:
                        annotated_path.unlink()
                        logger.info(f"Deleted video annotation file: {annotated_path}")
                    except OSError as e:
                        logger.warning(
                            f"Failed to delete video annotation file {annotated_path}: {e}"
                        )

        # Delete original video file from file system
        upload_dir = Path(settings.UPLOAD_DIR)
        file_path = upload_dir / filename

        if file_path.exists() and file_path.is_file():
            try:
                file_path.unlink()
                logger.info(f"Deleted original video: {file_path}")
            except OSError as e:
                logger.error(f"Failed to delete video file {file_path}: {e}")
                # Continue with database deletion even if file deletion fails

        # Delete from database (this will cascade delete analyses)
        if not delete_video_record(db, video_id):
            logger.error(f"Database deletion failed for video {video_id}")
            return False, filename, video_id

        return True, filename, video_id

    except (OSError, ValueError, RuntimeError) as e:
        logger.error(f"Error during video deletion for {video_id}: {e}")
        return False, filename, video_id


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
        video.quality_assessed_at = datetime.utcnow()
        db.commit()
        db.refresh(video)
        return video
    return None
