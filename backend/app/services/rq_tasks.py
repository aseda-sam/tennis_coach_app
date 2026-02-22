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
from contextlib import suppress
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
from app.models.ball_detection import BallDetection
from app.models.player import Player
from app.models.pose_detection import PoseDetection
from app.models.serve_window import ServeWindow
from app.models.video import Video
from app.models.video_job import VideoJob
from app.services import video_service
from app.services.storage_service import storage_service
from app.utils.logging_context import get_log_extra
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
            logger.debug("Cleaned up temp video file: %s", temp_path)
        except OSError as e:
            logger.warning("Failed to delete temp video file %s: %s", temp_path, e)


def run_ball_detection_rq(
    video_id: int,
    user_id: str,
    video_job_id: Optional[str] = None,
) -> Dict[str, Any]:
    """
    RQ task for standalone ball detection on existing serve windows.

    Runs YOLO + ByteTrack ball detection, auto-detects contact timestamps,
    and recomputes biomechanics to pick up toss metrics.

    Args:
        video_id: Video ID from database
        user_id: User ID who triggered the job
        video_job_id: Optional VideoJob ID for status tracking

    Returns:
        Dictionary with ball detection results
    """
    start_time = time.time()
    temp_video_path = None

    try:
        from app.services.ball_detection import YoloBallDetectionService
        from app.services.ball_detection.contact_detector import (
            detect_contact_timestamp,
        )
        from app.services.biomechanics.serve_biomechanics_service import (
            compute_biomechanics_batch,
        )

        logger.info(
            "RQ task: Starting ball detection for video %s",
            video_id,
            extra=get_log_extra(video_id=video_id, job_id=video_job_id),
        )

        video_job_uuid = None
        if video_job_id:
            try:
                import uuid

                video_job_uuid = uuid.UUID(video_job_id)
            except (ValueError, TypeError) as e:
                logger.warning("Invalid video_job_id %s: %s", video_job_id, e)

        # Validate video and load serve windows
        with SessionLocal() as db:
            video = video_service.get_video_by_id(db, video_id)
            if not video:
                logger.info(
                    "Video %s deleted before ball detection started, exiting",
                    video_id,
                )
                return {"status": "cancelled", "reason": "video_deleted"}

            video_path = video.file_path

            accepted_windows = (
                db.query(ServeWindow)
                .filter(
                    ServeWindow.video_id == video_id,
                    ServeWindow.status == "accepted",
                )
                .all()
            )
            if not accepted_windows:
                logger.info("No accepted serve windows for video %s", video_id)
                return {"status": "skipped", "reason": "no_serve_windows"}

            windows = [
                {
                    "start_ms": sw.start_timestamp * 1000.0,
                    "end_ms": sw.end_timestamp * 1000.0,
                }
                for sw in accepted_windows
            ]

            if video_job_uuid:
                video_job = (
                    db.query(VideoJob).filter(VideoJob.id == video_job_uuid).first()
                )
                if video_job:
                    video_job.status = "processing"
                    video_job.started_at = datetime.utcnow()
                    if hasattr(video_job, "stage"):
                        video_job.stage = "ball_detection"
                    db.commit()

        # Get local video file
        local_path, temp_video_path = _get_temp_video_path(video_path)

        # Run ball detection
        ball_service = YoloBallDetectionService()
        ball_results = ball_service.analyze_serve_windows(
            video_path=Path(local_path),
            windows=windows,
            padding_ms=300,
        )

        if "error" in ball_results:
            raise RuntimeError(f"Ball detection failed: {ball_results['error']}")

        # Store results
        with SessionLocal() as db:
            # Delete previous BallDetection for idempotency
            db.query(BallDetection).filter(BallDetection.video_id == video_id).delete()
            db.flush()

            ball_record = BallDetection(
                video_id=video_id,
                total_frames=ball_results["total_frames"],
                frames_with_ball=ball_results["frames_with_ball"],
                detection_rate=ball_results["detection_rate"],
                ball_data=json.dumps(ball_results["ball_detections"]),
                processing_time_seconds=ball_results["processing_time_seconds"],
                frame_processing_rate=ball_results.get("frame_processing_rate"),
                status="completed",
                time_windows=json.dumps(windows),
                completed_at=datetime.utcnow(),
            )
            db.add(ball_record)
            db.commit()
            db.refresh(ball_record)

            logger.info(
                "Ball detection stored for video %s: %s/%s frames",
                video_id,
                ball_results["frames_with_ball"],
                ball_results["total_frames"],
            )

            # Auto-detect contact timestamps (reuse pattern from rq_tasks.py:621-677)
            try:
                video_obj = db.query(Video).filter(Video.id == video_id).first()
                pose_detection = (
                    db.query(PoseDetection)
                    .filter(
                        PoseDetection.video_id == video_id,
                        PoseDetection.status == "completed",
                    )
                    .order_by(PoseDetection.created_at.desc())
                    .first()
                )
                if video_obj and pose_detection:
                    windows_missing_contact = (
                        db.query(ServeWindow)
                        .filter(
                            ServeWindow.video_id == video_id,
                            ServeWindow.contact_timestamp.is_(None),
                        )
                        .all()
                    )
                    for sw in windows_missing_contact:
                        player = (
                            db.query(Player).filter(Player.id == sw.player_id).first()
                            if sw.player_id
                            else None
                        )
                        dominant_hand = player.dominant_hand if player else "right"
                        contact_ts = detect_contact_timestamp(
                            ball_detection=ball_record,
                            pose_detection=pose_detection,
                            serve_window=sw,
                            video=video_obj,
                            dominant_hand=dominant_hand,
                        )
                        if contact_ts is not None:
                            sw.contact_timestamp = contact_ts
                            logger.info(
                                "Auto-detected contact for serve window %s at %.2fs",
                                sw.id,
                                contact_ts,
                            )
                    db.commit()
            except Exception as contact_err:  # noqa: BLE001
                logger.warning(
                    "Contact detection skipped for video %s: %s",
                    video_id,
                    contact_err,
                    exc_info=True,
                )

            # Recompute biomechanics to pick up toss metrics
            try:
                reports = compute_biomechanics_batch(
                    db=db,
                    video_id=video_id,
                    user_id=user_id,
                )
                logger.info(
                    "Recomputed biomechanics for %d serves in video %s",
                    len(reports),
                    video_id,
                )
            except Exception as bio_err:  # noqa: BLE001
                logger.warning(
                    "Biomechanics recompute failed for video %s: %s",
                    video_id,
                    bio_err,
                    exc_info=True,
                )

            # Update VideoJob status
            if video_job_uuid:
                video_job = (
                    db.query(VideoJob).filter(VideoJob.id == video_job_uuid).first()
                )
                if video_job:
                    video_job.status = "completed"
                    if hasattr(video_job, "stage"):
                        video_job.stage = "complete"
                    video_job.finished_at = datetime.utcnow()
                    db.commit()

        duration = time.time() - start_time
        logger.info(
            "RQ task: Ball detection completed for video %s in %.1fs",
            video_id,
            duration,
            extra=get_log_extra(video_id=video_id, job_id=video_job_id),
        )

        return {
            "status": "completed",
            "video_id": video_id,
            "total_frames": ball_results["total_frames"],
            "frames_with_ball": ball_results["frames_with_ball"],
            "detection_rate": ball_results["detection_rate"],
            "processing_time_seconds": duration,
        }

    except Exception as e:
        logger.error(
            "RQ ball detection failed for video %s: %s",
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
        logger.info("RQ task: Starting transcoding for video %s", video_id)

        video_job_uuid = None
        original_file_size = 0
        if video_job_id:
            try:
                import uuid

                video_job_uuid = uuid.UUID(video_job_id)
            except (ValueError, TypeError) as e:
                logger.warning(
                    "Invalid video_job_id %s: %s. Continuing without status update.",
                    video_job_id,
                    e,
                )

        # DB Stage 1: validate input and mark job as processing
        with SessionLocal() as db:
            video = video_service.get_video_by_id(db, video_id)
            if not video:
                logger.info(
                    "Video %s deleted before job started, exiting gracefully", video_id
                )
                return {"status": "cancelled", "reason": "video_deleted"}

            original_file_size = video.file_size
            if video_job_uuid:
                video_job = (
                    db.query(VideoJob).filter(VideoJob.id == video_job_uuid).first()
                )
                if video_job:
                    video_job.status = "processing"
                    video_job.started_at = datetime.utcnow()
                    if hasattr(video_job, "stage"):
                        video_job.stage = "transcoding"
                    db.commit()

        # Non-DB Stage: download/transcode/upload
        local_path, temp_video_path = _get_temp_video_path(video_path)

        fd, temp_output_name = tempfile.mkstemp(
            suffix=".mp4", dir=settings.PROCESSED_DIR
        )
        with suppress(OSError):
            os.close(fd)
        temp_output_path = Path(temp_output_name)
        temp_output_path.parent.mkdir(parents=True, exist_ok=True)

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
            "-an",
            "-movflags",
            "+faststart",
            "-y",
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

        with open(temp_output_path, "rb") as f:
            transcoded_content = f.read()

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

        rotation = get_video_rotation(temp_output_path)
        if rotation in (90, 270, -90, -270):
            new_width, new_height = raw_height, raw_width
        else:
            new_width, new_height = raw_width, raw_height

        new_duration = new_frame_count / new_fps if new_fps > 0 else None
        new_file_size = len(transcoded_content)
        new_storage_path = storage_service.replace_file(
            old_file_path=video_path,
            new_file_content=transcoded_content,
            content_type="video/mp4",
        )

        # DB Stage 2: persist results and chain follow-up jobs
        with SessionLocal() as db:
            video = video_service.get_video_by_id(db, video_id)
            if not video:
                raise ValueError(
                    f"Video with ID {video_id} was deleted during transcoding"
                )

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
                try:
                    pose_rq_job = analysis_queue.enqueue(
                        analyze_pose_detection_scout_refine_rq,
                        video_id=video_id,
                        video_path=new_storage_path,
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
                            "Chained scout/refine job %s after transcoding",
                            pose_rq_job.id,
                        )
                except Exception as e:  # noqa: BLE001 - best-effort chaining
                    logger.warning(
                        "Failed to chain scout/refine after transcoding: %s", e
                    )

            if video_job_uuid:
                video_job = (
                    db.query(VideoJob).filter(VideoJob.id == video_job_uuid).first()
                )
                if video_job:
                    video_job.status = "completed"
                    video_job.finished_at = datetime.utcnow()
                    db.commit()

        logger.info(
            "RQ task: Transcoding completed for video %s, "
            "size reduced from %s to %s bytes (%.1f%% reduction)",
            video_id,
            original_file_size,
            new_file_size,
            100 * (1 - new_file_size / original_file_size),
        )
        return {
            "status": "completed",
            "original_file_size": original_file_size,
            "new_file_size": new_file_size,
            "size_reduction_percent": 100 * (1 - new_file_size / original_file_size),
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
            "Enqueueing pose detection job for video %s, confidence_threshold=%s",
            video_id,
            confidence_threshold,
        )

        job = analysis_queue.enqueue(
            analyze_pose_detection_scout_refine_rq,
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
            "Successfully enqueued pose detection job %s for video %s to queue '%s'",
            job.id,
            video_id,
            analysis_queue.name,
        )

        return job

    except Exception as e:  # noqa: BLE001 - Intentionally catch all to allow upload to succeed
        # Log error but don't raise - allows upload to succeed even if Redis is down
        logger.warning(
            "Failed to enqueue pose detection job for video %s: %s. "
            "Upload succeeded, but analysis will need to be triggered manually.",
            video_id,
            e,
        )
        return None


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

        video_job_uuid = None
        if video_job_id:
            try:
                import uuid

                video_job_uuid = uuid.UUID(video_job_id)
            except (ValueError, TypeError) as e:
                logger.warning("Invalid video_job_id %s: %s", video_job_id, e)

        with SessionLocal() as db:
            video = video_service.get_video_by_id(db, video_id)
            if not video:
                logger.info(
                    "Video %s deleted before job started, exiting gracefully",
                    video_id,
                )
                return {"status": "cancelled", "reason": "video_deleted"}
            video_user_id = video.user_id
            if video_job_uuid:
                video_job = (
                    db.query(VideoJob).filter(VideoJob.id == video_job_uuid).first()
                )
                if video_job:
                    video_job.status = "processing"
                    video_job.started_at = datetime.utcnow()
                    if hasattr(video_job, "stage"):
                        video_job.stage = "scout"
                    db.commit()

        local_path, temp_video_path = _get_temp_video_path(video_path)

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

        with SessionLocal() as db:
            scout_pose_detection = pose_service.save_detection_results(
                db=db, video_id=video_id, detection_results=scout_results
            )
            scout_pose_detection_id = scout_pose_detection.id

            logger.info("Phase 2: Detecting serve windows from scout data")
            if video_job_uuid:
                video_job = (
                    db.query(VideoJob).filter(VideoJob.id == video_job_uuid).first()
                )
                if video_job and hasattr(video_job, "stage"):
                    video_job.stage = "detecting_serves"
                    db.commit()

            proposals = generate_proposals(
                db=db,
                video_id=video_id,
                user_id=video_user_id,
                force=True,
            )
            if not proposals:
                logger.info(
                    "No serve windows detected, completing with scout data only"
                )
                if video_job_uuid:
                    video_job = (
                        db.query(VideoJob).filter(VideoJob.id == video_job_uuid).first()
                    )
                    if video_job:
                        video_job.status = "completed"
                        video_job.finished_at = datetime.utcnow()
                        db.commit()
                duration = time.time() - start_time
                return {
                    "status": "completed",
                    "mode": "scout_only",
                    "serve_windows_found": 0,
                    "pose_detection_id": scout_pose_detection_id,
                }

            windows = [
                {
                    "start_ms": proposal.start_timestamp * 1000.0,
                    "end_ms": proposal.end_timestamp * 1000.0,
                }
                for proposal in proposals
            ]

        logger.info("Found %s serve windows, starting refine pass", len(windows))
        frames_with_poses = scout_results.get("frames_with_poses") or 0
        merged_data = scout_results.get("pose_detections", [])

        with SessionLocal() as db:
            if video_job_uuid:
                video_job = (
                    db.query(VideoJob).filter(VideoJob.id == video_job_uuid).first()
                )
                if video_job and hasattr(video_job, "stage"):
                    video_job.stage = "refining"
                    video_job.serve_windows_found = len(windows)
                    db.commit()

        refine_results = pose_service.analyze_serve_windows(
            video_path=Path(local_path),
            windows=windows,
            padding_ms=500.0,
            confidence_threshold=confidence_threshold,
            detection_threshold=0.5,
        )

        if "error" in refine_results:
            logger.warning(
                "Refine pass failed: %s, using scout data only",
                refine_results["error"],
            )
        else:
            merged_data = pose_service.merge_pose_data(
                merged_data, refine_results["pose_detections"]
            )
            frames_with_poses = sum(
                1 for f in merged_data if f and f.get("keypoints") is not None
            )

        with SessionLocal() as db:
            scout_pose_detection_db = (
                db.query(PoseDetection)
                .filter(PoseDetection.id == scout_pose_detection_id)
                .first()
            )
            if scout_pose_detection_db:
                scout_pose_detection_db.pose_data = json.dumps(merged_data)
                scout_pose_detection_db.time_windows = json.dumps(windows)
                scout_pose_detection_db.frames_with_poses = frames_with_poses
                scout_pose_detection_db.detection_rate = (
                    frames_with_poses / len(merged_data) if merged_data else 0.0
                )
                db.commit()

            logger.info(
                "Merged refine data into scout record for video %s, "
                "%s frames now have pose data",
                video_id,
                frames_with_poses,
            )

            # Ball detection on serve windows (optional: skip if import/runtime fails)
            try:
                from app.services.ball_detection import YoloBallDetectionService

                ball_service = YoloBallDetectionService()
                ball_results = ball_service.analyze_serve_windows(
                    video_path=Path(local_path),
                    windows=windows,
                    padding_ms=300,
                )
                if "error" not in ball_results:
                    ball_record = BallDetection(
                        video_id=video_id,
                        total_frames=ball_results["total_frames"],
                        frames_with_ball=ball_results["frames_with_ball"],
                        detection_rate=ball_results["detection_rate"],
                        ball_data=json.dumps(ball_results["ball_detections"]),
                        processing_time_seconds=ball_results["processing_time_seconds"],
                        frame_processing_rate=ball_results.get("frame_processing_rate"),
                        status="completed",
                        time_windows=json.dumps(windows),
                        completed_at=datetime.utcnow(),
                    )
                    db.add(ball_record)
                    db.commit()
                    logger.info(
                        "Ball detection completed for video %s: %s/%s frames with ball",
                        video_id,
                        ball_results["frames_with_ball"],
                        ball_results["total_frames"],
                    )
                else:
                    logger.warning(
                        "Ball detection failed for video %s: %s",
                        video_id,
                        ball_results.get("error"),
                    )
            except Exception as ball_err:  # noqa: BLE001
                logger.warning(
                    "Ball detection skipped for video %s: %s",
                    video_id,
                    ball_err,
                    exc_info=True,
                )

            # Auto-detect contact timestamps from ball + wrist data (only when contact not set)
            try:
                from app.services.ball_detection.contact_detector import (
                    detect_contact_timestamp,
                )

                ball_record = (
                    db.query(BallDetection)
                    .filter(
                        BallDetection.video_id == video_id,
                        BallDetection.status == "completed",
                    )
                    .order_by(BallDetection.created_at.desc())
                    .first()
                )
                if ball_record:
                    video_obj = db.query(Video).filter(Video.id == video_id).first()
                    if video_obj:
                        windows_missing_contact = (
                            db.query(ServeWindow)
                            .filter(
                                ServeWindow.video_id == video_id,
                                ServeWindow.contact_timestamp.is_(None),
                            )
                            .all()
                        )
                        for sw in windows_missing_contact:
                            player = (
                                db.query(Player)
                                .filter(Player.id == sw.player_id)
                                .first()
                                if sw.player_id
                                else None
                            )
                            dominant_hand = player.dominant_hand if player else "right"
                            contact_ts = detect_contact_timestamp(
                                ball_detection=ball_record,
                                pose_detection=scout_pose_detection_db,
                                serve_window=sw,
                                video=video_obj,
                                dominant_hand=dominant_hand,
                            )
                            if contact_ts is not None:
                                sw.contact_timestamp = contact_ts
                                logger.info(
                                    "Auto-detected contact for serve window %s at %.2fs",
                                    sw.id,
                                    contact_ts,
                                )
                        db.commit()
            except Exception as auto_contact_err:  # noqa: BLE001
                logger.warning(
                    "Auto-contact detection skipped for video %s: %s",
                    video_id,
                    auto_contact_err,
                    exc_info=True,
                )

            # Auto-accept proposals and compute biomechanics
            auto_accepted = []
            biomechanics_computed = 0
            if settings.AUTO_ACCEPT_SERVE_PROPOSALS:
                try:
                    from app.services.serve_detection.proposal_service import (
                        auto_accept_proposals,
                    )

                    if video_job_uuid:
                        video_job = (
                            db.query(VideoJob)
                            .filter(VideoJob.id == video_job_uuid)
                            .first()
                        )
                        if video_job and hasattr(video_job, "stage"):
                            video_job.stage = "auto_accepting"
                            db.commit()

                    auto_accepted = auto_accept_proposals(
                        db=db,
                        video_id=video_id,
                        user_id=video_user_id,
                    )
                    logger.info(
                        "Auto-accepted %d proposals for video %s",
                        len(auto_accepted),
                        video_id,
                    )
                except Exception as accept_err:  # noqa: BLE001
                    logger.warning(
                        "Auto-accept failed for video %s: %s",
                        video_id,
                        accept_err,
                        exc_info=True,
                    )

            if auto_accepted and settings.AUTO_COMPUTE_BIOMECHANICS:
                try:
                    from app.services.biomechanics.serve_biomechanics_service import (
                        compute_biomechanics_batch,
                    )

                    if video_job_uuid:
                        video_job = (
                            db.query(VideoJob)
                            .filter(VideoJob.id == video_job_uuid)
                            .first()
                        )
                        if video_job and hasattr(video_job, "stage"):
                            video_job.stage = "computing_biomechanics"
                            db.commit()

                    reports = compute_biomechanics_batch(
                        db=db,
                        video_id=video_id,
                        user_id=video_user_id,
                    )
                    biomechanics_computed = len(reports)
                    logger.info(
                        "Computed biomechanics for %d serves in video %s",
                        biomechanics_computed,
                        video_id,
                    )
                except Exception as bio_err:  # noqa: BLE001
                    logger.warning(
                        "Auto-biomechanics failed for video %s: %s",
                        video_id,
                        bio_err,
                        exc_info=True,
                    )

            if video_job_uuid:
                video_job = (
                    db.query(VideoJob).filter(VideoJob.id == video_job_uuid).first()
                )
                if video_job:
                    video_job.status = "completed"
                    if hasattr(video_job, "stage"):
                        video_job.stage = "complete"
                    video_job.finished_at = datetime.utcnow()
                    db.commit()

        duration = time.time() - start_time

        logger.info(
            "RQ task: Scout/refine pipeline completed for video %s, "
            "found %s serve windows, auto-accepted %s, biomechanics %s (%.1fs)",
            video_id,
            len(windows),
            len(auto_accepted),
            biomechanics_computed,
            duration,
            extra=get_log_extra(video_id=video_id, job_id=video_job_id),
        )

        return {
            "status": "completed",
            "mode": "scout_refine",
            "serve_windows_found": len(windows),
            "auto_accepted": len(auto_accepted),
            "biomechanics_computed": biomechanics_computed,
            "scout_pose_detection_id": scout_pose_detection_id,
        }

    except Exception as e:
        duration = time.time() - start_time

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
