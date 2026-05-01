"""Service for auto-enqueueing video analysis jobs on upload."""

import logging
import time

from rq import Retry
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.redis_config import analysis_queue
from app.models.video import Video
from app.models.video_job import VideoJob
from app.services.rq_tasks import (
    analyze_pose_detection_scout_refine_rq,
    transcode_video_rq,
)

logger = logging.getLogger(__name__)


def auto_enqueue_video_analysis(
    db: Session,
    video: Video,
    user_id: str,
) -> None:
    """Auto-enqueue transcoding and/or pose analysis for a video after upload.

    This function is called after a video is successfully uploaded. It creates
    VideoJob records and enqueues RQ jobs based on configuration.

    Args:
        db: Database session
        video: Video model instance that was just uploaded
        user_id: User ID who uploaded the video

    Note:
        This function intentionally catches all exceptions to ensure upload
        doesn't fail if enqueueing fails. Errors are logged but not raised.
    """
    if not settings.AUTO_ENQUEUE_ON_UPLOAD:
        logger.debug(
            "Auto-enqueue disabled (AUTO_ENQUEUE_ON_UPLOAD=False). "
            "Set AUTO_ENQUEUE_ON_UPLOAD=True in .env to enable."
        )
        return

    pose_job: VideoJob | None = None
    transcode_job: VideoJob | None = None

    try:
        # Create pose detection job record (will be started after transcode if needed)
        pose_job = VideoJob(
            video_id=video.id,
            user_id=user_id,
            job_type="pose_only",
            status="queued",
        )
        db.add(pose_job)
        db.commit()
        db.refresh(pose_job)

        # Always route through the transcode task when enabled.
        # The transcode task itself decides whether to actually re-encode
        # (based on file size AND codec compatibility) or skip and chain
        # straight to pose detection.  This ensures AV1 / VP9 videos are
        # always transcoded to H.264 even when they are small files.
        if settings.TRANSCODE_ENABLED:
            # Create transcode job record
            transcode_job = VideoJob(
                video_id=video.id,
                user_id=user_id,
                job_type="transcode",
                status="queued",
            )
            db.add(transcode_job)
            db.commit()
            db.refresh(transcode_job)

            # Enqueue transcode job (will chain to pose detection on completion)
            rq_job = analysis_queue.enqueue(
                transcode_video_rq,
                video_id=video.id,
                video_path=video.file_path,
                video_job_id=str(transcode_job.id),
                retry=Retry(max=2, interval=0),
                job_timeout=600,  # 10 minutes for transcoding
                result_ttl=3600,
                meta={"enqueued_at": time.time()},
            )
            if rq_job:
                transcode_job.rq_job_id = rq_job.id
                db.commit()
                logger.info(
                    "Auto-enqueued transcoding for video %d (is_demo=%s)",
                    video.id,
                    video.is_demo,
                )
            else:
                transcode_job.status = "failed"
                transcode_job.error = "Failed to enqueue transcode job to Redis"
                db.commit()
        else:
            # Transcoding disabled — go straight to scout/refine pipeline
            rq_job = analysis_queue.enqueue(
                analyze_pose_detection_scout_refine_rq,
                video_id=video.id,
                video_path=video.file_path,
                video_job_id=str(pose_job.id),
                confidence_threshold=0.7,
                retry=Retry(max=2, interval=0),
                job_timeout=settings.POSE_DETECTION_JOB_TIMEOUT_SECONDS,
                result_ttl=3600,
                meta={"enqueued_at": time.time()},
            )
            if not rq_job:
                pose_job.status = "failed"
                pose_job.error = "Failed to enqueue job to Redis"
                db.commit()
                logger.debug(
                    "Auto-enqueue failed for video %d (is_demo=%s)",
                    video.id,
                    video.is_demo,
                )
            else:
                pose_job.rq_job_id = rq_job.id
                db.commit()
                logger.info(
                    "Auto-enqueued pose analysis for video %d (is_demo=%s, transcode disabled)",
                    video.id,
                    video.is_demo,
                )
    except Exception:  # noqa: BLE001 - Intentionally catch all to ensure upload succeeds
        # Enqueue functions already log errors internally, just ensure upload doesn't fail
        if transcode_job is not None:
            transcode_job.status = "failed"
            transcode_job.error = "Failed to enqueue job to Redis"
        if pose_job is not None:
            pose_job.status = "failed"
            pose_job.error = "Failed to enqueue job to Redis"
        db.commit()
        logger.debug("Failed to enqueue jobs, but upload succeeded")
