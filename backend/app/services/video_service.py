import logging
import tempfile
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

import cv2
import numpy as np
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.core.config import settings
from app.models.ball_detection import BallDetection
from app.models.pose_detection import PoseDetection
from app.models.video import Video
from app.services import player_service
from app.services.storage_service import storage_service
from app.utils.error_handling import handle_file_error
from app.utils.file_validation import (
    VideoMetadataDict,
    ensure_unique_filename,
    get_safe_filename,
    validate_video_file,
)
from app.utils.video_utils import get_video_creation_time, get_video_rotation

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
    recorded_at_source: Optional[str] = None,
    primary_player_id: Optional[int] = None,
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
        session_type: Session type ('serve_practice', 'match', 'other')
        camera_angle: Camera angle ('behind', 'profile', 'unknown')
        recorded_at: When video was recorded (for trends)
        recorded_at_source: Source of recorded_at ('metadata', 'client', 'upload_time')
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
        recorded_at_source=recorded_at_source,
        primary_player_id=primary_player_id,
    )
    db.add(db_video)
    db.commit()
    db.refresh(db_video)
    return db_video


def _create_temp_file_for_processing(file_content: bytes, filename: str) -> Path:
    """Create a temporary file for video processing (metadata extraction)."""
    with tempfile.NamedTemporaryFile(
        delete=False, suffix=Path(filename).suffix
    ) as tmp_file:
        tmp_file.write(file_content)
        tmp_path = Path(tmp_file.name)
    return tmp_path


def extract_video_metadata(
    video_path: Path,
) -> VideoMetadataDict:
    """Extract metadata from video file using OpenCV and ffprobe."""
    try:
        cap = cv2.VideoCapture(str(video_path))
        if not cap.isOpened():
            return {
                "duration": None,
                "fps": None,
                "width": None,
                "height": None,
                "frame_count": None,
                "recorded_at": None,
            }

        fps = cap.get(cv2.CAP_PROP_FPS)
        frame_count = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
        raw_width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
        raw_height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))

        cap.release()

        rotation = get_video_rotation(video_path)

        if rotation in (90, 270, -90, -270):
            width, height = raw_height, raw_width
        else:
            width, height = raw_width, raw_height

        duration = frame_count / fps if fps > 0 else None
        recorded_at = get_video_creation_time(video_path)

        return {
            "duration": duration,
            "fps": fps,
            "width": width,
            "height": height,
            "frame_count": frame_count,
            "recorded_at": recorded_at,
        }
    except (cv2.error, OSError, ValueError):
        return {
            "duration": None,
            "fps": None,
            "width": None,
            "height": None,
            "frame_count": None,
            "recorded_at": None,
        }


def _ensure_unique_db_filename(db: Session, filename: str) -> str:
    """Ensure filename is unique in the database."""
    base_name = Path(filename).stem
    extension = Path(filename).suffix
    candidate = filename
    counter = 0

    while get_video_by_filename(db, candidate) is not None:
        counter += 1
        candidate = f"{base_name}_{counter}{extension}"

    return candidate


