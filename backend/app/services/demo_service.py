"""Service for demo video management."""

import logging
from typing import List

from sqlalchemy import func
from sqlalchemy.orm import Session

from app.core.config import settings
from app.models.pose_detection import PoseDetection
from app.models.serve_window import ServeWindow
from app.models.video import Video
from app.models.video_job import VideoJob
from app.services import video_service
from app.services.rq_tasks import enqueue_pose_analysis
from app.services.storage_service import storage_service

logger = logging.getLogger(__name__)


def list_demo_videos_with_status(db: Session) -> List[dict]:
    """List all demo videos with status information.

    Args:
        db: Database session

    Returns:
        List of demo video dictionaries with status information
    """
    demo_videos = (
        db.query(Video).filter(Video.is_demo.is_(True)).order_by(Video.id.desc()).all()
    )
    if not demo_videos:
        return []

    video_ids = [video.id for video in demo_videos]

    completed_pose_video_ids = {
        row[0]
        for row in db.query(PoseDetection.video_id)
        .filter(
            PoseDetection.video_id.in_(video_ids),
            PoseDetection.status == "completed",
        )
        .distinct()
        .all()
    }

    serve_count_rows = (
        db.query(ServeWindow.video_id, func.count(ServeWindow.id))
        .filter(ServeWindow.video_id.in_(video_ids))
        .group_by(ServeWindow.video_id)
        .all()
    )
    serve_counts = {video_id: count for video_id, count in serve_count_rows}

    # Get the latest active (non-completed, non-failed) job per video
    active_job_rows = (
        db.query(VideoJob.video_id, VideoJob.job_type, VideoJob.status)
        .filter(
            VideoJob.video_id.in_(video_ids),
            VideoJob.status.in_(["queued", "processing"]),
        )
        .order_by(VideoJob.video_id, VideoJob.id.desc())
        .all()
    )
    # Keep only the most recent active job per video
    active_jobs: dict[int, dict] = {}
    for row in active_job_rows:
        if row.video_id not in active_jobs:
            active_jobs[row.video_id] = {
                "job_type": row.job_type,
                "status": row.status,
            }

    result = []
    for video in demo_videos:
        has_pose_analysis = video.id in completed_pose_video_ids
        serve_count = serve_counts.get(video.id, 0)
        active_job = active_jobs.get(video.id)
        job_status = None
        if active_job:
            job_status = (
                "transcoding" if active_job["job_type"] == "transcode" else "analyzing"
            )

        result.append(
            {
                "id": video.id,
                "filename": video.filename,
                "file_path": video.file_path,
                "is_active_demo": video.is_active_demo,
                "has_pose_analysis": has_pose_analysis,
                "serve_window_count": serve_count,
                "job_status": job_status,
                "created_at": video.created_at,
            }
        )

    return result


def validate_demo_eligibility(video: Video) -> None:
    """Validate that a video is eligible to be set as active demo.

    Args:
        video: Video model instance

    Raises:
        ValueError: If video is not eligible (not demo or wrong path prefix)
    """
    if not video.is_demo:
        raise ValueError(f"Video {video.id} is not a demo video")

    if "demo/" not in video.file_path:
        raise ValueError(
            f"Video {video.id} is not eligible to be active demo. "
            f"File path must include 'demo/'"
        )


def set_active_demo_video(db: Session, video_id: int) -> Video:
    """Set a demo video as the active demo.

    Args:
        db: Database session
        video_id: ID of the demo video to set as active

    Returns:
        Updated Video instance

    Raises:
        ValueError: If video not found, not demo, or not eligible
        RuntimeError: If storage operations fail
    """
    video = db.query(Video).filter(Video.id == video_id).first()
    if not video:
        raise ValueError(f"Video with ID {video_id} not found")

    validate_demo_eligibility(video)
    video_path = video.file_path
    content_type = video.content_type

    # End any open transaction before external storage I/O.
    db.rollback()

    # Copy to demo bucket if using Supabase and demo bucket is configured
    if settings.STORAGE_TYPE == "supabase" and settings.SUPABASE_DEMO_BUCKET:
        demo_path = video_path
        if not storage_service.demo_object_exists(demo_path):
            try:
                file_content = storage_service.download_private_file(video_path)
                storage_service.upload_demo_object(
                    demo_path, file_content, content_type
                )
            except Exception as e:
                raise RuntimeError(f"Failed to copy video to demo bucket: {e}") from e

    # Re-load and re-validate before mutating DB state.
    video = db.query(Video).filter(Video.id == video_id).first()
    if not video:
        raise ValueError(f"Video with ID {video_id} not found")
    validate_demo_eligibility(video)

    # Unset previous active demo
    old_active = db.query(Video).filter(Video.is_active_demo).first()
    if old_active and old_active.id != video_id:
        old_active.is_active_demo = False

    # Set new active demo
    video.is_active_demo = True
    db.commit()
    db.refresh(video)

    return video


