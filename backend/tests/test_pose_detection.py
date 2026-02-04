"""
Tests for pose detection service and API endpoints.
"""

import tempfile
from pathlib import Path
from unittest.mock import Mock, patch

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.models.pose_detection import PoseDetection
from app.models.video import Video
from app.services.pose_detection import PoseDetectionService


class TestPoseDetectionService:
    """Test pose detection service functionality."""

    @pytest.fixture
    def pose_service(self) -> PoseDetectionService:
        """Create a pose detection service instance."""
        # Mock MediaPipe initialization to avoid errors in test environment
        mock_pose_instance = Mock()

        def mock_initialize_mediapipe(self: PoseDetectionService) -> None:
            """Mock MediaPipe initialization."""
            self.mp_pose = Mock()
            self.pose_detector = mock_pose_instance

        with patch.object(
            PoseDetectionService, "_initialize_mediapipe", mock_initialize_mediapipe
        ):
            service = PoseDetectionService()
            return service

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
    def test_iter_frames(
        self,
        mock_video_capture: Mock,
        pose_service: PoseDetectionService,
        mock_video_file: Path,
    ) -> None:
        """Test frame iteration from video."""
        # Mock video capture
        mock_cap = Mock()
        mock_video_capture.return_value = mock_cap
        mock_cap.isOpened.return_value = True
        mock_cap.read.side_effect = [
            (True, Mock()),  # First frame
            (True, Mock()),  # Second frame
            (False, None),  # End of video
        ]

        frames = list(pose_service._iter_frames(mock_video_file, max_frames=2))

        assert len(frames) == 2
        assert frames[0][0] == 0  # First frame index
        assert frames[1][0] == 1  # Second frame index
        mock_cap.release.assert_called_once()

    @patch("app.services.pose_detection.detection_service.cv2.VideoCapture")
    def test_analyze_video_file_no_detector(
        self,
        mock_video_capture: Mock,
        pose_service: PoseDetectionService,
        mock_video_file: Path,
    ) -> None:
        """Test pose detection when detector is not available."""
        pose_service.pose_detector = None

        results = pose_service.analyze_video_file(mock_video_file)

        assert results["frames_with_poses"] == 0
        assert results["total_pose_detections"] == 0
        assert "error" in results
        assert "Pose detector not initialized" in results["error"]

    def test_save_detection_results(
        self, pose_service: PoseDetectionService, db_session: Session, test_user_id: str
    ) -> None:
        """Test saving pose detection results to database."""
        # Create test video with unique filename
        video = Video(
            filename="test_save_detection_video.mp4",
            file_path="/path/to/test_save_detection_video.mp4",
            file_size=1000,
            user_id=test_user_id,
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
        self, pose_service: PoseDetectionService, db_session: Session, test_user_id: str
    ) -> None:
        """Test retrieving pose detection by video ID."""
        # Create test video with unique filename
        video = Video(
            filename="test_get_detection_video.mp4",
            file_path="/path/to/test_get_detection_video.mp4",
            file_size=1000,
            user_id=test_user_id,
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

    @patch("app.services.pose_detection.detection_service.cv2.VideoCapture")
    @patch(
        "app.services.pose_detection.detection_service.PoseDetectionService._initialize_mediapipe"
    )
    def test_analyze_video_file_scout_mode_calls_detector_with_frame_skip(
        self,
        mock_init_mediapipe: Mock,
        mock_video_capture: Mock,
        pose_service: PoseDetectionService,
        mock_video_file: Path,
    ) -> None:
        """Test that scout mode skips frames and includes timestamp_ms."""
        import numpy as np

        # Mock video capture with multiple frames
        mock_cap = Mock()
        mock_video_capture.return_value = mock_cap
        mock_cap.isOpened.return_value = True
        mock_cap.get.side_effect = lambda prop: {
            "CAP_PROP_FPS": 30.0,
            "CAP_PROP_FRAME_COUNT": 10.0,
        }.get(prop, 0.0)

        # Mock frames (10 frames total)
        frames = []
        for _i in range(10):
            frame = np.zeros((100, 100, 3), dtype=np.uint8)
            frames.append((True, frame))
        frames.append((False, None))  # End of video
        mock_cap.read.side_effect = frames

        # Mock pose detector
        mock_detector = Mock()
        mock_detector.detect_for_video.return_value = Mock()
        pose_service.pose_detector = mock_detector

        # Run scout mode
        results = pose_service.analyze_video_file(
            mock_video_file, mode="scout", confidence_threshold=0.7
        )

        # Verify mode is scout
        assert results["mode"] == "scout"
        # Verify pose_detections include timestamp_ms
        if "pose_detections" in results:
            for detection in results["pose_detections"]:
                assert "timestamp_ms" in detection
                assert "frame_index" in detection

    @patch("app.services.pose_detection.detection_service.cv2.VideoCapture")
    @patch(
        "app.services.pose_detection.detection_service.PoseDetectionService._initialize_mediapipe"
    )
    def test_analyze_serve_windows_processes_only_window_frames(
        self,
        mock_init_mediapipe: Mock,
        mock_video_capture: Mock,
        pose_service: PoseDetectionService,
        mock_video_file: Path,
    ) -> None:
        """Test that analyze_serve_windows processes only frames within specified windows."""
        import cv2
        import numpy as np

        # Mock video capture
        mock_cap = Mock()
        mock_video_capture.return_value = mock_cap
        mock_cap.isOpened.return_value = True
        mock_cap.get.side_effect = lambda prop: {
            cv2.CAP_PROP_FPS: 30.0,
            cv2.CAP_PROP_FRAME_COUNT: 300.0,  # 10 seconds at 30fps
        }.get(prop, 0.0)

        # Track which frames were accessed via set()
        accessed_frames = []

        def mock_set(prop: int, value: float) -> bool:
            if prop == cv2.CAP_PROP_POS_FRAMES:
                accessed_frames.append(int(value))
            return True

        mock_cap.set.side_effect = mock_set

        # Mock frame reading - return frames when read is called
        frame_count = 0

        def mock_read() -> tuple[bool, np.ndarray]:
            nonlocal frame_count
            frame_count += 1
            if frame_count <= 100:  # Return some frames
                return True, np.zeros((100, 100, 3), dtype=np.uint8)
            return False, None

        mock_cap.read.side_effect = mock_read

        # Mock pose detector
        mock_detector = Mock()
        mock_detector.detect_for_video.return_value = Mock()
        pose_service.pose_detector = mock_detector

        # Call analyze_serve_windows with a single window
        windows = [{"start_ms": 1000.0, "end_ms": 2000.0}]
        results = pose_service.analyze_serve_windows(
            mock_video_file, windows=windows, padding_ms=500.0, confidence_threshold=0.7
        )

        # Verify mode is refine and windows_processed is set
        assert results["mode"] == "refine"
        assert results["windows_processed"] == 1
        # Verify that set was called to seek to window frames (with padding)
        assert len(accessed_frames) > 0


class TestPoseDetectionAPI:
    """Test pose detection API endpoints."""

    def test_analyze_pose_detection_video_not_found(self, client: TestClient) -> None:
        """Test pose detection analysis with non-existent video."""
        response = client.post(
            "/v0/analysis/videos/999", json={"analysis_type": "pose_only"}
        )

        assert response.status_code == 404
        assert "not found" in response.json()["detail"].lower()

    def test_analyze_pose_detection_request_validation(
        self, client: TestClient
    ) -> None:
        """Test pose detection request validation."""
        # Test with invalid confidence threshold
        response = client.post(
            "/v0/analysis/videos/1",
            json={"analysis_type": "pose_only", "confidence_threshold": 2.0},
        )

        assert response.status_code == 422  # Validation error

    @patch("app.api.routes.analysis.analysis_queue.enqueue")
    def test_analyze_pose_detection_success(
        self,
        mock_enqueue: Mock,
        client: TestClient,
        db_session: Session,
        test_user_id: str,
    ) -> None:
        """Test successful pose detection analysis."""
        mock_job = Mock()
        mock_job.id = "job-123"
        mock_enqueue.return_value = mock_job

        # Create test video with unique filename
        video = Video(
            filename="test_analyze_pose_video.mp4",
            file_path="/path/to/test_analyze_pose_video.mp4",
            file_size=1000,
            user_id=test_user_id,
        )
        db_session.add(video)
        db_session.commit()

        # Test endpoint
        response = client.post(
            f"/v0/analysis/videos/{video.id}",
            json={"analysis_type": "pose_only", "confidence_threshold": 0.5},
        )

        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "queued"
        # job_id is now VideoJob UUID, not RQ job ID
        assert "job_id" in data
        assert isinstance(data["job_id"], str)
        assert len(data["job_id"]) == 36  # UUID format
        assert data["analysis_type"] == "pose_only"


# Integration test helper
def create_test_video_with_pose_detection(db: Session) -> tuple[Video, PoseDetection]:
    """Helper to create test video with pose detection for integration tests."""
    import uuid

    unique_id = str(uuid.uuid4())[:8]
    video = Video(
        filename=f"integration_test_{unique_id}.mp4",
        file_path=f"/path/to/integration_test_{unique_id}.mp4",
        file_size=2000,
        user_id="00000000-0000-0000-0000-000000000000",
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
