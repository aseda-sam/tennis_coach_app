"""
Background task service for video analysis.
"""

import logging
import threading
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime
from typing import Any, Dict, Optional

from app.core.database import get_db
from app.services.analysis_service import analyze_video, update_analysis_status
from app.services.video_service import get_video_by_id

logger = logging.getLogger(__name__)

# Global task storage (in production, use Redis or database)
_active_tasks: Dict[int, Dict[str, Any]] = {}
_task_counter = 0
_task_lock = threading.Lock()


class BackgroundTaskService:
    """Service for managing background video analysis tasks."""

    def __init__(self, max_workers: int = 2) -> None:
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

        # Store task info
        _active_tasks[task_id] = {
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

        # Store future for potential cancellation
        _active_tasks[task_id]["future"] = future
        _active_tasks[task_id]["status"] = "processing"

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
            # Update task status
            _active_tasks[task_id]["status"] = "processing"
            _active_tasks[task_id]["progress"] = 5

            # Get database session
            db = next(get_db())

            # Get video info
            video = get_video_by_id(db, video_id)
            if not video:
                raise ValueError(f"Video {video_id} not found")

            logger.info(f"Task {task_id}: Starting analysis for video {video.filename}")

            # Update progress - frame extraction
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
            _active_tasks[task_id]["progress"] = 95

            # Check for errors
            if isinstance(result, dict) and "error" in result:
                raise RuntimeError(result["error"])

            # Update task status
            _active_tasks[task_id]["status"] = "completed"
            _active_tasks[task_id]["progress"] = 100
            _active_tasks[task_id]["result"] = result
            _active_tasks[task_id]["completed_at"] = datetime.now()

            logger.info(f"Task {task_id}: Analysis completed successfully")

        except (OSError, ValueError, RuntimeError) as e:
            logger.error(f"Task {task_id}: Analysis failed: {e}")
            _active_tasks[task_id]["status"] = "failed"
            _active_tasks[task_id]["error"] = str(e)
            _active_tasks[task_id]["completed_at"] = datetime.now()

            # Update database status
            try:
                db = next(get_db())
                update_analysis_status(db, video_id, "failed", str(e))
            except (OSError, ValueError, RuntimeError) as db_error:
                logger.error(f"Failed to update database status: {db_error}")

    def get_task_status(self, task_id: int) -> Optional[Dict[str, Any]]:
        """Get the status of a background task."""
        task = _active_tasks.get(task_id)
        if task:
            # Remove future object from response (not serializable)
            response = task.copy()
            response.pop("future", None)
            return response
        return None

    def get_all_tasks(self) -> Dict[int, Dict[str, Any]]:
        """Get all active tasks."""
        tasks = {}
        for task_id, task in _active_tasks.items():
            # Remove future object from response
            response = task.copy()
            response.pop("future", None)
            tasks[task_id] = response
        return tasks

    def cancel_task(self, task_id: int) -> bool:
        """Cancel a background task."""
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

    def cleanup_completed_tasks(self, max_age_hours: int = 24) -> int:
        """Clean up old completed tasks to prevent memory leaks."""
        cutoff_time = datetime.now().timestamp() - (max_age_hours * 3600)
        tasks_to_remove = []

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
        total_tasks = len(_active_tasks)
        status_counts = {}

        for task in _active_tasks.values():
            status = task["status"]
            status_counts[status] = status_counts.get(status, 0) + 1

        return {
            "total_tasks": total_tasks,
            "status_counts": status_counts,
            "active_workers": len(self.executor._threads),
            "max_workers": self.executor._max_workers,
        }


# Global instance
background_service = BackgroundTaskService()
