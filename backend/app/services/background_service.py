"""
Background task service for video analysis.
"""

import logging
import threading
from concurrent.futures import ThreadPoolExecutor
from contextlib import contextmanager
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, Optional

from sqlalchemy.orm import Session

from app.core.database import SessionLocal
from app.services.analysis_service import (
    analyze_video,
    create_analysis_record,
    update_analysis_status,
)
from app.services.ball_detection import BallDetectionService
from app.services.pose_detection import PoseDetectionService
from app.services.video_service import get_video_by_id
from app.utils.progress_utils import set_task_storage, update_task_progress

logger = logging.getLogger(__name__)

# Global task storage (in production, use Redis or database)
_active_tasks: Dict[int, Dict[str, Any]] = {}
_task_counter = 0
_task_lock = threading.Lock()

# Initialize progress utility
set_task_storage(_active_tasks, _task_lock)


@contextmanager
def get_background_db_session() -> Session:
    """Get a database session for background tasks with proper cleanup."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


class BackgroundTaskService:
    """Service for managing background video analysis tasks."""

    def __init__(self, max_workers: int = 2) -> None:
        self.max_workers = max_workers
        self.executor = ThreadPoolExecutor(max_workers=max_workers)
        self._task_counter = 0
        logger.info(f"BackgroundTaskService initialized with {max_workers} workers")

    def start_analysis_task(
        self,
        video_id: int,
        analysis_type: str,
        confidence_threshold: float = 0.7,
        include_pose_detection: bool = False,
    ) -> int:
        """
        Start a background analysis task.

        Args:
            video_id: Video ID to analyze
            analysis_type: Type of analysis (ball_tracking, pose_detection,
                comprehensive)
            confidence_threshold: YOLO confidence threshold
            include_pose_detection: Whether to include pose detection

        Returns:
            Task ID for tracking
        """
        global _task_counter

        with _task_lock:
            _task_counter += 1
            task_id = _task_counter

        # Store task info with proper locking
        with _task_lock:
            _active_tasks[task_id] = {
                "task_id": task_id,
                "video_id": video_id,
                "analysis_type": analysis_type,
                "confidence_threshold": confidence_threshold,
                "include_pose_detection": include_pose_detection,
                "status": "queued",
                "progress": 0,
                "error": None,
                "result": None,
                "started_at": datetime.now(),
                "completed_at": None,
                "future": None,
            }

        # Submit task to thread pool
        future = self.executor.submit(
            self._run_analysis_task,
            task_id,
            video_id,
            analysis_type,
            confidence_threshold,
            include_pose_detection,
        )

        # Store future for potential cancellation (keep status as "queued"
        # until processing starts)
        with _task_lock:
            _active_tasks[task_id]["future"] = future

        logger.info(f"Started background analysis task {task_id} for video {video_id}")
        return task_id

    def _run_analysis_task(
        self,
        task_id: int,
        video_id: int,
        analysis_type: str,
        confidence_threshold: float,
        include_pose_detection: bool,
    ) -> None:
        """Run the actual analysis task in a background thread."""
        try:
            # Update task status to processing (now actually processing)
            with _task_lock:
                if task_id in _active_tasks:
                    _active_tasks[task_id]["status"] = "processing"
                    _active_tasks[task_id]["progress"] = 5
                    _active_tasks[task_id]["current_stage"] = "initializing"
                    _active_tasks[task_id]["stage_progress"] = 100
                    _active_tasks[task_id]["stage_message"] = (
                        "Setting up analysis environment"
                    )

            # Use proper database session management
            with get_background_db_session() as db:
                # Get video info
                video = get_video_by_id(db, video_id)
                if not video:
                    raise ValueError(f"Video {video_id} not found")

                logger.info(
                    f"Task {task_id}: Starting analysis for video {video.filename}"
                )

                # Get video file path
                video_path = Path(video.file_path)
                if not video_path.exists():
                    raise ValueError(f"Video file not found: {video.file_path}")

                # Check if analysis record already exists for this video
                from app.services.analysis_service import get_analysis_by_video_id

                existing_analysis = get_analysis_by_video_id(db, video_id)

                if not existing_analysis:
                    # Create initial analysis record with processing status
                    from app.services.analysis_service import create_analysis_record

                    create_analysis_record(
                        db=db,
                        video_id=video_id,
                        video_filename=video.filename,
                        analysis_type=analysis_type,
                        analysis_results={},  # Empty for now
                        processing_time=0.0,
                        model_used="yolov8n+mediapipe"
                        if include_pose_detection
                        else "yolov8n",
                        confidence_threshold=confidence_threshold,
                        status="processing",
                    )

                # Update progress - frame extraction
                with _task_lock:
                    if task_id in _active_tasks:
                        _active_tasks[task_id]["progress"] = 15
                        _active_tasks[task_id]["current_stage"] = "frame_extraction"
                        _active_tasks[task_id]["stage_progress"] = 100
                        _active_tasks[task_id]["stage_message"] = (
                            "Extracting video frames for analysis"
                        )

                # Run analysis using new modular services based on analysis_type
                logger.info(
                    f"Task {task_id}: Starting analysis with type={analysis_type}, "
                    f"include_pose_detection={include_pose_detection}"
                )

                # Route to appropriate modular service based on analysis_type
                if analysis_type == "pose_only":
                    result = self._run_pose_only_analysis(
                        db=db,
                        video_id=video_id,
                        video_path=str(video_path),
                        confidence_threshold=confidence_threshold,
                        task_id=task_id,
                    )
                elif analysis_type == "ball_only":
                    result = self._run_ball_only_analysis(
                        db=db,
                        video_id=video_id,
                        video_path=str(video_path),
                        confidence_threshold=confidence_threshold,
                        task_id=task_id,
                    )
                elif analysis_type == "comprehensive":
                    result = self._run_comprehensive_analysis(
                        db=db,
                        video_id=video_id,
                        video_path=str(video_path),
                        confidence_threshold=confidence_threshold,
                        include_pose_detection=include_pose_detection,
                        task_id=task_id,
                    )
                else:
                    # Fall back to legacy system for other types
                    logger.warning(
                        f"Task {task_id}: Using legacy analyze_video for analysis_type={analysis_type}"
                    )
                    result = analyze_video(
                        db=db,
                        video_id=video_id,
                        analysis_type=analysis_type,
                        confidence_threshold=confidence_threshold,
                        include_pose_detection=include_pose_detection,
                        task_id=task_id,
                    )
                logger.info(
                    f"Task {task_id}: analyze_video completed with result: "
                    f"{type(result)}"
                )
                if isinstance(result, dict) and "error" in result:
                    logger.error(
                        f"Task {task_id}: Analysis failed with error: {result['error']}"
                    )
                elif isinstance(result, dict) and "contact_timestamps" in result:
                    contact_count = len(result.get("contact_timestamps", []))
                    logger.info(
                        f"Task {task_id}: Analysis completed with {contact_count} "
                        f"contacts detected"
                    )
                else:
                    logger.info(f"Task {task_id}: Analysis completed successfully")

                # Update progress - finalizing
                with _task_lock:
                    if task_id in _active_tasks:
                        _active_tasks[task_id]["progress"] = 95
                        _active_tasks[task_id]["current_stage"] = "finalizing"
                        _active_tasks[task_id]["stage_progress"] = 100
                        _active_tasks[task_id]["stage_message"] = (
                            "Completing analysis and saving results"
                        )

                # Check for errors
                if isinstance(result, dict) and "error" in result:
                    raise RuntimeError(result["error"])

                # Update task status
                with _task_lock:
                    if task_id in _active_tasks:
                        _active_tasks[task_id]["status"] = "completed"
                        _active_tasks[task_id]["progress"] = 100
                        _active_tasks[task_id]["result"] = result
                        _active_tasks[task_id]["completed_at"] = datetime.now()

                logger.info(f"Task {task_id}: Analysis completed successfully")

        except (OSError, ValueError, RuntimeError) as e:
            logger.error(f"Task {task_id}: Analysis failed: {e}")

            # Update task status with error
            with _task_lock:
                if task_id in _active_tasks:
                    _active_tasks[task_id]["status"] = "failed"
                    _active_tasks[task_id]["error"] = str(e)
                    _active_tasks[task_id]["completed_at"] = datetime.now()

            # Update database status with proper session management
            try:
                with get_background_db_session() as db:
                    update_analysis_status(db, video_id, "failed", str(e))
            except (OSError, ValueError, RuntimeError) as db_error:
                logger.error(f"Failed to update database status: {db_error}")

    def get_task_status(self, task_id: int) -> Optional[Dict[str, Any]]:
        """Get the status of a background task."""
        with _task_lock:
            task = _active_tasks.get(task_id)
            if task:
                # Remove future object from response (not serializable)
                response = task.copy()
                response.pop("future", None)
                # Add task_id to response
                response["task_id"] = task_id
                return response
        return None

    def get_all_tasks(self) -> Dict[int, Dict[str, Any]]:
        """Get all active tasks."""
        tasks = {}
        with _task_lock:
            for task_id, task in _active_tasks.items():
                # Remove future object from response
                response = task.copy()
                response.pop("future", None)
                # Add task_id to response
                response["task_id"] = task_id
                tasks[task_id] = response
        return tasks

    def cancel_task(self, task_id: int) -> bool:
        """Cancel a background task."""
        with _task_lock:
            if task_id in _active_tasks:
                task = _active_tasks[task_id]
                future = task.get("future")

                if future and not future.done():
                    future.cancel()
                    logger.info(f"Task {task_id} cancelled")

                task["status"] = "cancelled"
                task["completed_at"] = datetime.now()
                return True
        return False

    def get_active_task_for_video(self, video_id: int) -> Optional[Dict[str, Any]]:
        """
        Check if there's an active background task processing a specific video.

        Args:
            video_id: Video ID to check for active tasks

        Returns:
            Task info if found and active, None otherwise
        """
        with _task_lock:
            for task_id, task in _active_tasks.items():
                if task.get("video_id") == video_id and task.get("status") in [
                    "queued",
                    "processing",
                ]:
                    # Return a copy without the future object
                    response = task.copy()
                    response.pop("future", None)
                    response["task_id"] = task_id
                    return response
        return None

    def cleanup_completed_tasks(self, max_age_hours: int = 24) -> int:
        """Clean up old completed tasks to prevent memory leaks."""
        cutoff_time = datetime.now().timestamp() - (max_age_hours * 3600)
        tasks_to_remove = []

        with _task_lock:
            for task_id, task in _active_tasks.items():
                if task["status"] in ["completed", "failed", "cancelled"]:
                    completed_at = task.get("completed_at")
                    if completed_at and completed_at.timestamp() < cutoff_time:
                        tasks_to_remove.append(task_id)

            for task_id in tasks_to_remove:
                del _active_tasks[task_id]

        if tasks_to_remove:
            logger.info(f"Cleaned up {len(tasks_to_remove)} old tasks")

        return len(tasks_to_remove)

    def get_task_stats(self) -> Dict[str, Any]:
        """Get statistics about background tasks."""
        with _task_lock:
            total_tasks = len(_active_tasks)
            status_counts = {}

            for task in _active_tasks.values():
                status = task["status"]
                status_counts[status] = status_counts.get(status, 0) + 1

            # Count active workers (tasks currently processing)
            active_workers = status_counts.get("processing", 0)

        # Note: Avoid accessing private ThreadPoolExecutor attributes
        # They are internal implementation details and may change
        return {
            "total_tasks": total_tasks,
            "status_counts": status_counts,
            "max_workers": self.max_workers,  # Use our stored value
            "active_workers": active_workers,
        }

    def _run_pose_only_analysis(
        self,
        db: Session,
        video_id: int,
        video_path: str,
        confidence_threshold: float,
        task_id: int,
    ) -> Dict[str, Any]:
        """Run pose-only analysis using PoseDetectionService."""

        logger.info(f"Task {task_id}: Starting pose-only analysis")

        try:
            # Update progress
            update_task_progress(
                task_id, "pose_detection", 0, "Starting pose detection analysis", 30
            )

            # Use PoseDetectionService
            pose_service = PoseDetectionService()
            pose_results = pose_service.analyze_video_file(
                video_path=Path(video_path),
                confidence_threshold=confidence_threshold,
                detection_threshold=0.5,  # Default detection threshold
                max_frames=None,  # Process all frames
            )

            # Check for errors
            if "error" in pose_results:
                raise RuntimeError(f"Pose detection failed: {pose_results['error']}")

            # Update progress
            update_task_progress(
                task_id, "pose_detection", 50, "Saving pose detection results", 60
            )

            # Save results to PoseDetection table
            pose_detection = pose_service.save_detection_results(
                db=db, video_id=video_id, detection_results=pose_results
            )

            # Update progress
            update_task_progress(
                task_id, "pose_detection", 80, "Creating legacy analysis record", 90
            )

            # Create legacy Analysis record for backward compatibility
            analysis_record = create_analysis_record(
                db=db,
                video_id=video_id,
                video_filename=Path(video_path).name,
                analysis_type="pose_only",
                analysis_results={
                    "pose_detections": pose_results.get("detection_data", []),
                    "total_frames": pose_results.get("total_frames", 0),
                    "frames_with_poses": pose_results.get("frames_with_poses", 0),
                    "detection_rate": pose_results.get("detection_rate", 0.0),
                },
                processing_time=pose_results.get("processing_time_seconds", 0.0),
                model_used="mediapipe",
                confidence_threshold=confidence_threshold,
                status="completed",
            )

            # Update analysis status
            update_analysis_status(db, analysis_record.id, "completed")

            logger.info(f"Task {task_id}: Pose-only analysis completed successfully")

            return {
                "analysis_id": analysis_record.id,
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
            logger.error(f"Task {task_id}: Pose-only analysis failed: {e}")
            raise

    def _run_ball_only_analysis(
        self,
        db: Session,
        video_id: int,
        video_path: str,
        confidence_threshold: float,
        task_id: int,
    ) -> Dict[str, Any]:
        """Run ball-only analysis using BallDetectionService."""

        logger.info(f"Task {task_id}: Starting ball-only analysis")

        try:
            # Update progress
            update_task_progress(
                task_id, "ball_detection", 0, "Starting ball detection analysis", 30
            )

            # Use BallDetectionService
            ball_service = BallDetectionService()
            ball_results = ball_service.analyze_video_file(
                video_path=Path(video_path),
                confidence_threshold=confidence_threshold,
                video_quality_level=None,  # Will be determined by service
                max_frames=None,  # Process all frames
            )

            # Check for errors
            if "error" in ball_results:
                raise RuntimeError(f"Ball detection failed: {ball_results['error']}")

            # Update progress
            update_task_progress(
                task_id, "ball_detection", 50, "Saving ball detection results", 60
            )

            # Save results to BallDetection table
            ball_detection = ball_service.save_detection_results(
                db=db, video_id=video_id, detection_results=ball_results
            )

            # Update progress
            update_task_progress(
                task_id, "ball_detection", 80, "Creating legacy analysis record", 90
            )

            # Create legacy Analysis record for backward compatibility
            analysis_record = create_analysis_record(
                db=db,
                video_id=video_id,
                video_filename=Path(video_path).name,
                analysis_type="ball_only",
                analysis_results={
                    "ball_detections": ball_results.get("detection_data", []),
                    "total_frames": ball_results.get("total_frames", 0),
                    "frames_with_balls": ball_results.get("frames_with_balls", 0),
                    "detection_rate": ball_results.get("detection_rate", 0.0),
                },
                processing_time=ball_results.get("processing_time_seconds", 0.0),
                model_used=ball_results.get("model_used", "yolov8n"),
                confidence_threshold=confidence_threshold,
                status="completed",
            )

            # Update analysis status
            update_analysis_status(db, analysis_record.id, "completed")

            logger.info(f"Task {task_id}: Ball-only analysis completed successfully")

            return {
                "analysis_id": analysis_record.id,
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
            logger.error(f"Task {task_id}: Ball-only analysis failed: {e}")
            raise

    def _run_comprehensive_analysis(
        self,
        db: Session,
        video_id: int,
        video_path: str,
        confidence_threshold: float,
        include_pose_detection: bool,
        task_id: int,
    ) -> Dict[str, Any]:
        """Run comprehensive analysis using both BallDetectionService and PoseDetectionService."""

        logger.info(
            f"Task {task_id}: Starting comprehensive analysis (pose_detection={include_pose_detection})"
        )

        try:
            analysis_results = {}
            ball_detection_id = None
            pose_detection_id = None
            total_processing_time = 0.0

            # Run ball detection
            update_task_progress(
                task_id, "ball_detection", 0, "Starting ball detection analysis", 30
            )

            ball_service = BallDetectionService()
            ball_results = ball_service.analyze_video_file(
                video_path=Path(video_path),
                confidence_threshold=confidence_threshold,
                video_quality_level=None,
                max_frames=None,
            )

            if "error" in ball_results:
                raise RuntimeError(f"Ball detection failed: {ball_results['error']}")

            # Save ball detection results
            ball_detection = ball_service.save_detection_results(
                db=db, video_id=video_id, detection_results=ball_results
            )
            ball_detection_id = ball_detection.id
            total_processing_time += ball_results.get("processing_time_seconds", 0.0)

            analysis_results.update(
                {
                    "ball_detections": ball_results.get("detection_data", []),
                    "total_frames": ball_results.get("total_frames", 0),
                    "frames_with_balls": ball_results.get("frames_with_balls", 0),
                    "ball_detection_rate": ball_results.get("detection_rate", 0.0),
                }
            )

            # Run pose detection if requested
            if include_pose_detection:
                update_task_progress(
                    task_id,
                    "pose_detection",
                    30,
                    "Starting pose detection analysis",
                    60,
                )

                pose_service = PoseDetectionService()
                pose_results = pose_service.analyze_video_file(
                    video_path=Path(video_path),
                    confidence_threshold=confidence_threshold,
                    detection_threshold=0.5,
                    max_frames=None,
                )

                if "error" in pose_results:
                    raise RuntimeError(
                        f"Pose detection failed: {pose_results['error']}"
                    )

                # Save pose detection results
                pose_detection = pose_service.save_detection_results(
                    db=db, video_id=video_id, detection_results=pose_results
                )
                pose_detection_id = pose_detection.id
                total_processing_time += pose_results.get(
                    "processing_time_seconds", 0.0
                )

                analysis_results.update(
                    {
                        "pose_detections": pose_results.get("detection_data", []),
                        "frames_with_poses": pose_results.get("frames_with_poses", 0),
                        "pose_detection_rate": pose_results.get("detection_rate", 0.0),
                    }
                )

            # Update progress
            update_task_progress(
                task_id, "comprehensive", 60, "Creating legacy analysis record", 90
            )

            # Create legacy Analysis record for backward compatibility
            analysis_record = create_analysis_record(
                db=db,
                video_id=video_id,
                video_filename=Path(video_path).name,
                analysis_type="comprehensive",
                analysis_results=analysis_results,
                processing_time=total_processing_time,
                model_used="yolov8n+mediapipe" if include_pose_detection else "yolov8n",
                confidence_threshold=confidence_threshold,
                status="completed",
            )

            # Update analysis status
            update_analysis_status(db, analysis_record.id, "completed")

            logger.info(
                f"Task {task_id}: Comprehensive analysis completed successfully"
            )

            return {
                "analysis_id": analysis_record.id,
                "processing_time": total_processing_time,
                "analysis_summary": {
                    "total_frames": analysis_results.get("total_frames", 0),
                    "frames_with_balls": analysis_results.get("frames_with_balls", 0),
                    "ball_detection_rate": analysis_results.get(
                        "ball_detection_rate", 0.0
                    ),
                    "frames_with_poses": analysis_results.get("frames_with_poses", 0),
                    "pose_detection_rate": analysis_results.get(
                        "pose_detection_rate", 0.0
                    ),
                },
                "ball_detection_id": ball_detection_id,
                "pose_detection_id": pose_detection_id,
                "analysis_type": "comprehensive",
            }

        except Exception as e:
            logger.error(f"Task {task_id}: Comprehensive analysis failed: {e}")
            raise


# Global instance
background_service = BackgroundTaskService()
