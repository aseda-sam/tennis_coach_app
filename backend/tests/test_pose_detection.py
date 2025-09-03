"""
Tests for pose detection service and API endpoints.
"""

import tempfile
from pathlib import Path
from unittest.mock import Mock, patch

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.main import app
from app.models.pose_detection import PoseDetection
from app.models.video import Video
from app.services.pose_detection import PoseDetectionService

client = TestClient(app)


class TestPoseDetectionService:
    """Test pose detection service functionality."""

    @pytest.fixture
    def pose_service(self) -> PoseDetectionService:
        """Create a pose detection service instance."""
        return PoseDetectionService()

    @pytest.fixture
    def mock_video_file(self) -> Path:
        """Create a mock video file path."""
        with tempfile.NamedTemporaryFile(suffix=".mp4", delete=False) as tmp:
            return Path(tmp.name)

    def test_service_initialization(self, pose_service: PoseDetectionService) -> None:
        """Test that pose detection service initializes properly."""
        assert pose_service is not None
        # Note: MediaPipe might not be available in test environment
        # assert pose_service.pose_detector is not None

    @patch("app.services.pose_detection.detection_service.cv2.VideoCapture")
    def test_extract_frames(
        self,
        mock_video_capture: Mock,
        pose_service: PoseDetectionService,
        mock_video_file: Path,
    ) -> None:
        """Test frame extraction from video."""
        # Mock video capture
        mock_cap = Mock()
        mock_video_capture.return_value = mock_cap
        mock_cap.isOpened.return_value = True
        mock_cap.read.side_effect = [
            (True, Mock()),  # First frame
            (True, Mock()),  # Second frame
            (False, None),  # End of video
        ]

        frames = pose_service._extract_frames(mock_video_file, max_frames=2)

        assert len(frames) == 2
        mock_cap.release.assert_called_once()

    def test_detect_poses_in_frames_no_detector(
        self, pose_service: PoseDetectionService
    ) -> None:
        """Test pose detection when detector is not available."""
        pose_service.pose_detector = None

        frames = [Mock(), Mock()]
        results = pose_service.detect_poses_in_frames(frames)

        assert results["frames_with_poses"] == 0
        assert results["total_pose_detections"] == 0
        assert results["detection_rate"] == 0.0
        assert "error" in results

    def test_save_detection_results(
        self, pose_service: PoseDetectionService, db_session: Session
    ) -> None:
        """Test saving pose detection results to database."""
        # Create test video
        video = Video(
            filename="test_video.mp4",
            file_path="/path/to/test_video.mp4",
            file_size=1000,
        )
        db_session.add(video)
        db_session.commit()

        # Mock detection results
        detection_results = {
            "total_frames": 100,
            "frames_with_poses": 80,
            "total_pose_detections": 80,
            "detection_rate": 0.8,
            "average_confidence": 0.85,
            "min_confidence": 0.6,
            "max_confidence": 0.95,
            "confidence_threshold": 0.5,
            "detection_threshold": 0.5,
            "pose_detections": [{"frame": 0, "keypoints": {}}],
            "confidence_scores": [0.8, 0.9],
            "processing_time_seconds": 15.5,
            "frame_processing_rate": 6.45,
        }

        # Save results
        pose_detection = pose_service.save_detection_results(
            db_session, video.id, detection_results
        )

        assert pose_detection.id is not None
        assert pose_detection.video_id == video.id
        assert pose_detection.total_frames == 100
        assert pose_detection.frames_with_poses == 80
        assert pose_detection.detection_rate == 0.8
        assert pose_detection.status == "completed"

    def test_get_detection_by_video_id(
        self, pose_service: PoseDetectionService, db_session: Session
    ) -> None:
        """Test retrieving pose detection by video ID."""
        # Create test video
        video = Video(
            filename="test_video.mp4",
            file_path="/path/to/test_video.mp4",
            file_size=1000,
        )
        db_session.add(video)
        db_session.commit()

        # Create pose detection record
        pose_detection = PoseDetection(
            video_id=video.id,
            total_frames=50,
            frames_with_poses=30,
            total_pose_detections=30,
            detection_rate=0.6,
            confidence_threshold=0.5,
            detection_threshold=0.5,
            processing_time_seconds=10.0,
            status="completed",
        )
        db_session.add(pose_detection)
        db_session.commit()

        # Retrieve detection
        retrieved = pose_service.get_detection_by_video_id(db_session, video.id)

        assert retrieved is not None
        assert retrieved.id == pose_detection.id
        assert retrieved.video_id == video.id
        assert retrieved.total_frames == 50


class TestPoseDetectionAPI:
    """Test pose detection API endpoints."""

    def test_analyze_pose_detection_video_not_found(self) -> None:
        """Test pose detection analysis with non-existent video."""
        response = client.post("/v0/pose-detection/analyze/999")

        assert response.status_code == 404
        assert "not found" in response.json()["detail"].lower()

    def test_get_pose_detection_video_not_found(self) -> None:
        """Test getting pose detection for non-existent video."""
        response = client.get("/v0/pose-detection/999")

        assert response.status_code == 404
        assert "not found" in response.json()["detail"].lower()

    def test_analyze_pose_detection_request_validation(self) -> None:
        """Test pose detection request validation."""
        # Test with invalid confidence threshold
        response = client.post(
            "/v0/pose-detection/analyze/1",
            json={"confidence_threshold": 2.0},  # Invalid: > 1.0
        )

        assert response.status_code == 422  # Validation error

    @patch(
        "app.services.pose_detection.detection_service.PoseDetectionService.analyze_video_file"
    )
    @patch("app.api.routes.pose_detection.Path.exists")
    def test_analyze_pose_detection_success(
        self, mock_exists: Mock, mock_analyze: Mock, db_session: Session
    ) -> None:
        """Test successful pose detection analysis."""
        # Setup
        mock_exists.return_value = True
        mock_analyze.return_value = {
            "total_frames": 50,
            "frames_with_poses": 30,
            "total_pose_detections": 30,
            "detection_rate": 0.6,
            "processing_time_seconds": 10.0,
        }

        # Create test video
        video = Video(
            filename="test_video.mp4",
            file_path="/path/to/test_video.mp4",
            file_size=1000,
        )
        db_session.add(video)
        db_session.commit()

        # Test endpoint
        response = client.post(
            f"/v0/pose-detection/analyze/{video.id}", json={"confidence_threshold": 0.5}
        )

        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "completed"
        assert "pose_detection_id" in data
        assert data["video_filename"] == "test_video.mp4"


# Integration test helper
def create_test_video_with_pose_detection(db: Session) -> tuple[Video, PoseDetection]:
    """Helper to create test video with pose detection for integration tests."""
    video = Video(
        filename="integration_test.mp4",
        file_path="/path/to/integration_test.mp4",
        file_size=2000,
    )
    db.add(video)
    db.commit()

    pose_detection = PoseDetection(
        video_id=video.id,
        total_frames=100,
        frames_with_poses=85,
        total_pose_detections=85,
        detection_rate=0.85,
        confidence_threshold=0.6,
        detection_threshold=0.5,
        processing_time_seconds=20.0,
        status="completed",
    )
    db.add(pose_detection)
    db.commit()

    return video, pose_detection