def handle_video_upload(
    *,
    db: Session,
    file_content: bytes,
    filename: str,
    file_size: int,
    content_type: Optional[str],
    is_demo: bool,
    user_id: str,
    session_type: Optional[str],
    camera_angle: Optional[str],
    recorded_at: Optional[datetime],
    client_recorded_at: Optional[datetime] = None,
) -> tuple[Video, VideoMetadataDict]:
    """Handle common upload flow and create video record."""
    if not filename:
        raise handle_file_error("invalid", "", "No file provided")

    validate_video_file(filename, file_size, content_type, file_content=file_content)

    safe_filename = get_safe_filename(filename)
    path_prefix = "demo/" if is_demo else "raw/"

    if settings.STORAGE_TYPE == "local":
        base_upload_dir = Path(settings.UPLOAD_DIR).parent
        upload_dir = base_upload_dir / path_prefix.rstrip("/")
        upload_dir.mkdir(parents=True, exist_ok=True)
        # Check DB uniqueness first, then filesystem — avoids IntegrityError when a
        # file was previously uploaded (DB record exists) but later deleted from disk.
        db_unique_filename = _ensure_unique_db_filename(db, safe_filename)
        unique_filename = ensure_unique_filename(db_unique_filename, upload_dir)
        storage_file_path = str(Path(path_prefix.rstrip("/")) / unique_filename)
    else:
        unique_filename = _ensure_unique_db_filename(db, safe_filename)
        storage_file_path = f"{path_prefix}{unique_filename}"

    tmp_path = _create_temp_file_for_processing(file_content, unique_filename)
    try:
        metadata = extract_video_metadata(tmp_path)
    finally:
        tmp_path.unlink()

    validate_video_file(filename, file_size, content_type, metadata)

    try:
        if (
            is_demo
            and settings.STORAGE_TYPE == "supabase"
            and settings.SUPABASE_DEMO_BUCKET
        ):
            storage_path = storage_service.upload_demo_object(
                file_path=storage_file_path,
                file_content=file_content,
                content_type=content_type,
            )
        else:
            storage_path = storage_service.upload_file(
                file_content=file_content,
                file_path=storage_file_path,
                content_type=content_type,
            )
        actual_filename = Path(storage_path).name
        unique_filename = actual_filename
    except (ValueError, RuntimeError, OSError) as e:
        raise handle_file_error("upload_failed", unique_filename, str(e)) from e

    final_recorded_at: Optional[datetime] = None
    recorded_at_source: Optional[str] = None

    if metadata.get("recorded_at"):
        final_recorded_at = metadata["recorded_at"]
        recorded_at_source = "metadata"
    elif client_recorded_at:
        final_recorded_at = client_recorded_at
        recorded_at_source = "client"
    elif recorded_at:
        final_recorded_at = recorded_at
        recorded_at_source = "upload_time"
    else:
        final_recorded_at = datetime.now(timezone.utc)
        recorded_at_source = "upload_time"

    default_player = player_service.get_or_create_default_player(db, user_id)

    db_video = create_video_record(
        db=db,
        filename=unique_filename,
        file_path=storage_path,
        file_size=file_size,
        user_id=user_id,
        content_type=content_type,
        duration=metadata["duration"],
        fps=metadata["fps"],
        width=metadata["width"],
        height=metadata["height"],
        frame_count=metadata["frame_count"],
        is_demo=is_demo,
        session_type=session_type,
        camera_angle=camera_angle,
        recorded_at=final_recorded_at,
        recorded_at_source=recorded_at_source,
        primary_player_id=default_player.id,
    )

    return db_video, metadata


def get_video_by_id(db: Session, video_id: int) -> Optional[Video]:
    """Get video by ID."""
    return db.query(Video).filter(Video.id == video_id).first()


def get_video_by_filename(db: Session, filename: str) -> Optional[Video]:
    """Get video by filename."""
    return db.query(Video).filter(Video.filename == filename).first()


def get_all_videos(db: Session) -> List[Video]:
    """Get all videos ordered by creation date."""
    return db.query(Video).order_by(Video.created_at.desc()).all()


