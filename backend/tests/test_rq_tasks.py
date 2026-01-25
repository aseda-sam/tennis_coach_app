"""
Tests for RQ task functions.
"""

from pathlib import Path
from typing import Generator
from unittest.mock import MagicMock, patch

import pytest

from app.services.rq_tasks import analyze_pose_detection_rq


@pytest.fixture
def mock_video() -> MagicMock:
    """Mock video object."""
    video = MagicMock()
    video.id = 1
    video.file_path = "/test/path/video.mp4"
    return video


@pytest.fixture
def mock_db_session() -> Generator[MagicMock, None, None]:
    """Mock database session."""
    with patch("app.services.rq_tasks.SessionLocal") as mock_session:
        db = MagicMock()
        mock_session.return_value.__enter__.return_value = db
        mock_session.return_value.__exit__.return_value = None
        yield db


class TestAnalyzePoseDetectionRq:
    """Tests for analyze_pose_detection_rq."""

    @patch("app.services.rq_tasks.video_service.get_video_by_id")
    @patch("app.services.rq_tasks.storage_service.get_local_file_path")
    @patch("app.services.pose_detection.PoseDetectionService")
    def test_success(
        self,
        mock_pose_service_class: MagicMock,
        mock_get_path: MagicMock,
        mock_get_video: MagicMock,
        mock_db_session: MagicMock,
        mock_video: MagicMock,
    ) -> None:
        """Test successful pose detection."""
        mock_get_video.return_value = mock_video
        mock_get_path.return_value = Path("/local/path/video.mp4")
        mock_pose_service = MagicMock()
        mock_pose_service_class.return_value = mock_pose_service

        # Mock pose detection results
        mock_pose_service.analyze_video_file.return_value = {
            "processing_time_seconds": 120.0,
            "total_frames": 1000,
            "frames_with_poses": 800,
            "detection_rate": 0.8,
        }

        # Mock pose detection model
        mock_pose_detection = MagicMock()
        mock_pose_detection.id = 123
        mock_pose_service.save_detection_results.return_value = mock_pose_detection

        result = analyze_pose_detection_rq(
            video_id=1, video_path="/test/path/video.mp4", confidence_threshold=0.7
        )

        assert result["status"] == "completed"
        assert result["pose_detection_id"] == 123
        assert result["analysis_type"] == "pose_only"
        mock_pose_service.analyze_video_file.assert_called_once()

    @patch("app.services.rq_tasks.video_service.get_video_by_id")
    def test_video_not_found(
        self, mock_get_video: MagicMock, mock_db_session: MagicMock
    ) -> None:
        """Test error when video not found."""
        mock_get_video.return_value = None

        with pytest.raises(ValueError, match="Video 1 not found"):
            analyze_pose_detection_rq(
                video_id=1, video_path="/test/path/video.mp4", confidence_threshold=0.7
            )

    @patch("app.services.rq_tasks.video_service.get_video_by_id")
    @patch("app.services.rq_tasks.storage_service.get_local_file_path")
    @patch("app.services.pose_detection.PoseDetectionService")
    def test_pose_detection_error(
        self,
        mock_pose_service_class: MagicMock,
        mock_get_path: MagicMock,
        mock_get_video: MagicMock,
        mock_db_session: MagicMock,
        mock_video: MagicMock,
    ) -> None:
        """Test error handling when pose detection fails."""
        mock_get_video.return_value = mock_video
        mock_get_path.return_value = Path("/local/path/video.mp4")
        mock_pose_service = MagicMock()
        mock_pose_service_class.return_value = mock_pose_service

        # Mock pose detection error
        mock_pose_service.analyze_video_file.return_value = {
            "error": "Detection failed"
        }

        with pytest.raises(RuntimeError, match="Pose detection failed"):
            analyze_pose_detection_rq(
                video_id=1, video_path="/test/path/video.mp4", confidence_threshold=0.7
            )


