"""
Tests for RQ task functions.
"""

from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from app.services.rq_tasks import (
    analyze_ball_detection_rq,
    analyze_pose_detection_rq,
    create_video_annotation_rq,
)


@pytest.fixture
def mock_video():
    """Mock video object."""
    video = MagicMock()
    video.id = 1
    video.file_path = "/test/path/video.mp4"
    return video


@pytest.fixture
def mock_db_session():
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
    @patch("app.services.rq_tasks.PoseDetectionService")
    def test_success(
        self,
        mock_pose_service_class,
        mock_get_path,
        mock_get_video,
        mock_db_session,
        mock_video,
    ):
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
    def test_video_not_found(self, mock_get_video, mock_db_session):
        """Test error when video not found."""
        mock_get_video.return_value = None

        with pytest.raises(ValueError, match="Video 1 not found"):
            analyze_pose_detection_rq(
                video_id=1, video_path="/test/path/video.mp4", confidence_threshold=0.7
            )

    @patch("app.services.rq_tasks.video_service.get_video_by_id")
    @patch("app.services.rq_tasks.storage_service.get_local_file_path")
    @patch("app.services.rq_tasks.PoseDetectionService")
    def test_pose_detection_error(
        self,
        mock_pose_service_class,
        mock_get_path,
        mock_get_video,
        mock_db_session,
        mock_video,
    ):
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


class TestAnalyzeBallDetectionRq:
    """Tests for analyze_ball_detection_rq."""

    @patch("app.services.rq_tasks.video_service.get_video_by_id")
    @patch("app.services.rq_tasks.storage_service.get_local_file_path")
    @patch("app.services.rq_tasks.BallDetectionService")
    def test_success(
        self,
        mock_ball_service_class,
        mock_get_path,
        mock_get_video,
        mock_db_session,
        mock_video,
    ):
        """Test successful ball detection."""
        mock_get_video.return_value = mock_video
        mock_get_path.return_value = Path("/local/path/video.mp4")
        mock_ball_service = MagicMock()
        mock_ball_service_class.return_value = mock_ball_service

        # Mock ball detection results
        mock_ball_service.analyze_video_file.return_value = {
            "processing_time_seconds": 180.0,
            "total_frames": 1000,
            "frames_with_balls": 600,
            "detection_rate": 0.6,
        }

        # Mock ball detection model
        mock_ball_detection = MagicMock()
        mock_ball_detection.id = 456
        mock_ball_service.save_detection_results.return_value = mock_ball_detection

        result = analyze_ball_detection_rq(
            video_id=1, video_path="/test/path/video.mp4", confidence_threshold=0.7
        )

        assert result["status"] == "completed"
        assert result["ball_detection_id"] == 456
        assert result["analysis_type"] == "ball_only"
        mock_ball_service.analyze_video_file.assert_called_once()


class TestCreateVideoAnnotationRq:
    """Tests for create_video_annotation_rq."""

    @patch("app.services.rq_tasks.video_service.get_video_by_id")
    @patch("app.services.rq_tasks.storage_service.get_local_file_path")
    @patch("app.services.rq_tasks.VideoAnnotationService")
    def test_success_with_pose_detection(
        self,
        mock_annotation_service_class,
        mock_get_path,
        mock_get_video,
        mock_db_session,
        mock_video,
    ):
        """Test successful video annotation with pose detection."""
        mock_get_video.return_value = mock_video
        mock_get_path.return_value = Path("/local/path/video.mp4")

        # Mock pose detection in database
        mock_pose_detection = MagicMock()
        mock_pose_detection.id = 789
        mock_db_session.query.return_value.filter.return_value.order_by.return_value.first.side_effect = [
            None,  # No ball detection
            mock_pose_detection,  # Pose detection found
        ]

        mock_annotation_service = MagicMock()
        mock_annotation_service_class.return_value = mock_annotation_service

        # Mock annotation result
        mock_annotation_result = MagicMock()
        mock_annotation_result.id = 999
        mock_annotation_result.annotated_video_path = "/annotated/video.mp4"
        mock_annotation_service.create_pose_annotation.return_value = (
            mock_annotation_result
        )

        result = create_video_annotation_rq(
            video_id=1, video_path="/test/path/video.mp4", confidence_threshold=0.7
        )

        assert result["status"] == "completed"
        assert result["video_annotation_id"] == 999
        assert result["analysis_type"] == "video_annotation_only"

    @patch("app.services.rq_tasks.video_service.get_video_by_id")
    @patch("app.services.rq_tasks.storage_service.get_local_file_path")
    def test_no_detections_found(
        self, mock_get_path, mock_get_video, mock_db_session, mock_video
    ):
        """Test error when no detections found."""
        mock_get_video.return_value = mock_video
        mock_get_path.return_value = Path("/local/path/video.mp4")

        # Mock no detections in database
        mock_db_session.query.return_value.filter.return_value.order_by.return_value.first.side_effect = [
            None,  # No ball detection
            None,  # No pose detection
        ]

        with pytest.raises(ValueError, match="No ball or pose detections found"):
            create_video_annotation_rq(
                video_id=1, video_path="/test/path/video.mp4", confidence_threshold=0.7
            )