def list_user_videos(
    db: Session,
    user_id: str,
    is_admin: bool = False,
    skip: int = 0,
    limit: int = 20,
    camera_angle: Optional[str] = None,
    player_id: Optional[int] = None,
    exclude_player_id: Optional[int] = None,
) -> List[Video]:
    """List videos for a user with pagination.

    Excludes demo videos from user's library.
    Admins see all non-demo videos.

    Args:
        db: Database session
        user_id: User ID to filter by (if not admin)
        is_admin: Whether the user is an admin
        skip: Number of videos to skip (for pagination)
        limit: Maximum number of videos to return
        camera_angle: Optional filter by camera angle
        player_id: Optional filter by primary player ID
        exclude_player_id: Optional exclude videos with this player ID

    Returns:
        List of Video instances ordered by recorded_at (fallback created_at), newest first
    """
    query = db.query(Video).filter(~Video.is_demo)

    if not is_admin:
        query = query.filter(Video.user_id == user_id)

    if camera_angle is not None:
        query = query.filter(Video.camera_angle == camera_angle)
    if player_id is not None:
        query = query.filter(Video.primary_player_id == player_id)
    if exclude_player_id is not None:
        query = query.filter(
            Video.primary_player_id.isnot(None),
            Video.primary_player_id != exclude_player_id,
        )

    return (
        query.order_by(func.coalesce(Video.recorded_at, Video.created_at).desc())
        .offset(skip)
        .limit(limit)
        .all()
    )


def get_active_demo_video(db: Session) -> Optional[Video]:
    """Get the active demo video (is_active_demo=True).

    Args:
        db: Database session

    Returns:
        Video object or None if no active demo exists
    """
    return db.query(Video).filter(Video.is_active_demo.is_(True)).first()


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
        from app.services.storage_service import storage_service

        # Delete original video file from storage (local or Supabase)

        try:
            # Use storage service to delete the file
            # For Supabase, file_path is 'raw/filename.mp4'
            # For local, file_path is the full path
            storage_path = video.file_path
            storage_service.delete_file(storage_path)
            logger.info("Deleted original video from storage: %s", storage_path)
        except (ValueError, RuntimeError, OSError) as e:
            logger.error(
                "Failed to delete video file from storage %s: %s", storage_path, e
            )
            # Continue with database deletion even if file deletion fails

        # Delete from database (this will cascade delete all related records)
        # The cascade relationships will automatically delete:
        # - PoseDetection records
        if not delete_video_record(db, video_id):
            logger.error("Database deletion failed for video %s", video_id)
            return False, filename, video_id

        return True, filename, video_id

    except (OSError, ValueError, RuntimeError) as e:
        logger.error("Error during video deletion for %s: %s", video_id, e)
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


