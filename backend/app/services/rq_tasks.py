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

from app.core.database import SessionLocal
from app.models.ball_detection import BallDetection
from app.models.pose_detection import PoseDetection
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

    Replaces: BackgroundTaskService._run_pose_only_analysis()

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

    Replaces: BackgroundTaskService._run_ball_only_analysis()

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


def create_video_annotation_rq(
    video_id: int,
    video_path: str,
    confidence_threshold: float = 0.7,
) -> Dict[str, Any]:
    """
    RQ task for video annotation (requires existing ball or pose detections).

    Replaces: BackgroundTaskService._run_video_annotation_analysis()

    Args:
        video_id: Video ID from database
        video_path: Path to video file (can be cloud path)
        confidence_threshold: Not used for annotation, kept for API compatibility

    Returns:
        Analysis results dictionary

    Raises:
        ValueError: If no detections found or video not found
        RuntimeError: If annotation service fails
    """
    temp_video_path = None
    try:
        # Lazy imports inside function (avoids fork issues)
        from app.services.video_annotation.annotation_service import (
            VideoAnnotationService,
        )

        logger.info(f"RQ task: Starting video annotation for video {video_id}")

        # Create database session
        with SessionLocal() as db:
            # Verify video exists
            video = video_service.get_video_by_id(db, video_id)
            if not video:
                raise ValueError(f"Video {video_id} not found")

            # Get local file path (handles cloud download)
            # Note: local_path not used here, but download ensures file is available locally
            _, temp_video_path = _get_temp_video_path(video_path)

            # Get the most recent ball detection for this video
            ball_detection = (
                db.query(BallDetection)
                .filter(BallDetection.video_id == video_id)
                .order_by(BallDetection.created_at.desc())
                .first()
            )

            # Get the most recent pose detection for this video
            pose_detection = (
                db.query(PoseDetection)
                .filter(PoseDetection.video_id == video_id)
                .order_by(PoseDetection.created_at.desc())
                .first()
            )

            if not ball_detection and not pose_detection:
                raise ValueError(
                    "No ball or pose detections found. "
                    "Please run ball_only or pose_only analysis first."
                )

            # Run video annotation
            annotation_service = VideoAnnotationService()
            annotation_result = annotation_service.create_pose_annotation(
                db=db,
                video_id=video_id,
                pose_detection_id=pose_detection.id if pose_detection else None,
            )

            logger.info(
                f"RQ task: Video annotation completed for video {video_id}, "
                f"annotation_id={annotation_result.id}"
            )

            return {
                "status": "completed",
                "success": True,
                "ball_detection_id": ball_detection.id if ball_detection else None,
                "pose_detection_id": pose_detection.id if pose_detection else None,
                "video_annotation_id": annotation_result.id,
                "annotated_video_path": annotation_result.annotated_video_path,
                "analysis_type": "video_annotation_only",
            }

    except Exception as e:
        logger.error(f"RQ task failed for video {video_id}: {e}", exc_info=True)
        raise

    finally:
        # Clean up temp video file if created for cloud storage
        _cleanup_temp_file(temp_video_path)


def analyze_pose_with_annotation_rq(
    video_id: int,
    video_path: str,
    confidence_threshold: float = 0.7,
) -> Dict[str, Any]:
    """
    RQ task for pose detection followed by video annotation.

    Replaces: BackgroundTaskService._run_pose_with_annotation_analysis()

    Args:
        video_id: Video ID from database
        video_path: Path to video file (can be cloud path)
        confidence_threshold: Detection confidence threshold

    Returns:
        Analysis results dictionary

    Raises:
        ValueError: If video not found or analysis fails
        RuntimeError: If pose detection or annotation service fails
    """
    temp_video_path = None
    try:
        # Lazy imports inside function (avoids fork issues)
        from app.services.pose_detection import PoseDetectionService
        from app.services.video_annotation.annotation_service import (
            VideoAnnotationService,
        )

        logger.info(
            f"RQ task: Starting pose detection with annotation for video {video_id}"
        )

        # Create database session
        with SessionLocal() as db:
            # Verify video exists
            video = video_service.get_video_by_id(db, video_id)
            if not video:
                raise ValueError(f"Video {video_id} not found")

            # Get local file path (handles cloud download)
            local_path, temp_video_path = _get_temp_video_path(video_path)

            # Step 1: Run pose detection
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

            # Save pose detection results
            pose_detection = pose_service.save_detection_results(
                db=db, video_id=video_id, detection_results=pose_results
            )

            logger.info(
                f"RQ task: Pose detection completed for video {video_id}, "
                f"starting annotation"
            )

            # Step 2: Run video annotation
            annotation_service = VideoAnnotationService()
            annotation_result = annotation_service.create_pose_annotation(
                db=db,
                video_id=video_id,
                pose_detection_id=pose_detection.id,
            )

            logger.info(
                f"RQ task: Pose detection with annotation completed for video {video_id}, "
                f"pose_detection_id={pose_detection.id}, "
                f"annotation_id={annotation_result.id}"
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
                "video_annotation_id": annotation_result.id,
                "annotated_video_path": annotation_result.annotated_video_path,
                "analysis_type": "pose_with_annotation",
            }

    except Exception as e:
        logger.error(f"RQ task failed for video {video_id}: {e}", exc_info=True)
        raise

    finally:
        # Clean up temp video file if created for cloud storage
        _cleanup_temp_file(temp_video_path)
