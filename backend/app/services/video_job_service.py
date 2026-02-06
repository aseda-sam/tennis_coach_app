"""Service for video job operations."""

from typing import List, Optional
from uuid import UUID

from sqlalchemy.orm import Session

from app.models.video_job import VideoJob


def get_user_jobs(
    db: Session,
    user_id: str,
    status_filter: Optional[List[str]] = None,
    limit: int = 50,
) -> List[VideoJob]:
    """Get jobs for a user, optionally filtered by status.

    Args:
        db: Database session
        user_id: User ID to filter jobs by
        status_filter: Optional list of statuses to filter by
        limit: Maximum number of jobs to return

    Returns:
        List of VideoJob instances ordered by creation date (newest first)
    """
    query = db.query(VideoJob).filter(VideoJob.user_id == user_id)

    if status_filter:
        query = query.filter(VideoJob.status.in_(status_filter))

    return query.order_by(VideoJob.created_at.desc()).limit(limit).all()


def get_job_by_id(
    db: Session,
    job_id: UUID,
    user_id: Optional[str] = None,
    is_admin: bool = False,
) -> Optional[VideoJob]:
    """Get a job by ID with authorization check.

    Args:
        db: Database session
        job_id: Job UUID
        user_id: User ID for authorization check (required if not admin)
        is_admin: Whether the user is an admin (admins can see all jobs)

    Returns:
        VideoJob instance if found and authorized, None otherwise
    """
    query = db.query(VideoJob).filter(VideoJob.id == job_id)

    if not is_admin and user_id:
        query = query.filter(VideoJob.user_id == user_id)

    return query.first()


def create_video_job(
    db: Session,
    video_id: int,
    user_id: str,
    job_type: str,
    status: str = "queued",
) -> VideoJob:
    """Create a new VideoJob record.

    Args:
        db: Database session
        video_id: Video ID
        user_id: User ID
        job_type: Type of job (e.g., "pose_detection")
        status: Initial status (default: "queued")

    Returns:
        Created VideoJob instance
    """
    video_job = VideoJob(
        video_id=video_id,
        user_id=user_id,
        job_type=job_type,
        status=status,
    )
    db.add(video_job)
    db.commit()
    db.refresh(video_job)
    return video_job