def update_video_metadata(
    db: Session,
    video_id: int,
    session_type: Optional[str] = None,
    camera_angle: Optional[str] = None,
    primary_player_id: Optional[int] = None,
    title: Optional[str] = None,
    notes: Optional[str] = None,
    recorded_at: Optional[datetime] = None,
) -> Optional[Video]:
    """Update video metadata (session_type, camera_angle, primary_player_id, title, notes, recorded_at).

    Args:
        db: Database session
        video_id: Video ID to update
        session_type: Session type ('serve_practice', 'match', 'other')
        camera_angle: Camera angle ('behind', 'profile', 'unknown')
        primary_player_id: Default player ID for serves from this video

    Returns:
        Updated Video object, or None if video not found
    """
    video = get_video_by_id(db, video_id)
    if not video:
        return None

    if session_type is not None:
        video.session_type = session_type
    if camera_angle is not None:
        video.camera_angle = camera_angle
    if primary_player_id is not None:
        video.primary_player_id = primary_player_id
    if title is not None:
        video.title = title
    if notes is not None:
        video.notes = notes
    if recorded_at is not None:
        video.recorded_at = recorded_at
        video.recorded_at_source = "user"

    db.commit()
    db.refresh(video)
    return video


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
            logger.error("Could not open video: %s", video_path)
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

        logger.info("Extracting frames from %s", video_path)
        logger.info(
            "Total frames: %s, FPS: %s, Frame skip ratio: %s, Interval: %s",
            total_frames,
            fps,
            frame_skip_ratio,
            interval,
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
        logger.info("Extracted %s frames using interval %s", len(frames), interval)

    except (OSError, RuntimeError, ValueError) as e:
        logger.error("Error extracting frames: %s", e)

    elapsed_time = time.time() - start_time
    logger.info("⏱️ Frame Extraction completed in %.3fs", elapsed_time)
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
        logger.error("Error extracting video metadata: %s", e)
        return {"error": str(e)}


def get_video_analysis_status(db: Session, video_id: int) -> dict:
    """Get analysis status for a single video.

    Args:
        db: Database session
        video_id: Video ID

    Returns:
        Dict with video_id, has_analysis (bool), and analysis_types (list)

    Raises:
        ValueError: If video not found
    """
    db_video = get_video_by_id(db, video_id)
    if not db_video:
        raise ValueError(f"Video with ID {video_id} not found")

    analysis_types = []
    has_analysis = False

    # Check for pose detection
    pose_detection = (
        db.query(PoseDetection).filter(PoseDetection.video_id == video_id).first()
    )
    if pose_detection and pose_detection.status == "completed":
        has_analysis = True
        analysis_types.append("pose_detection")

    # Check for ball detection
    ball_detection = (
        db.query(BallDetection)
        .filter(BallDetection.video_id == video_id)
        .order_by(BallDetection.created_at.desc())
        .first()
    )
    has_ball_detection = bool(ball_detection and ball_detection.status == "completed")
    if has_ball_detection:
        analysis_types.append("ball_detection")

    return {
        "video_id": video_id,
        "has_analysis": has_analysis,
        "analysis_types": analysis_types,
        "has_ball_detection": has_ball_detection,
        "ball_detection_rate": ball_detection.detection_rate
        if ball_detection and ball_detection.status == "completed"
        else None,
        "ball_detection_status": ball_detection.status if ball_detection else None,
    }


def get_bulk_analysis_status(
    db: Session,
    video_ids: List[int],
    user_id: str,
    is_admin: bool = False,
) -> List[dict]:
    """Get analysis status for multiple videos in bulk.

    Args:
        db: Database session
        video_ids: List of video IDs to check
        user_id: User ID for authorization check
        is_admin: Whether the user is an admin (admins can see all videos)

    Returns:
        List of analysis status dicts, one per video_id

    Raises:
        ValueError: If any video not found or access denied
    """
    # Verify all videos exist and user has access
    query = db.query(Video).filter(Video.id.in_(video_ids))
    if not is_admin:
        query = query.filter(Video.user_id == user_id)

    accessible_videos = {video.id for video in query.all()}

    # Check for unauthorized access
    unauthorized_ids = set(video_ids) - accessible_videos
    if unauthorized_ids:
        raise ValueError(f"Videos not found or access denied: {list(unauthorized_ids)}")

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
        db.query(BallDetection).filter(BallDetection.video_id.in_(video_ids)).all()
    )

    # Build lookup maps for O(1) access
    pose_map: Dict[int, PoseDetection] = {pd.video_id: pd for pd in pose_detections}
    ball_map: Dict[int, BallDetection] = {}
    for bd in ball_detections:
        # Keep the most recent per video
        if bd.video_id not in ball_map or (
            bd.created_at
            and ball_map[bd.video_id].created_at
            and bd.created_at > ball_map[bd.video_id].created_at
        ):
            ball_map[bd.video_id] = bd

    # Build response for each video
    statuses = []
    for video_id in video_ids:
        analysis_types = []
        has_analysis = False

        if video_id in pose_map:
            has_analysis = True
            analysis_types.append("pose_detection")

        ball_det = ball_map.get(video_id)
        has_ball = bool(ball_det and ball_det.status == "completed")
        if has_ball:
            analysis_types.append("ball_detection")

        statuses.append(
            {
                "video_id": video_id,
                "has_analysis": has_analysis,
                "analysis_types": analysis_types,
                "has_ball_detection": has_ball,
                "ball_detection_rate": ball_det.detection_rate
                if ball_det and ball_det.status == "completed"
                else None,
                "ball_detection_status": ball_det.status if ball_det else None,
            }
        )

    return statuses
