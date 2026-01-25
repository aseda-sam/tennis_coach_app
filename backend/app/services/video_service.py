import logging
import time
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

import cv2
import numpy as np
from sqlalchemy.orm import Session

from app.models.video import Video

logger = logging.getLogger(__name__)


def create_video_record(
    db: Session,
    filename: str,
    file_path: str,
    file_size: int,
    user_id: str,
    content_type: Optional[str] = None,
    duration: Optional[float] = None,
    fps: Optional[float] = None,
    width: Optional[int] = None,
    height: Optional[int] = None,
    frame_count: Optional[int] = None,
    is_demo: bool = False,
    session_type: Optional[str] = None,
    camera_angle: Optional[str] = None,
    recorded_at: Optional[datetime] = None,
) -> Video:
    """Create a new video record in the database.

    Args:
        db: Database session
        filename: Video filename
        file_path: Path to video file
        file_size: Size of video file in bytes
        user_id: UUID of the user who owns this video (required)
        content_type: MIME type of the video
        duration: Video duration in seconds
        fps: Frames per second
        width: Video width in pixels
        height: Video height in pixels
        frame_count: Total number of frames
        is_demo: Whether this is a demo video
        session_type: Session type ('serve_drill', 'match', 'practice', 'other')
        camera_angle: Camera angle ('behind', 'profile', 'diagonal', 'unknown')
        recorded_at: When video was recorded (for trends)
    """
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
        user_id=user_id,
        is_demo=is_demo,
        session_type=session_type,
        camera_angle=camera_angle,
        recorded_at=recorded_at,
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

    # Get video from database
    video = get_video_by_id(db, video_id)
    if not video:
        raise ValueError(f"Video with ID {video_id} not found")

    filename = video.filename

    try:
        # Delete video annotations
        from app.models.video_annotation import VideoAnnotation
        from app.services.storage_service import storage_service

        video_annotations = (
            db.query(VideoAnnotation).filter(VideoAnnotation.video_id == video_id).all()
        )
        for annotation in video_annotations:
            # Delete annotated video files using storage service
            if annotation.annotated_video_path:
                try:
                    # Use storage service to delete (handles both local and Supabase)
                    storage_service.delete_file(annotation.annotated_video_path)
                    logger.info(
                        f"Deleted video annotation file: {annotation.annotated_video_path}"
                    )
                except (ValueError, RuntimeError, OSError) as e:
                    logger.warning(
                        f"Failed to delete video annotation file {annotation.annotated_video_path}: {e}"
                    )

        # Delete pose detection annotated video files
        from app.models.pose_detection import PoseDetection

        pose_detections = (
            db.query(PoseDetection).filter(PoseDetection.video_id == video_id).all()
        )
        for pose_detection in pose_detections:
            # Delete annotated video files using storage service
            if pose_detection.annotated_video_path:
                try:
                    # Use storage service to delete (handles both local and Supabase)
                    storage_service.delete_file(pose_detection.annotated_video_path)
                    logger.info(
                        f"Deleted pose detection annotated video: {pose_detection.annotated_video_path}"
                    )
                except (ValueError, RuntimeError, OSError) as e:
                    logger.warning(
                        f"Failed to delete pose detection annotated video {pose_detection.annotated_video_path}: {e}"
                    )

        # Delete original video file from storage (local or Supabase)

        try:
            # Use storage service to delete the file
            # For Supabase, file_path is 'raw/filename.mp4'
            # For local, file_path is the full path
            storage_path = video.file_path
            storage_service.delete_file(storage_path)
            logger.info(f"Deleted original video from storage: {storage_path}")
        except (ValueError, RuntimeError, OSError) as e:
            logger.error(
                f"Failed to delete video file from storage {storage_path}: {e}"
            )
            # Continue with database deletion even if file deletion fails

        # Delete from database (this will cascade delete all related records)
        # The cascade relationships will automatically delete:
        # - BallDetection records
        # - PoseDetection records
        # - BallContact records
        # - VideoAnnotation records
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


def extract_frames(
    video_path: Path, max_frames: Optional[int] = None
) -> List[np.ndarray]:
    """
    Extract frames from video file.

    Args:
        video_path: Path to video file
        max_frames: Maximum number of frames to extract (None = extract all frames)

    Returns:
        List of frame arrays
    """
    start_time = time.time()
    frames = []
    try:
        cap = cv2.VideoCapture(str(video_path))
        if not cap.isOpened():
            logger.error(f"Could not open video: {video_path}")
            return frames

        frame_count = 0
        total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
        fps = cap.get(cv2.CAP_PROP_FPS)

        # Use FRAME_SKIP_RATIO from config for proper frame skipping
        from app.core.config import env_limits

        frame_skip_ratio = env_limits["frame_skip_ratio"]

        # Calculate frame interval based on max_frames and frame_skip_ratio
        if max_frames is None:
            # If no max_frames specified, use frame_skip_ratio directly
            interval = frame_skip_ratio
        else:
            # If max_frames specified, calculate interval to get max_frames
            # but respect the minimum frame_skip_ratio
            calculated_interval = (
                total_frames // max_frames if total_frames > max_frames else 1
            )
            interval = max(calculated_interval, frame_skip_ratio)

        # Log frame skipping status
        if frame_skip_ratio > 1:
            logger.info(
                f"Frame skipping enabled: processing every {frame_skip_ratio} frames"
            )
        else:
            logger.info("Frame skipping disabled: processing all frames")

        logger.info(f"Extracting frames from {video_path}")
        logger.info(
            f"Total frames: {total_frames}, FPS: {fps}, Frame skip ratio: {frame_skip_ratio}, Interval: {interval}"
        )

        # Process frames with proper skipping
        while frame_count < total_frames:
            ret, frame = cap.read()
            if not ret:
                break

            # Only keep frames at interval
            if frame_count % interval == 0:
                frames.append(frame)

                # Stop if we've reached max_frames
                if max_frames is not None and len(frames) >= max_frames:
                    break

            frame_count += interval

            # Skip frames to maintain interval
            if interval > 1:
                for _ in range(interval - 1):
                    cap.read()

        cap.release()
        logger.info(f"Extracted {len(frames)} frames using interval {interval}")

    except (OSError, RuntimeError, ValueError) as e:
        logger.error(f"Error extracting frames: {e}")

    elapsed_time = time.time() - start_time
    logger.info(f"⏱️ Frame Extraction completed in {elapsed_time:.3f}s")
    return frames


def get_video_metadata(video_path: Path) -> Dict[str, Any]:
    """
    Extract basic video metadata.

    Args:
        video_path: Path to video file

    Returns:
        Video metadata dictionary
    """
    try:
        cap = cv2.VideoCapture(str(video_path))
        if not cap.isOpened():
            return {"error": "Could not open video file"}

        metadata = {
            "width": int(cap.get(cv2.CAP_PROP_FRAME_WIDTH)),
            "height": int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT)),
            "fps": float(cap.get(cv2.CAP_PROP_FPS)),
            "frame_count": int(cap.get(cv2.CAP_PROP_FRAME_COUNT)),
            "duration": float(cap.get(cv2.CAP_PROP_FRAME_COUNT))
            / float(cap.get(cv2.CAP_PROP_FPS)),
            "codec": int(cap.get(cv2.CAP_PROP_FOURCC)),
        }

        cap.release()
        return metadata

    except (OSError, RuntimeError, ValueError) as e:
        logger.error(f"Error extracting video metadata: {e}")
        return {"error": str(e)}
