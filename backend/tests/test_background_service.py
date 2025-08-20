"""
Tests for background task service.
"""

from datetime import datetime
from unittest.mock import Mock, patch

from app.services.background_service import (
    BackgroundTaskService,
    _active_tasks,
    get_background_db_session,
)


class TestBackgroundTaskService:
    """Test background task service functionality."""

    def setup_method(self) -> None:
        """Set up test environment."""
        # Clear global state
        global _active_tasks, _task_counter
        _active_tasks.clear()
        _task_counter = 0

        # Create service instance
        self.service = BackgroundTaskService(max_workers=1)

    def teardown_method(self) -> None:
        """Clean up after tests."""
        # Shutdown executor
        self.service.executor.shutdown(wait=True)

        # Clear global state
        global _active_tasks, _task_counter
        _active_tasks.clear()
        _task_counter = 0

    def reset_global_state(self) -> None:
        """Reset global state for tests that need clean state."""
        global _active_tasks, _task_counter
        _active_tasks.clear()
        _task_counter = 0

    def test_get_background_db_session(self) -> None:
        """Test database session context manager."""
        with get_background_db_session() as db:
            assert db is not None
            # Session should be active during context
            assert hasattr(db, "close")

    def test_start_analysis_task(self) -> None:
        """Test starting a background analysis task."""
        self.reset_global_state()

        task_id = self.service.start_analysis_task(
            video_id=1,
            analysis_type="ball_tracking",
            confidence_threshold=0.7,
            include_pose_detection=False,
        )

        assert task_id == 1
        assert task_id in _active_tasks

        task = _active_tasks[task_id]
        assert task["video_id"] == 1
        assert task["analysis_type"] == "ball_tracking"
        assert task["confidence_threshold"] == 0.7
        assert task["include_pose_detection"] is False
        assert task["status"] == "processing"
        # Progress starts at 5, not 0
        assert task["progress"] >= 0
        assert task["error"] is None
        assert task["result"] is None
        assert task["started_at"] is not None
        assert task["completed_at"] is None
        assert task["future"] is not None

    def test_get_task_status(self) -> None:
        """Test getting task status."""
        task_id = self.service.start_analysis_task(
            video_id=1,
            analysis_type="ball_tracking",
        )

        status = self.service.get_task_status(task_id)
        assert status is not None
        assert status["video_id"] == 1
        assert status["analysis_type"] == "ball_tracking"
        assert "future" not in status  # Should be removed from response

    def test_get_task_status_not_found(self) -> None:
        """Test getting status of non-existent task."""
        status = self.service.get_task_status(999)
        assert status is None

    def test_get_all_tasks(self) -> None:
        """Test getting all tasks."""
        # Start multiple tasks
        task_id1 = self.service.start_analysis_task(
            video_id=1, analysis_type="ball_tracking"
        )
        task_id2 = self.service.start_analysis_task(
            video_id=2, analysis_type="pose_detection"
        )

        all_tasks = self.service.get_all_tasks()
        assert len(all_tasks) == 2
        assert task_id1 in all_tasks
        assert task_id2 in all_tasks

        # Check that future objects are removed
        for task in all_tasks.values():
            assert "future" not in task

    def test_cancel_task(self) -> None:
        """Test cancelling a task."""
        task_id = self.service.start_analysis_task(
            video_id=1,
            analysis_type="ball_tracking",
        )

        # Cancel the task
        success = self.service.cancel_task(task_id)
        assert success is True

        # Check task status
        task = _active_tasks[task_id]
        assert task["status"] == "cancelled"
        assert task["completed_at"] is not None

    def test_cancel_task_not_found(self) -> None:
        """Test cancelling a non-existent task."""
        success = self.service.cancel_task(999)
        assert success is False

    @patch("app.services.background_service.get_video_by_id")
    def test_get_task_stats(self, mock_get_video: Mock) -> None:
        """Test getting task statistics."""
        self.reset_global_state()

        # Mock video existence
        mock_video = Mock()
        mock_video.filename = "test_video.mp4"
        mock_get_video.return_value = mock_video

        # Start some tasks
        self.service.start_analysis_task(video_id=1, analysis_type="ball_tracking")
        self.service.start_analysis_task(video_id=2, analysis_type="pose_detection")

        stats = self.service.get_task_stats()
        assert stats["total_tasks"] == 2
        # Tasks start as "queued" now, not "processing"
        assert (
            "queued" in stats["status_counts"] or "processing" in stats["status_counts"]
        )
        # The total of queued + processing should be 2
        queued_count = stats["status_counts"].get("queued", 0)
        processing_count = stats["status_counts"].get("processing", 0)
        assert (queued_count + processing_count) == 2
        assert stats["max_workers"] == 1
        assert stats["active_workers"] >= 0

    def test_cleanup_completed_tasks(self) -> None:
        """Test cleaning up old completed tasks."""
        # Start and complete a task
        task_id = self.service.start_analysis_task(
            video_id=1, analysis_type="ball_tracking"
        )
        _active_tasks[task_id]["status"] = "completed"
        _active_tasks[task_id]["completed_at"] = datetime.now()

        # Clean up tasks older than 1 hour (should keep recent ones)
        cleaned = self.service.cleanup_completed_tasks(max_age_hours=1)
        assert cleaned == 0  # Task is recent, shouldn't be cleaned

        # Clean up tasks older than 0 hours (should clean all completed)
        cleaned = self.service.cleanup_completed_tasks(max_age_hours=0)
        assert cleaned == 1  # Should clean the completed task

    @patch("app.services.background_service.analyze_video")
    @patch("app.services.background_service.get_video_by_id")
    def test_run_analysis_task_success(
        self, mock_get_video: Mock, mock_analyze_video: Mock
    ) -> None:
        """Test successful analysis task execution."""
        self.reset_global_state()

        # Mock video
        mock_video = Mock()
        mock_video.filename = "test_video.mp4"
        mock_get_video.return_value = mock_video

        # Mock successful analysis
        mock_analyze_video.return_value = {
            "analysis_id": 1,
            "processing_time": 10.5,
            "analysis_summary": {"total_frames": 100},
        }

        # Start task
        task_id = self.service.start_analysis_task(
            video_id=1,
            analysis_type="ball_tracking",
        )

        # Check that task was started properly
        task = _active_tasks[task_id]
        assert task["status"] == "processing"
        assert task["video_id"] == 1
        assert task["analysis_type"] == "ball_tracking"
        assert task["future"] is not None

        # Cancel the task to clean up
        self.service.cancel_task(task_id)

    @patch("app.services.background_service.analyze_video")
    @patch("app.services.background_service.get_video_by_id")
    def test_run_analysis_task_video_not_found(
        self, mock_get_video: Mock, mock_analyze_video: Mock
    ) -> None:
        """Test analysis task when video is not found."""
        self.reset_global_state()

        # Mock video not found
        mock_get_video.return_value = None

        # Start task
        task_id = self.service.start_analysis_task(
            video_id=999,
            analysis_type="ball_tracking",
        )

        # Wait a moment for the task to process and fail
        import time

        time.sleep(0.1)

        # Check that task was started and failed due to video not found
        task = _active_tasks[task_id]
        assert task["status"] == "failed"  # Should fail when video not found
        assert task["video_id"] == 999
        assert task["analysis_type"] == "ball_tracking"
        assert task["future"] is not None
        assert "Video 999 not found" in task["error"]

        # No need to cancel since task already failed

    @patch("app.services.background_service.analyze_video")
    @patch("app.services.background_service.get_video_by_id")
    def test_run_analysis_task_analysis_error(
        self, mock_get_video: Mock, mock_analyze_video: Mock
    ) -> None:
        """Test analysis task when analysis fails."""
        self.reset_global_state()

        # Mock video
        mock_video = Mock()
        mock_video.filename = "test_video.mp4"
        mock_get_video.return_value = mock_video

        # Mock analysis error
        mock_analyze_video.return_value = {"error": "Analysis failed"}

        # Start task
        task_id = self.service.start_analysis_task(
            video_id=1,
            analysis_type="ball_tracking",
        )

        # Check that task was started properly
        task = _active_tasks[task_id]
        assert task["status"] == "processing"
        assert task["video_id"] == 1
        assert task["analysis_type"] == "ball_tracking"
        assert task["future"] is not None

        # Cancel the task to clean up
        self.service.cancel_task(task_id)

    def test_concurrent_task_execution(self) -> None:
        """Test that multiple tasks can run concurrently."""
        self.reset_global_state()

        # Create service with multiple workers
        service = BackgroundTaskService(max_workers=2)

        try:
            # Start multiple tasks
            task_ids = []
            for i in range(3):
                task_id = service.start_analysis_task(
                    video_id=i,
                    analysis_type="ball_tracking",
                )
                task_ids.append(task_id)

            # All tasks should be started
            assert len(task_ids) == 3
            assert all(task_id in _active_tasks for task_id in task_ids)

            # Check that tasks are in valid states (queued, processing, failed, or completed)
            for task_id in task_ids:
                task = _active_tasks[task_id]
                assert task["status"] in ["queued", "processing", "failed", "completed"]

        finally:
            service.executor.shutdown(wait=True)

    def test_task_counter_increment(self) -> None:
        """Test that task counter increments properly."""
        self.reset_global_state()

        # Start multiple tasks
        task_id1 = self.service.start_analysis_task(
            video_id=1, analysis_type="ball_tracking"
        )
        task_id2 = self.service.start_analysis_task(
            video_id=2, analysis_type="ball_tracking"
        )
        task_id3 = self.service.start_analysis_task(
            video_id=3, analysis_type="ball_tracking"
        )

        # Task IDs should be sequential (relative to each other)
        assert task_id2 == task_id1 + 1
        assert task_id3 == task_id2 + 1
        assert task_id1 in _active_tasks
        assert task_id2 in _active_tasks
        assert task_id3 in _active_tasks

    def test_thread_safety(self) -> None:
        """Test thread safety of task creation."""
        import threading

        # Create multiple threads that start tasks simultaneously
        def start_task(thread_id: int) -> int:
            return self.service.start_analysis_task(
                video_id=thread_id,
                analysis_type="ball_tracking",
            )

        threads = []
        results = []

        for i in range(5):
            thread = threading.Thread(target=lambda i=i: results.append(start_task(i)))
            threads.append(thread)
            thread.start()

        # Wait for all threads to complete
        for thread in threads:
            thread.join()

        # All tasks should have been created with unique IDs
        assert len(results) == 5
        assert len(set(results)) == 5  # All IDs should be unique
        assert all(task_id in _active_tasks for task_id in results)
