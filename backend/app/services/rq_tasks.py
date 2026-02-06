"""
RQ task functions for video analysis.

These functions are executed by RQ workers and must be:
- Serializable (only use basic types as parameters)
- Self-contained (create their own database sessions)
- Idempotent (safe to retry)
- Error-handling (log and re-raise exceptions)
"""

import json
import logging
import os
import subprocess
import tempfile
import time
from contextlib import contextmanager, suppress
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, Iterator, Optional

import cv2
from rq import Retry, get_current_job
from rq.job import Job
from sqlalchemy.exc import SQLAlchemyError

from app.core.config import settings
from app.core.database import SessionLocal
from app.core.redis_config import analysis_queue
from app.models.video_job import VideoJob
from app.services import video_service
from app.services.storage_service import storage_service
from app.utils.logging_context import get_log_extra
from app.utils.metrics import (
    record_job_failed,
    record_job_started,
    record_job_succeeded,
    record_queue_wait,
)
from app.utils.video_utils import get_video_rotation

logger = logging.getLogger(__name__)


@contextmanager
def _rq_job_span(
    span_name: str, video_id: int, video_job_id: Optional[str] = None
) -> Iterator[Any]:
    """Create one trace span for an RQ job so it shows up in Grafana (job_id, video_id, rq_job_id)."""
    span_context = None
    span = None
    try:
        from opentelemetry import trace

        tracer = trace.get_tracer(__name__, "0.1.0")
        span_context = tracer.start_as_current_span(span_name)
        span = span_context.__enter__()
        span.set_attribute("video_id", video_id)
        if video_job_id:
            span.set_attribute("job_id", str(video_job_id))
        try:
            job = get_current_job()
            if job is not None:
                span.set_attribute("rq_job_id", str(job.id))
                # Add queue wait time as span attribute (visible in trace detail)
                if job.meta and "enqueued_at" in job.meta:
                    queue_wait = time.time() - job.meta["enqueued_at"]
                    span.set_attribute("queue_wait_seconds", round(queue_wait, 2))
        except Exception as e:  # noqa: BLE001 - get_current_job can fail outside RQ
            logger.debug("Could not get RQ job for span: %s", e)
    except Exception as e:  # noqa: BLE001
        logger.warning("OTel span creation failed: %s", e)
        span = None

    # Single yield point - always executed
    try:
        yield span
    finally:
        # Cleanup: ensure span is closed and flushed (don't mask exceptions from with-body)
        if span_context is not None:
            try:
                span_context.__exit__(None, None, None)
                # Force flush so the span is exported immediately after job completes
                provider = trace.get_tracer_provider()
                if hasattr(provider, "force_flush"):
                    provider.force_flush(timeout_millis=5000)
            except Exception as e:  # noqa: BLE001 - Don't mask exceptions from with-body
                logger.debug("OTel span cleanup failed: %s", e)


@contextmanager
def _stage_span(
    span_name: str, **attributes: str | int | float | bool | None
) -> Iterator[Any]:
    """Create a child span for a pipeline stage (download, scout, refine, db_write, etc.)."""
    span_context = None
    span = None
    try:
        from opentelemetry import trace

        tracer = trace.get_tracer(__name__, "0.1.0")
        span_context = tracer.start_as_current_span(span_name)
        span = span_context.__enter__()
        for key, value in attributes.items():
            if value is not None:
                span.set_attribute(
                    key,
                    str(value) if not isinstance(value, (int, float, bool)) else value,
                )
    except Exception:  # noqa: BLE001 - OTel may not be available
        span = None

    # Single yield point - always executed
    try:
        yield span
    finally:
        # Cleanup: ensure span is closed (don't mask exceptions from with-body)
        if span_context is not None:
            with suppress(Exception):  # Don't mask exceptions from with-body
                span_context.__exit__(None, None, None)


def _record_queue_wait(job_type: str, video_id: int) -> None:
    """Read enqueued_at from RQ job meta and record queue wait time."""
    try:
        job = get_current_job()
        if job and job.meta and "enqueued_at" in job.meta:
            wait = time.time() - job.meta["enqueued_at"]
            record_queue_wait(job_type, wait, video_id=video_id)
            logger.info(
                "Queue wait for %s video %s: %.1fs",
                job_type,
                video_id,
                wait,
                extra=get_log_extra(video_id=video_id),
            )
    except Exception:  # noqa: BLE001, S110 - best-effort, don't break the job
        pass


