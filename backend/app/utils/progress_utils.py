"""Progress update utilities for background tasks."""

import logging
import threading
from typing import Optional

logger = logging.getLogger(__name__)

# Global task storage (imported from background_service to avoid circular imports)
_active_tasks = {}
_task_lock = None


def set_task_storage(tasks: dict, lock: threading.Lock) -> None:
    """Set the task storage from background service."""
    global _active_tasks, _task_lock
    _active_tasks = tasks
    _task_lock = lock


def update_task_progress(
    task_id: Optional[int],
    current_stage: str,
    stage_progress: int,
    stage_message: str,
    overall_progress: Optional[int] = None,
) -> None:
    """Update task progress with stage information."""
    if task_id is None or _task_lock is None:
        return

    with _task_lock:
        if task_id in _active_tasks:
            _active_tasks[task_id]["current_stage"] = current_stage
            _active_tasks[task_id]["stage_progress"] = stage_progress
            _active_tasks[task_id]["stage_message"] = stage_message
            if overall_progress is not None:
                _active_tasks[task_id]["progress"] = overall_progress