def enqueue_demo_pose_analysis(
    db: Session, video_id: int, user_id: str, confidence_threshold: float
) -> VideoJob:
    """Enqueue pose analysis for a demo video.

    Args:
        db: Database session
        video_id: ID of the demo video
        user_id: ID of the user requesting analysis
        confidence_threshold: Confidence threshold for pose detection

    Returns:
        Created VideoJob instance

    Raises:
        ValueError: If video not found, not demo, or already analyzed
        RuntimeError: If job enqueue fails
    """
    video = video_service.get_video_by_id(db, video_id)
    if not video:
        raise ValueError(f"Video with ID {video_id} not found")

    if not video.is_demo:
        raise ValueError(f"Video {video_id} is not a demo video")

    # Check for existing completed pose analysis
    existing_detection = (
        db.query(PoseDetection.id)
        .filter(
            PoseDetection.video_id == video_id,
            PoseDetection.status == "completed",
        )
        .first()
    )
    if existing_detection:
        raise ValueError(f"Video {video_id} already has completed pose analysis")

    # Create VideoJob record
    video_job = VideoJob(
        video_id=video_id,
        user_id=user_id,
        job_type="pose_only",
        status="queued",
    )
    db.add(video_job)
    db.commit()
    db.refresh(video_job)

    try:
        # Enqueue pose analysis job
        job = enqueue_pose_analysis(
            video_id=video_id,
            video_path=video.file_path,
            confidence_threshold=confidence_threshold,
            video_job_id=str(video_job.id),
        )
        if not job:
            video_job.status = "failed"
            video_job.error = "Failed to enqueue job to Redis"
            db.commit()
            raise RuntimeError("Failed to enqueue job to Redis")

        video_job.rq_job_id = job.id
        db.commit()

        return video_job
    except RuntimeError:
        raise
    except Exception as e:
        logger.exception("Failed to enqueue pose analysis for demo video %s", video_id)
        video_job.status = "failed"
        video_job.error = f"Failed to enqueue job: {e}"
        db.commit()
        raise RuntimeError(f"Failed to start analysis: {e}") from e


def delete_demo_video(db: Session, video_id: int) -> tuple[str, int]:
    """Delete a demo video and all associated data.

    The active demo cannot be deleted — set another video as active first.
    Cleans up both the private storage bucket and the public demo bucket (if applicable).

    Args:
        db: Database session
        video_id: ID of the demo video to delete

    Returns:
        Tuple of (filename, video_id)

    Raises:
        ValueError: If video not found or is not a demo video
        PermissionError: If the video is the currently active demo
    """
    video = db.query(Video).filter(Video.id == video_id).first()
    if not video:
        raise ValueError(f"Video with ID {video_id} not found")
    if not video.is_demo:
        raise ValueError(f"Video {video_id} is not a demo video")
    if video.is_active_demo:
        raise PermissionError(
            "Cannot delete the active demo. Set another video as active first."
        )

    file_path = video.file_path

    # Best-effort: clean up the demo bucket copy if it exists there.
    # set_active_demo_video copies to the demo bucket, so a formerly-active video
    # may have a stale copy there even after being superseded.
    if settings.STORAGE_TYPE == "supabase" and settings.SUPABASE_DEMO_BUCKET:
        try:
            if storage_service.demo_object_exists(file_path):
                storage_service._supabase_client.storage.from_(
                    settings.SUPABASE_DEMO_BUCKET
                ).remove([file_path])
                logger.info("Deleted demo bucket copy: %s", file_path)
        except Exception:  # noqa: BLE001
            logger.warning(
                "Failed to delete demo bucket copy for video %s (%s) — continuing",
                video_id,
                file_path,
            )

    success, filename, video_id = video_service.delete_video_with_analyses(db, video_id)
    if not success:
        raise RuntimeError(
            f"Failed to delete video {video_id} from storage or database"
        )

    return filename, video_id