def _get_temp_video_path(video_path: str) -> tuple[Path, Path | None]:
    """
    Get local file path and determine if it's a temp file that needs cleanup.

    Args:
        video_path: Path to video file (can be cloud path)

    Returns:
        Tuple of (local_path, temp_path) where temp_path is None if not a temp file
    """
    local_path = storage_service.get_local_file_path(video_path)
    temp_path = local_path if storage_service.storage_type == "supabase" else None
    return local_path, temp_path


def _cleanup_temp_file(temp_path: Path | None) -> None:
    """
    Clean up temporary video file if it exists.

    Args:
        temp_path: Path to temp file, or None if no cleanup needed
    """
    if temp_path and temp_path.exists():
        try:
            temp_path.unlink()
            logger.debug("Cleaned up temp video file: %s", temp_path)
        except OSError as e:
            logger.warning("Failed to delete temp video file %s: %s", temp_path, e)


def transcode_video_rq(
    video_id: int,
    video_path: str,
    video_job_id: Optional[str] = None,
) -> Dict[str, Any]:
    """
    RQ task for transcoding video to 720p/30fps H.264.

    Args:
        video_id: Video ID from database
        video_path: Path to video file (can be cloud path)
        video_job_id: Optional VideoJob ID for status tracking

    Returns:
        Dictionary with transcoding results

    Raises:
        ValueError: If video not found or transcoding fails
        RuntimeError: If ffmpeg fails
    """
    _record_queue_wait("transcode", video_id)
    temp_video_path = None
    temp_output_path = None
    try:
        logger.info("RQ task: Starting transcoding for video %s", video_id)

        # Create database session
        with SessionLocal() as db:
            # Check video exists early - exit gracefully if deleted
            video = video_service.get_video_by_id(db, video_id)
            if not video:
                logger.info(
                    "Video %s deleted before job started, exiting gracefully", video_id
                )
                return {"status": "cancelled", "reason": "video_deleted"}

            # Skip transcoding if file is already small enough
            if video.file_size < settings.TRANSCODE_THRESHOLD_BYTES:
                logger.info(
                    f"Video {video_id} file size ({video.file_size} bytes) "
                    f"below threshold ({settings.TRANSCODE_THRESHOLD_BYTES} bytes), skipping transcoding"
                )
                return {
                    "status": "skipped",
                    "reason": "file_too_small",
                    "file_size": video.file_size,
                }

            # Update VideoJob status to processing if video_job_id provided
            video_job = None
            if video_job_id:
                try:
                    import uuid

                    video_job = (
                        db.query(VideoJob)
                        .filter(VideoJob.id == uuid.UUID(video_job_id))
                        .first()
                    )
                    if video_job:
                        video_job.status = "processing"
                        video_job.started_at = datetime.utcnow()
                        if hasattr(video_job, "stage"):
                            video_job.stage = "transcoding"
                        db.commit()
                except (ValueError, TypeError, SQLAlchemyError) as e:
                    logger.warning(
                        f"Invalid video_job_id {video_job_id}: {e}. Continuing without status update."
                    )

            # Get local file path (handles cloud download)
            local_path, temp_video_path = _get_temp_video_path(video_path)

            # Create temp output file
            fd, temp_output_name = tempfile.mkstemp(
                suffix=".mp4", dir=settings.PROCESSED_DIR
            )
            # Close the file descriptor immediately - we only need the filename
            # Use suppress to handle edge cases (e.g., invalid FD in tests)
            with suppress(OSError):
                os.close(
                    fd
                )  # FD may already be closed or invalid - not critical since we only need the filename
            temp_output_path = Path(temp_output_name)
            temp_output_path.parent.mkdir(parents=True, exist_ok=True)

            # Run ffmpeg transcoding
            # Scale to 720p height (preserve aspect ratio), 30fps, H.264 CRF 23, remove audio, fast-start
            ffmpeg_cmd = [
                "ffmpeg",
                "-i",
                str(local_path),
                "-vf",
                f"scale=-2:{settings.TRANSCODE_RESOLUTION}",
                "-r",
                str(settings.TRANSCODE_FPS),
                "-c:v",
                "libx264",
                "-crf",
                str(settings.TRANSCODE_CRF),
                "-an",  # Remove audio
                "-movflags",
                "+faststart",  # Enable streaming playback
                "-y",  # Overwrite output file
                str(temp_output_path),
            ]

            logger.info("Running ffmpeg: %s", " ".join(ffmpeg_cmd))
            result = subprocess.run(  # noqa: S603 - ffmpeg args from config and validated storage path
                ffmpeg_cmd,
                capture_output=True,
                text=True,
                check=False,
            )

            if result.returncode != 0:
                logger.error("ffmpeg failed: %s", result.stderr)
                raise RuntimeError(f"ffmpeg transcoding failed: {result.stderr}")

            # Read transcoded file
            with open(temp_output_path, "rb") as f:
                transcoded_content = f.read()

            # Extract metadata from transcoded video
            cap = cv2.VideoCapture(str(temp_output_path))
            if not cap.isOpened():
                raise RuntimeError(
                    "Could not open transcoded video for metadata extraction"
                )

            new_fps = cap.get(cv2.CAP_PROP_FPS)
            new_frame_count = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
            raw_width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
            raw_height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
            cap.release()

            # Get rotation metadata (may affect dimensions)
            rotation = get_video_rotation(temp_output_path)
            if rotation in (90, 270, -90, -270):
                new_width, new_height = raw_height, raw_width
            else:
                new_width, new_height = raw_width, raw_height

            new_duration = new_frame_count / new_fps if new_fps > 0 else None
            new_file_size = len(transcoded_content)

            # Replace original file with transcoded version
            original_file_size = video.file_size
            new_storage_path = storage_service.replace_file(
                old_file_path=video_path,
                new_file_content=transcoded_content,
                content_type="video/mp4",
            )

            # Update video record
            video.file_path = new_storage_path
            video.file_size = new_file_size
            video.width = new_width
            video.height = new_height
            video.fps = new_fps
            video.frame_count = new_frame_count
            if new_duration:
                video.duration = new_duration
            if hasattr(video, "is_transcoded"):
                video.is_transcoded = True
            if hasattr(video, "original_file_size"):
                video.original_file_size = original_file_size

            db.commit()
            db.refresh(video)

            logger.info(
                "RQ task: Transcoding completed for video %s, "
                "size reduced from %s to %s bytes (%.1f%% reduction)",
                video_id,
                original_file_size,
                new_file_size,
                100 * (1 - new_file_size / original_file_size),
            )

            # Chain to scout/refine pipeline if this was part of auto-enqueue flow
            # Check if there's a pose detection job waiting
            pose_job = (
                db.query(VideoJob)
                .filter(
                    VideoJob.video_id == video_id,
                    VideoJob.job_type == "pose_only",
                    VideoJob.status == "queued",
                )
                .first()
            )

            if pose_job:
                # Enqueue scout/refine pipeline with updated video path
                try:
                    pose_rq_job = analysis_queue.enqueue(
                        analyze_pose_detection_scout_refine_rq,
                        video_id=video_id,
                        video_path=new_storage_path,  # Use transcoded path
                        video_job_id=str(pose_job.id),
                        confidence_threshold=0.7,
                        retry=Retry(max=2, interval=0),
                        job_timeout=settings.POSE_DETECTION_JOB_TIMEOUT_SECONDS,
                        result_ttl=3600,
                        meta={"enqueued_at": time.time()},
                    )
                    if pose_rq_job:
                        pose_job.rq_job_id = pose_rq_job.id
                        db.commit()
                        logger.info(
                            f"Chained scout/refine job {pose_rq_job.id} after transcoding"
                        )
                except Exception as e:  # noqa: BLE001 - per python-code-standards: Exception with comment why; transcode must still succeed
                    logger.warning(
                        "Failed to chain scout/refine after transcoding: %s", e
                    )

            # Update transcode VideoJob status to completed
            if video_job:
                video_job.status = "completed"
                video_job.finished_at = datetime.utcnow()
                db.commit()

            return {
                "status": "completed",
                "original_file_size": original_file_size,
                "new_file_size": new_file_size,
                "size_reduction_percent": 100
                * (1 - new_file_size / original_file_size),
                "new_width": new_width,
                "new_height": new_height,
                "new_fps": new_fps,
            }

    except Exception as e:
        logger.error("RQ task failed for video %s: %s", video_id, e, exc_info=True)

        # Update VideoJob status to failed if video_job_id provided
        if video_job_id:
            try:
                import uuid

                with SessionLocal() as db:
                    video_job = (
                        db.query(VideoJob)
                        .filter(VideoJob.id == uuid.UUID(video_job_id))
                        .first()
                    )
                    if video_job:
                        video_job.status = "failed"
                        video_job.error = str(e)[:500]
                        video_job.finished_at = datetime.utcnow()
                        db.commit()
            except (ValueError, TypeError, SQLAlchemyError) as e2:
                logger.warning(
                    f"Failed to update VideoJob status: {e2}. Original error: {e}"
                )

        raise

    finally:
        # Clean up temp files
        _cleanup_temp_file(temp_video_path)
        if temp_output_path and temp_output_path.exists():
            try:
                temp_output_path.unlink()
                logger.debug("Cleaned up temp transcoded file: %s", temp_output_path)
            except OSError as e:
                logger.warning(
                    "Failed to delete temp transcoded file %s: %s",
                    temp_output_path,
                    e,
                )


