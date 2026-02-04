"""Service for demo video management."""

import logging
from typing import List

from sqlalchemy.orm import Session

from app.core.config import settings
from app.models.pose_detection import PoseDetection
from app.models.serve_attempt import ServeAttempt
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
        db.query(Video).filter(Video.is_demo).order_by(Video.id.desc()).all()
    )

    result = []
    for video in demo_videos:
        pose_detection = (
            db.query(PoseDetection.id)
            .filter(
                PoseDetection.video_id == video.id,
                PoseDetection.status == "completed",
            )
            .first()
        )
        has_pose_analysis = pose_detection is not None

        serve_count = (
            db.query(ServeAttempt).filter(ServeAttempt.video_id == video.id).count()
        )

        result.append(
            {
                "id": video.id,
                "filename": video.filename,
                "file_path": video.file_path,
                "is_active_demo": video.is_active_demo,
                "has_pose_analysis": has_pose_analysis,
                "serve_attempt_count": serve_count,
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

    if not video.file_path.startswith("demo/"):
        raise ValueError(
            f"Video {video.id} is not eligible to be active demo. "
            f"File path must start with 'demo/'"
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

    # Copy to demo bucket if using Supabase and demo bucket is configured
    if settings.STORAGE_TYPE == "supabase" and settings.SUPABASE_DEMO_BUCKET:
        demo_path = video.file_path
        if not storage_service.demo_object_exists(demo_path):
            try:
                file_content = storage_service.download_private_file(video.file_path)
                storage_service.upload_demo_object(
                    demo_path, file_content, video.content_type
                )
            except Exception as e:
                raise RuntimeError(f"Failed to copy video to demo bucket: {e}") from e

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
