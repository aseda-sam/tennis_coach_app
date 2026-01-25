"""
RQ task functions for video analysis.

These functions are executed by RQ workers and must be:
- Serializable (only use basic types as parameters)
- Self-contained (create their own database sessions)
- Idempotent (safe to retry)
- Error-handling (log and re-raise exceptions)
"""

import logging
from pathlib import Path
from typing import Any, Dict

from sqlalchemy.exc import SQLAlchemyError

from app.core.database import SessionLocal
from app.services import video_service
from app.services.storage_service import storage_service

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


def analyze_pose_detection_rq(
    video_id: int,
    video_path: str,
    confidence_threshold: float = 0.7,
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
            # Verify video exists
            video = video_service.get_video_by_id(db, video_id)
            if not video:
                raise ValueError(f"Video {video_id} not found")

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

            logger.info(
                f"RQ task: Pose detection completed for video {video_id}, "
                f"detection_id={pose_detection.id}"
            )

            # Post-process: analyze contacts for this video (synchronous, fast)
            try:
                from app.services.posture_analysis import (
                    analyze_all_contacts_for_video,
                )

                logger.info(
                    f"RQ task: Calculating contact metrics for video {video_id}"
                )
                contact_metrics_result = analyze_all_contacts_for_video(
                    db=db, video_id=video_id, force_reanalysis=False
                )
                logger.info(
                    f"RQ task: Contact metrics calculated for video {video_id}: "
                    f"{contact_metrics_result.get('analyzed', 0)} contacts analyzed"
                )
            except (
                ValueError,
                KeyError,
                AttributeError,
                RuntimeError,
                SQLAlchemyError,
            ) as e:
                # Log error but don't fail the pose detection task
                logger.warning(
                    f"RQ task: Failed to calculate contact metrics for video {video_id}: {e}",
                    exc_info=True,
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
        raise

    finally:
        # Clean up temp video file if created for cloud storage
        _cleanup_temp_file(temp_video_path)


def analyze_ball_detection_rq(
    video_id: int,
    video_path: str,
    confidence_threshold: float = 0.7,
) -> Dict[str, Any]:
    """
    RQ task for ball detection analysis.

    Args:
        video_id: Video ID from database
        video_path: Path to video file (can be cloud path)
        confidence_threshold: YOLO confidence threshold

    Returns:
        Analysis results dictionary

    Raises:
        ValueError: If video not found or analysis fails
        RuntimeError: If ball detection service fails
    """
    temp_video_path = None
    try:
        # Lazy imports inside function (avoids fork issues)
        from app.services.ball_detection import BallDetectionService

        logger.info(f"RQ task: Starting ball detection for video {video_id}")

        # Create database session
        with SessionLocal() as db:
            # Verify video exists
            video = video_service.get_video_by_id(db, video_id)
            if not video:
                raise ValueError(f"Video {video_id} not found")

            # Get local file path (handles cloud download)
            local_path, temp_video_path = _get_temp_video_path(video_path)

            # Run ball detection
            ball_service = BallDetectionService()
            ball_results = ball_service.analyze_video_file(
                video_path=Path(local_path),
                confidence_threshold=confidence_threshold,
                video_quality_level=None,
                max_frames=None,
            )

            # Check for errors
            if "error" in ball_results:
                raise RuntimeError(f"Ball detection failed: {ball_results['error']}")

            # Save results
            ball_detection = ball_service.save_detection_results(
                db=db, video_id=video_id, detection_results=ball_results
            )

            logger.info(
                f"RQ task: Ball detection completed for video {video_id}, "
                f"detection_id={ball_detection.id}"
            )

            return {
                "status": "completed",
                "processing_time": ball_results.get("processing_time_seconds", 0.0),
                "analysis_summary": {
                    "total_frames": ball_results.get("total_frames", 0),
                    "frames_with_balls": ball_results.get("frames_with_balls", 0),
                    "detection_rate": ball_results.get("detection_rate", 0.0),
                },
                "ball_detection_id": ball_detection.id,
                "analysis_type": "ball_only",
            }

    except Exception as e:
        logger.error(f"RQ task failed for video {video_id}: {e}", exc_info=True)
        raise

    finally:
        # Clean up temp video file if created for cloud storage
        _cleanup_temp_file(temp_video_path)


def analyze_contact_metrics_rq(
    video_id: int, force_reanalysis: bool = False
) -> Dict[str, Any]:
    """
    RQ task for contact metrics re-analysis (elbow angles, etc.).

    This task analyzes contact metrics using existing pose detection data.
    It does not re-run pose detection.

    Args:
        video_id: Video ID from database
        force_reanalysis: Whether to reanalyze contacts that already have metrics

    Returns:
        Analysis results dictionary

    Raises:
        ValueError: If video not found or pose data missing
        RuntimeError: If analysis fails
    """
    try:
        from app.services.posture_analysis import analyze_all_contacts_for_video

        logger.info(
            f"RQ task: Starting contact metrics analysis for video {video_id} "
            f"(force_reanalysis={force_reanalysis})"
        )

        # Create database session
        with SessionLocal() as db:
            # Verify video exists
            video = video_service.get_video_by_id(db, video_id)
            if not video:
                raise ValueError(f"Video {video_id} not found")

            # Verify pose detection exists
            from app.models.pose_detection import PoseDetection

            pose_detection = (
                db.query(PoseDetection)
                .filter(
                    PoseDetection.video_id == video_id,
                    PoseDetection.status == "completed",
                )
                .first()
            )

            if not pose_detection:
                raise ValueError(
                    f"No completed pose detection found for video {video_id}. "
                    "Please run pose detection first."
                )

            # Analyze all contacts
            results = analyze_all_contacts_for_video(
                db=db, video_id=video_id, force_reanalysis=force_reanalysis
            )

            logger.info(
                f"RQ task: Contact metrics analysis completed for video {video_id}: "
                f"{results.get('analyzed', 0)} contacts analyzed, "
                f"{results.get('failed', 0)} failed, "
                f"{results.get('skipped', 0)} skipped"
            )

            return {
                "status": "completed",
                "analysis_summary": {
                    "total_contacts": results.get("total_contacts", 0),
                    "analyzed": results.get("analyzed", 0),
                    "failed": results.get("failed", 0),
                    "skipped": results.get("skipped", 0),
                },
                "contact_results": results.get("contact_results", []),
                "analysis_type": "contact_metrics",
            }

    except Exception as e:
        logger.error(
            f"RQ task failed for contact metrics analysis on video {video_id}: {e}",
            exc_info=True,
        )
        raise


def analyze_serve_attempts_rq(video_id: int) -> Dict[str, Any]:
    """
    RQ task for batch analysis of manually-tagged serve attempts.

    Steps:
    1. Load serve_attempts for video (that haven't been analyzed yet)
    2. Run ServeAnalysisService.analyze_serve_attempts()
    3. Update serve_attempts with calculated metrics
    4. Return summary with serve count and avg elbow angle

    Args:
        video_id: Video ID from database

    Returns:
        Analysis results dictionary

    Raises:
        ValueError: If video not found or pose data missing
        RuntimeError: If analysis fails
    """
    try:
        # Lazy imports inside function (avoids fork issues)
        from app.models.serve_attempt import ServeAttempt
        from app.services.serve_analysis_service import ServeAnalysisService

        logger.info(f"RQ task: Starting serve attempts analysis for video {video_id}")

        # Create database session
        with SessionLocal() as db:
            # Verify video exists
            video = video_service.get_video_by_id(db, video_id)
            if not video:
                raise ValueError(f"Video {video_id} not found")

            # Load serve attempts for this video
            serve_attempts = (
                db.query(ServeAttempt).filter(ServeAttempt.video_id == video_id).all()
            )

            if not serve_attempts:
                logger.warning(f"No serve attempts found for video {video_id}")
                return {
                    "status": "completed",
                    "video_id": video_id,
                    "total_serves": 0,
                    "analyzed": 0,
                    "failed": 0,
                    "skipped": 0,
                    "avg_elbow_angle": None,
                    "message": "No serve attempts found for analysis",
                }

            # Run batch analysis
            analysis_service = ServeAnalysisService()
            results = analysis_service.analyze_serve_attempts(
                db=db, video_id=video_id, serve_attempts=serve_attempts
            )

            logger.info(
                f"RQ task: Serve attempts analysis completed for video {video_id}: "
                f"{results.get('analyzed', 0)} analyzed, "
                f"{results.get('failed', 0)} failed, "
                f"{results.get('skipped', 0)} skipped"
            )

            return {
                "status": "completed",
                "video_id": video_id,
                "total_serves": results.get("total_serves", 0),
                "analyzed": results.get("analyzed", 0),
                "failed": results.get("failed", 0),
                "skipped": results.get("skipped", 0),
                "avg_elbow_angle": results.get("avg_elbow_angle"),
                "recommendations": results.get("recommendations", []),
                "analysis_type": "serve_attempts",
            }

    except Exception as e:
        logger.error(
            f"RQ task failed for serve attempts analysis on video {video_id}: {e}",
            exc_info=True,
        )
        raise