def enqueue_pose_analysis(
    video_id: int,
    video_path: str,
    confidence_threshold: float = 0.7,
    video_job_id: Optional[str] = None,
) -> Optional[Job]:
    """
    Enqueue a pose detection analysis job.

    This is a shared helper function used by both the manual analysis endpoint
    and the automatic enqueue on upload. It wraps the RQ enqueue logic with
    consistent retry/timeout settings.

    Args:
        video_id: Video ID from database
        video_path: Path to video file (can be cloud path)
        confidence_threshold: Detection confidence threshold (default 0.7)

    Returns:
        RQ Job object if enqueued successfully, None if enqueue failed
        (failures are logged but not raised to allow upload to succeed)

    Note:
        This function swallows Redis errors to allow uploads to succeed
        even if Redis is unavailable. The manual analysis endpoint should
        still raise errors for user feedback.
    """
    try:
        logger.info(
            f"Enqueueing pose detection job for video {video_id}, "
            f"confidence_threshold={confidence_threshold}"
        )

        job = analysis_queue.enqueue(
            analyze_pose_detection_rq,
            video_id=video_id,
            video_path=video_path,
            confidence_threshold=confidence_threshold,
            video_job_id=video_job_id,  # Pass VideoJob ID for status updates
            retry=Retry(max=2, interval=0),
            job_timeout=settings.POSE_DETECTION_JOB_TIMEOUT_SECONDS,
            result_ttl=3600,  # Keep results for 1 hour
            meta={"enqueued_at": time.time()},
        )

        logger.info(
            f"Successfully enqueued pose detection job {job.id} "
            f"for video {video_id} to queue '{analysis_queue.name}'"
        )

        return job

    except Exception as e:  # noqa: BLE001 - Intentionally catch all to allow upload to succeed
        # Log error but don't raise - allows upload to succeed even if Redis is down
        logger.warning(
            f"Failed to enqueue pose detection job for video {video_id}: {e}. "
            "Upload succeeded, but analysis will need to be triggered manually."
        )
        return None


