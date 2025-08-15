"""
Background task service for video analysis.
"""

import logging
import threading
from concurrent.futures import ThreadPoolExecutor
from contextlib import contextmanager
from datetime import datetime
from typing import Any, Dict, Optional

from sqlalchemy.orm import Session

from app.core.database import SessionLocal
from app.services.analysis_service import analyze_video, update_analysis_status
from app.services.video_service import get_video_by_id

logger = logging.getLogger(__name__)

# Global task storage (in production, use Redis or database)
_active_tasks: Dict[int, Dict[str, Any]] = {}
_task_counter = 0
_task_lock = threading.Lock()


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
            analysis_type: Type of analysis (ball_tracking, pose_detection, comprehensive)
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

        # Store future for potential cancellation (keep status as "queued" until processing starts)
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

            # Use proper database session management
            with get_background_db_session() as db:
                # Get video info
                video = get_video_by_id(db, video_id)
                if not video:
                    raise ValueError(f"Video {video_id} not found")

                logger.info(
                    f"Task {task_id}: Starting analysis for video {video.filename}"
                )

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

                # Run analysis (this is the CPU-intensive part)
                result = analyze_video(
                    db=db,
                    video_id=video_id,
                    analysis_type=analysis_type,
                    confidence_threshold=confidence_threshold,
                    include_pose_detection=include_pose_detection,
                )

                # Update progress
                with _task_lock:
                    if task_id in _active_tasks:
                        _active_tasks[task_id]["progress"] = 95

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


# Global instance
background_service = BackgroundTaskService()
