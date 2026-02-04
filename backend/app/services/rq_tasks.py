"""
RQ task functions for video analysis.

These functions are executed by RQ workers and must be:
- Serializable (only use basic types as parameters)
- Self-contained (create their own database sessions)
- Idempotent (safe to retry)
- Error-handling (log and re-raise exceptions)
"""

import logging
import subprocess
import tempfile
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, Optional

import cv2
from rq import Retry
from rq.job import Job
from sqlalchemy.exc import SQLAlchemyError

from app.core.config import settings
from app.core.database import SessionLocal
from app.core.redis_config import analysis_queue
from app.models.video_job import VideoJob
from app.services import video_service
from app.services.storage_service import storage_service
from app.utils.video_utils import get_video_rotation

logger = logging.getLogger(__name__)


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
            logger.debug(f"Cleaned up temp video file: {temp_path}")
        except OSError as e:
            logger.warning(f"Failed to delete temp video file {temp_path}: {e}")


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
    temp_video_path = None
    temp_output_path = None
    try:
        logger.info(f"RQ task: Starting transcoding for video {video_id}")

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
            temp_output_path = Path(
                tempfile.mkstemp(suffix=".mp4", dir=settings.PROCESSED_DIR)[1]
            )
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

            logger.info(f"Running ffmpeg: {' '.join(ffmpeg_cmd)}")
            result = subprocess.run(  # noqa: S603 - ffmpeg args from config and validated storage path
                ffmpeg_cmd,
                capture_output=True,
                text=True,
                check=False,
            )

            if result.returncode != 0:
                logger.error(f"ffmpeg failed: {result.stderr}")
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
                f"RQ task: Transcoding completed for video {video_id}, "
                f"size reduced from {original_file_size} to {new_file_size} bytes "
                f"({100 * (1 - new_file_size / original_file_size):.1f}% reduction)"
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
                        retry=Retry(max=2, interval=60),
                        job_timeout=settings.POSE_DETECTION_JOB_TIMEOUT_SECONDS,
                        result_ttl=3600,
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
        logger.error(f"RQ task failed for video {video_id}: {e}", exc_info=True)

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
                logger.debug(f"Cleaned up temp transcoded file: {temp_output_path}")
            except OSError as e:
                logger.warning(
                    f"Failed to delete temp transcoded file {temp_output_path}: {e}"
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
            retry=Retry(max=2, interval=60),
            job_timeout=settings.POSE_DETECTION_JOB_TIMEOUT_SECONDS,
            result_ttl=3600,  # Keep results for 1 hour
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
    temp_video_path = None
    try:
        # Lazy imports inside function (avoids fork issues)
        from app.services.pose_detection import PoseDetectionService

        logger.info(f"RQ task: Starting pose detection for video {video_id}")

        # Create database session
        with SessionLocal() as db:
            # Check video exists early - exit gracefully if deleted
            video = video_service.get_video_by_id(db, video_id)
            if not video:
                logger.info(
                    "Video %s deleted before job started, exiting gracefully", video_id
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
                        f"Invalid video_job_id {video_job_id}: {e}. Continuing without status update."
                    )

            # Get local file path (handles cloud download)
            local_path, temp_video_path = _get_temp_video_path(video_path)

            # Run pose detection
            pose_service = PoseDetectionService()
            pose_results = pose_service.analyze_video_file(
                video_path=Path(local_path),
                confidence_threshold=confidence_threshold,
                detection_threshold=0.5,
                max_frames=None,
            )

            # Check for errors
            if "error" in pose_results:
                raise RuntimeError(f"Pose detection failed: {pose_results['error']}")

            # Save results
            pose_detection = pose_service.save_detection_results(
                db=db, video_id=video_id, detection_results=pose_results
            )

            # Update VideoJob status to completed if video_job_id provided
            if video_job:
                video_job.status = "completed"
                video_job.finished_at = datetime.utcnow()
                db.commit()

            logger.info(
                f"RQ task: Pose detection completed for video {video_id}, "
                f"detection_id={pose_detection.id}"
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
        logger.error(f"RQ task failed for video {video_id}: {e}", exc_info=True)

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
                        video_job.error = str(e)[:500]  # Truncate error message
                        video_job.finished_at = datetime.utcnow()
                        db.commit()
            except (ValueError, TypeError, SQLAlchemyError) as e2:
                logger.warning(
                    f"Failed to update VideoJob status: {e2}. Original error: {e}"
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
    temp_video_path = None
    try:
        # Lazy imports
        from app.services.pose_detection import PoseDetectionService
        from app.services.serve_detection.proposal_service import generate_proposals

        logger.info(f"RQ task: Starting scout/refine pipeline for video {video_id}")

        # Create database session
        with SessionLocal() as db:
            # Check video exists early
            video = video_service.get_video_by_id(db, video_id)
            if not video:
                logger.info(
                    "Video %s deleted before job started, exiting gracefully", video_id
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
                    logger.warning(f"Invalid video_job_id {video_job_id}: {e}")

            # Get local file path
            local_path, temp_video_path = _get_temp_video_path(video_path)

            # Phase 1: Scout pass
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
                raise RuntimeError(f"Scout pass failed: {scout_results['error']}")

            # Save scout results
            scout_pose_detection = pose_service.save_detection_results(
                db=db, video_id=video_id, detection_results=scout_results
            )

            # Phase 2: Detect serve windows using scout data
            logger.info("Phase 2: Detecting serve windows from scout data")
            if video_job and hasattr(video_job, "stage"):
                video_job.stage = "detecting_serves"
                db.commit()

            # Generate proposals (uses scout pose data)
            proposals = generate_proposals(
                db=db, video_id=video_id, user_id=video.user_id, force=True
            )

            if not proposals:
                logger.info(
                    "No serve windows detected, completing with scout data only"
                )
                if video_job:
                    video_job.status = "completed"
                    video_job.finished_at = datetime.utcnow()
                    db.commit()
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

            logger.info(f"Found {len(windows)} serve windows, starting refine pass")

            # Phase 3: Refine pass (full model on windows only)
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
                    f"Refine pass failed: {refine_results['error']}, using scout data only"
                )
                refine_results = None
            else:
                # Add time_windows to results
                refine_results["time_windows"] = windows

                # Save refine results as new pose detection record
                refine_pose_detection = pose_service.save_detection_results(
                    db=db, video_id=video_id, detection_results=refine_results
                )

            # Update VideoJob status
            if video_job:
                video_job.status = "completed"
                if hasattr(video_job, "stage"):
                    video_job.stage = "complete"
                video_job.finished_at = datetime.utcnow()
                db.commit()

            logger.info(
                f"RQ task: Scout/refine pipeline completed for video {video_id}, "
                f"found {len(windows)} serve windows"
            )

            return {
                "status": "completed",
                "mode": "scout_refine",
                "serve_windows_found": len(windows),
                "scout_pose_detection_id": scout_pose_detection.id,
                "refine_pose_detection_id": refine_pose_detection.id
                if refine_results
                else None,
            }

    except Exception as e:
        logger.error(f"RQ task failed for video {video_id}: {e}", exc_info=True)

        # Update VideoJob status to failed
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
        _cleanup_temp_file(temp_video_path)