def analyze_pose_detection_rq(
    video_id: int,
    video_path: str,
    confidence_threshold: float = 0.7,
    video_job_id: Optional[str] = None,
) -> Dict[str, Any]:
    """
    RQ task for pose detection analysis.

    Args:
        video_id: Video ID from database
        video_path: Path to video file (can be cloud path)
        confidence_threshold: Detection confidence threshold

    Returns:
        Analysis results dictionary

    Raises:
        ValueError: If video not found or analysis fails
        RuntimeError: If pose detection service fails
    """
    start_time = time.time()
    _record_queue_wait("pose_detection", video_id)
    record_job_started("pose_detection", video_id=video_id)

    with _rq_job_span(
        "rq.pose_detection", video_id=video_id, video_job_id=video_job_id
    ):
        temp_video_path = None
        try:
            # Lazy imports inside function (avoids fork issues)
            from app.services.pose_detection import PoseDetectionService

            logger.info(
                "RQ task: Starting pose detection for video %s",
                video_id,
                extra=get_log_extra(video_id=video_id, job_id=video_job_id),
            )

            # Create database session
            with SessionLocal() as db:
                # Check video exists early - exit gracefully if deleted
                video = video_service.get_video_by_id(db, video_id)
                if not video:
                    logger.info(
                        "Video %s deleted before job started, exiting gracefully",
                        video_id,
                    )
                    return {"status": "cancelled", "reason": "video_deleted"}

                # Update VideoJob status to processing if video_job_id provided
                video_job = None
                if video_job_id:
                    try:
                        import uuid

                        video_job = (
                            db.query(VideoJob)
                            .filter(VideoJob.id == uuid.UUID(video_job_id))
                            .first()
                        )
                        if video_job:
                            video_job.status = "processing"
                            video_job.started_at = datetime.utcnow()
                            db.commit()
                    except (ValueError, TypeError, SQLAlchemyError) as e:
                        logger.warning(
                            "Invalid video_job_id %s: %s. Continuing without status update.",
                            video_job_id,
                            e,
                        )

                # Stage: Download video (if cloud storage)
                with _stage_span("download", video_id=video_id):
                    local_path, temp_video_path = _get_temp_video_path(video_path)

                # Stage: Pose detection
                with _stage_span("pose_detection", video_id=video_id):
                    pose_service = PoseDetectionService()
                    pose_results = pose_service.analyze_video_file(
                        video_path=Path(local_path),
                        confidence_threshold=confidence_threshold,
                        detection_threshold=0.5,
                        max_frames=None,
                    )

                    # Check for errors
                    if "error" in pose_results:
                        raise RuntimeError(
                            f"Pose detection failed: {pose_results['error']}"
                        )

                # Stage: DB write
                with _stage_span("db_write", video_id=video_id, job_id=video_job_id):
                    pose_detection = pose_service.save_detection_results(
                        db=db, video_id=video_id, detection_results=pose_results
                    )

                # Update VideoJob status to completed if video_job_id provided
                if video_job:
                    video_job.status = "completed"
                    video_job.finished_at = datetime.utcnow()
                    db.commit()

                duration = time.time() - start_time
                record_job_succeeded("pose_detection", duration, video_id=video_id)

                logger.info(
                    "RQ task: Pose detection completed for video %s, detection_id=%s",
                    video_id,
                    pose_detection.id,
                    extra=get_log_extra(video_id=video_id, job_id=video_job_id),
                )

                return {
                    "status": "completed",
                    "processing_time": pose_results.get("processing_time_seconds", 0.0),
                    "analysis_summary": {
                        "total_frames": pose_results.get("total_frames", 0),
                        "frames_with_poses": pose_results.get("frames_with_poses", 0),
                        "detection_rate": pose_results.get("detection_rate", 0.0),
                    },
                    "pose_detection_id": pose_detection.id,
                    "analysis_type": "pose_only",
                }

        except Exception as e:
            duration = time.time() - start_time
            record_job_failed("pose_detection", duration, video_id=video_id)

            logger.error(
                "RQ task failed for video %s: %s",
                video_id,
                e,
                exc_info=True,
                extra=get_log_extra(video_id=video_id, job_id=video_job_id),
            )

            # Update VideoJob status to failed if video_job_id provided
            if video_job_id:
                try:
                    import uuid

                    with SessionLocal() as db:
                        video_job = (
                            db.query(VideoJob)
                            .filter(VideoJob.id == uuid.UUID(video_job_id))
                            .first()
                        )
                        if video_job:
                            video_job.status = "failed"
                            video_job.error = str(e)[:500]
                            video_job.finished_at = datetime.utcnow()
                            db.commit()
                except (ValueError, TypeError, SQLAlchemyError) as e2:
                    logger.warning(
                        "Failed to update VideoJob status: %s. Original: %s",
                        e2,
                        e,
                    )

            raise

        finally:
            # Clean up temp video file if created for cloud storage
            _cleanup_temp_file(temp_video_path)


def analyze_pose_detection_scout_refine_rq(
    video_id: int,
    video_path: str,
    video_job_id: Optional[str] = None,
    confidence_threshold: float = 0.7,
) -> Dict[str, Any]:
    """
    RQ task for two-pass pose detection (scout/refine pipeline).

    Args:
        video_id: Video ID from database
        video_path: Path to video file (can be cloud path)
        video_job_id: Optional VideoJob ID for status tracking
        confidence_threshold: Detection confidence threshold

    Returns:
        Analysis results dictionary
    """
    start_time = time.time()
    _record_queue_wait("scout_refine", video_id)
    record_job_started("scout_refine", video_id=video_id)

    with _rq_job_span("rq.scout_refine", video_id=video_id, video_job_id=video_job_id):
        temp_video_path = None
        try:
            # Lazy imports
            from app.services.pose_detection import PoseDetectionService
            from app.services.serve_detection.proposal_service import (
                generate_proposals,
            )

            logger.info(
                "RQ task: Starting scout/refine pipeline for video %s",
                video_id,
                extra=get_log_extra(video_id=video_id, job_id=video_job_id),
            )

            # Create database session
            with SessionLocal() as db:
                # Check video exists early
                video = video_service.get_video_by_id(db, video_id)
                if not video:
                    logger.info(
                        "Video %s deleted before job started, exiting gracefully",
                        video_id,
                    )
                    return {"status": "cancelled", "reason": "video_deleted"}

                # Update VideoJob status
                video_job = None
                if video_job_id:
                    try:
                        import uuid

                        video_job = (
                            db.query(VideoJob)
                            .filter(VideoJob.id == uuid.UUID(video_job_id))
                            .first()
                        )
                        if video_job:
                            video_job.status = "processing"
                            video_job.started_at = datetime.utcnow()
                            if hasattr(video_job, "stage"):
                                video_job.stage = "scout"
                            db.commit()
                    except (ValueError, TypeError, SQLAlchemyError) as e:
                        logger.warning(
                            "Invalid video_job_id %s: %s",
                            video_job_id,
                            e,
                        )

                # Stage: Download video (if cloud storage)
                with _stage_span("download", video_id=video_id):
                    local_path, temp_video_path = _get_temp_video_path(video_path)

                # Stage: Scout pass
                with _stage_span("scout", video_id=video_id, job_id=video_job_id):
                    logger.info("Phase 1: Running scout pass (lite model, frame skip)")
                    pose_service = PoseDetectionService()
                    scout_results = pose_service.analyze_video_file(
                        video_path=Path(local_path),
                        confidence_threshold=confidence_threshold,
                        detection_threshold=0.5,
                        max_frames=None,
                        mode="scout",
                    )

                    if "error" in scout_results:
                        raise RuntimeError(
                            f"Scout pass failed: {scout_results['error']}"
                        )

                    # Save scout results
                    scout_pose_detection = pose_service.save_detection_results(
                        db=db, video_id=video_id, detection_results=scout_results
                    )

                # Stage: Detect serve windows
                with _stage_span(
                    "detect_serves", video_id=video_id, job_id=video_job_id
                ):
                    logger.info("Phase 2: Detecting serve windows from scout data")
                    if video_job and hasattr(video_job, "stage"):
                        video_job.stage = "detecting_serves"
                        db.commit()

                    # Generate proposals (uses scout pose data)
                    proposals = generate_proposals(
                        db=db,
                        video_id=video_id,
                        user_id=video.user_id,
                        force=True,
                    )

                    if not proposals:
                        logger.info(
                            "No serve windows detected, completing with scout data only"
                        )
                        if video_job:
                            video_job.status = "completed"
                            video_job.finished_at = datetime.utcnow()
                            db.commit()
                        duration = time.time() - start_time
                        record_job_succeeded(
                            "scout_refine", duration, video_id=video_id
                        )
                        return {
                            "status": "completed",
                            "mode": "scout_only",
                            "serve_windows_found": 0,
                            "pose_detection_id": scout_pose_detection.id,
                        }

                    # Convert proposals to windows format (milliseconds)
                    windows = []
                    for proposal in proposals:
                        windows.append(
                            {
                                "start_ms": proposal.start_timestamp * 1000.0,
                                "end_ms": proposal.end_timestamp * 1000.0,
                            }
                        )

                    logger.info(
                        "Found %s serve windows, starting refine pass", len(windows)
                    )

                # Stage: Refine pass
                # Initialize frames_with_poses from scout data (fallback if refine fails)
                frames_with_poses = scout_pose_detection.frames_with_poses or 0

                with _stage_span(
                    "refine",
                    video_id=video_id,
                    job_id=video_job_id,
                    windows_count=len(windows),
                ):
                    if video_job and hasattr(video_job, "stage"):
                        video_job.stage = "refining"
                        video_job.serve_windows_found = len(windows)
                        db.commit()

                    refine_results = pose_service.analyze_serve_windows(
                        video_path=Path(local_path),
                        windows=windows,
                        padding_ms=500.0,  # 0.5s padding
                        confidence_threshold=confidence_threshold,
                        detection_threshold=0.5,
                    )

                    if "error" in refine_results:
                        logger.warning(
                            "Refine pass failed: %s, using scout data only",
                            refine_results["error"],
                        )
                    else:
                        # Merge refine data into scout record (no separate record)
                        scout_pose_data = json.loads(scout_pose_detection.pose_data)
                        refine_pose_data = refine_results["pose_detections"]

                        merged_data = pose_service.merge_pose_data(
                            scout_pose_data, refine_pose_data
                        )

                        scout_pose_detection.pose_data = json.dumps(merged_data)
                        scout_pose_detection.time_windows = json.dumps(windows)

                        frames_with_poses = sum(
                            1
                            for f in merged_data
                            if f and f.get("keypoints") is not None
                        )
                        scout_pose_detection.frames_with_poses = frames_with_poses
                        scout_pose_detection.detection_rate = (
                            frames_with_poses / len(merged_data) if merged_data else 0.0
                        )
                        db.commit()

                # Stage: Final DB write
                with _stage_span("db_write", video_id=video_id, job_id=video_job_id):
                    logger.info(
                        "Merged refine data into scout record for video %s, "
                        "%s frames now have pose data",
                        video_id,
                        frames_with_poses,
                    )

                # Update VideoJob status
                if video_job:
                    video_job.status = "completed"
                    if hasattr(video_job, "stage"):
                        video_job.stage = "complete"
                    video_job.finished_at = datetime.utcnow()
                    db.commit()

                duration = time.time() - start_time
                record_job_succeeded("scout_refine", duration, video_id=video_id)

                logger.info(
                    "RQ task: Scout/refine pipeline completed for video %s, "
                    "found %s serve windows",
                    video_id,
                    len(windows),
                    extra=get_log_extra(video_id=video_id, job_id=video_job_id),
                )

                return {
                    "status": "completed",
                    "mode": "scout_refine",
                    "serve_windows_found": len(windows),
                    "scout_pose_detection_id": scout_pose_detection.id,
                }

        except Exception as e:
            duration = time.time() - start_time
            record_job_failed("scout_refine", duration, video_id=video_id)

            logger.error(
                "RQ task failed for video %s: %s",
                video_id,
                e,
                exc_info=True,
                extra=get_log_extra(video_id=video_id, job_id=video_job_id),
            )

            if video_job_id:
                try:
                    import uuid

                    with SessionLocal() as db:
                        video_job = (
                            db.query(VideoJob)
                            .filter(VideoJob.id == uuid.UUID(video_job_id))
                            .first()
                        )
                        if video_job:
                            video_job.status = "failed"
                            video_job.error = str(e)[:500]
                            video_job.finished_at = datetime.utcnow()
                            db.commit()
                except (ValueError, TypeError, SQLAlchemyError) as e2:
                    logger.warning(
                        "Failed to update VideoJob status: %s. Original: %s",
                        e2,
                        e,
                    )

            raise

        finally:
            _cleanup_temp_file(temp_video_path)
