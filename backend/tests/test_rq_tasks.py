"""
Tests for RQ task functions.
"""

from pathlib import Path
from typing import Generator
from unittest.mock import MagicMock, patch

import pytest

from app.services.rq_tasks import (
    analyze_pose_detection_rq,
    analyze_pose_detection_scout_refine_rq,
    transcode_video_rq,
)


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
        """Test resilient exit when video deleted before job started."""
        mock_get_video.return_value = None

        result = analyze_pose_detection_rq(
            video_id=1, video_path="/test/path/video.mp4", confidence_threshold=0.7
        )

        assert result["status"] == "cancelled"
        assert result["reason"] == "video_deleted"

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


class TestTranscodeVideoRq:
    """Tests for transcode_video_rq."""

    @pytest.fixture
    def mock_video_large(self) -> MagicMock:
        """Mock video object with large file size."""
        video = MagicMock()
        video.id = 1
        video.file_path = "/test/path/video.mp4"
        video.file_size = 25 * 1024 * 1024  # 25MB, above threshold
        video.user_id = "test-user-id"
        return video

    @pytest.fixture
    def mock_video_small(self) -> MagicMock:
        """Mock video object with small file size."""
        video = MagicMock()
        video.id = 1
        video.file_path = "/test/path/video.mp4"
        video.file_size = 10 * 1024 * 1024  # 10MB, below threshold
        video.user_id = "test-user-id"
        return video

    @patch("app.services.rq_tasks.video_service.get_video_by_id")
    def test_transcode_returns_cancelled_when_video_deleted(
        self, mock_get_video: MagicMock, mock_db_session: MagicMock
    ) -> None:
        """Test resilient exit when video deleted before transcode job started."""
        mock_get_video.return_value = None

        result = transcode_video_rq(video_id=1, video_path="/test/path/video.mp4")

        assert result["status"] == "cancelled"
        assert result["reason"] == "video_deleted"

    @patch("app.services.rq_tasks.video_service.get_video_by_id")
    @patch("app.services.rq_tasks.settings.TRANSCODE_THRESHOLD_BYTES", 20 * 1024 * 1024)
    def test_transcode_skips_when_file_size_below_threshold(
        self,
        mock_get_video: MagicMock,
        mock_db_session: MagicMock,
        mock_video_small: MagicMock,
    ) -> None:
        """Test that transcode is skipped when file size is below threshold."""
        mock_get_video.return_value = mock_video_small

        with patch(
            "app.services.rq_tasks.storage_service.replace_file"
        ) as mock_replace, patch(
            "app.services.rq_tasks.subprocess.run"
        ) as mock_subprocess:
            result = transcode_video_rq(video_id=1, video_path="/test/path/video.mp4")

            assert result["status"] == "skipped"
            assert result["reason"] == "file_too_small"
            assert result["file_size"] == mock_video_small.file_size
            # Verify transcode operations were not called
            mock_replace.assert_not_called()
            mock_subprocess.assert_not_called()

    @patch("app.services.rq_tasks.video_service.get_video_by_id")
    @patch("app.services.rq_tasks.storage_service.get_local_file_path")
    @patch("app.services.rq_tasks.storage_service.replace_file")
    @patch("app.services.rq_tasks.subprocess.run")
    @patch("app.services.rq_tasks.cv2.VideoCapture")
    @patch("app.services.rq_tasks.get_video_rotation")
    @patch("app.services.rq_tasks.tempfile.mkstemp")
    def test_transcode_success_updates_video_and_returns_completed(
        self,
        mock_mkstemp: MagicMock,
        mock_get_rotation: MagicMock,
        mock_cv2_capture: MagicMock,
        mock_subprocess: MagicMock,
        mock_replace_file: MagicMock,
        mock_get_path: MagicMock,
        mock_get_video: MagicMock,
        mock_db_session: MagicMock,
        mock_video_large: MagicMock,
    ) -> None:
        """Test successful transcoding updates video record and returns completed status."""
        import tempfile

        mock_get_video.return_value = mock_video_large
        # get_local_file_path returns a single Path, not a tuple
        mock_get_path.return_value = Path("/local/path/video.mp4")

        # Mock temp file creation
        temp_fd, temp_path = tempfile.mkstemp(suffix=".mp4")
        mock_mkstemp.return_value = (temp_fd, temp_path)

        # Mock ffmpeg success
        mock_subprocess_result = MagicMock()
        mock_subprocess_result.returncode = 0
        mock_subprocess_result.stderr = ""
        mock_subprocess.return_value = mock_subprocess_result

        # Mock cv2 metadata extraction
        mock_cap = MagicMock()
        mock_cv2_capture.return_value = mock_cap
        mock_cap.isOpened.return_value = True
        # Use proper cv2 constants
        import cv2

        def get_prop(prop: int) -> float:
            if prop == cv2.CAP_PROP_FPS:
                return 30.0
            elif prop == cv2.CAP_PROP_FRAME_COUNT:
                return 900.0
            elif prop == cv2.CAP_PROP_FRAME_WIDTH:
                return 1280.0
            elif prop == cv2.CAP_PROP_FRAME_HEIGHT:
                return 720.0
            return 0.0

        mock_cap.get.side_effect = get_prop
        mock_cap.release.return_value = None

        mock_get_rotation.return_value = 0

        # Mock replace_file to return new path
        new_storage_path = "/test/path/video_transcoded.mp4"
        transcoded_content = b"transcoded video content"
        mock_replace_file.return_value = new_storage_path

        # Mock file reading
        with patch("builtins.open", create=True) as mock_open:
            mock_file = MagicMock()
            mock_file.__enter__.return_value.read.return_value = transcoded_content
            mock_file.__exit__.return_value = None
            mock_open.return_value = mock_file

            result = transcode_video_rq(video_id=1, video_path="/test/path/video.mp4")

        assert result["status"] == "completed"
        assert result["original_file_size"] == mock_video_large.file_size
        assert result["new_file_size"] == len(transcoded_content)
        assert "size_reduction_percent" in result
        assert result["new_width"] == 1280
        assert result["new_height"] == 720
        assert result["new_fps"] == 30.0

        # Verify video was updated
        assert mock_video_large.file_path == new_storage_path
        assert mock_video_large.file_size == len(transcoded_content)
        assert mock_video_large.is_transcoded is True
        assert mock_video_large.original_file_size == mock_video_large.file_size
        mock_db_session.commit.assert_called()

    @patch("app.services.rq_tasks.video_service.get_video_by_id")
    @patch("app.services.rq_tasks.storage_service.get_local_file_path")
    @patch("app.services.rq_tasks.subprocess.run")
    @patch("app.services.rq_tasks.tempfile.mkstemp")
    def test_transcode_raises_when_ffmpeg_fails(
        self,
        mock_mkstemp: MagicMock,
        mock_subprocess: MagicMock,
        mock_get_path: MagicMock,
        mock_get_video: MagicMock,
        mock_db_session: MagicMock,
        mock_video_large: MagicMock,
    ) -> None:
        """Test that transcode raises RuntimeError when ffmpeg fails."""
        import tempfile

        mock_get_video.return_value = mock_video_large
        mock_get_path.return_value = Path("/local/path/video.mp4")

        temp_fd, temp_path = tempfile.mkstemp(suffix=".mp4")
        mock_mkstemp.return_value = (temp_fd, temp_path)

        # Mock ffmpeg failure
        mock_subprocess_result = MagicMock()
        mock_subprocess_result.returncode = 1
        mock_subprocess_result.stderr = "ffmpeg error: codec not found"
        mock_subprocess.return_value = mock_subprocess_result

        with pytest.raises(RuntimeError, match="ffmpeg transcoding failed"):
            transcode_video_rq(video_id=1, video_path="/test/path/video.mp4")


class TestAnalyzePoseDetectionScoutRefineRq:
    """Tests for analyze_pose_detection_scout_refine_rq."""

    @patch("app.services.rq_tasks.video_service.get_video_by_id")
    def test_scout_refine_returns_cancelled_when_video_deleted(
        self, mock_get_video: MagicMock, mock_db_session: MagicMock
    ) -> None:
        """Test resilient exit when video deleted before scout/refine job started."""
        mock_get_video.return_value = None

        result = analyze_pose_detection_scout_refine_rq(
            video_id=1, video_path="/test/path/video.mp4"
        )

        assert result["status"] == "cancelled"
        assert result["reason"] == "video_deleted"

    @patch("app.services.rq_tasks.video_service.get_video_by_id")
    @patch("app.services.rq_tasks.storage_service.get_local_file_path")
    @patch("app.services.pose_detection.PoseDetectionService")
    @patch("app.services.rq_tasks.generate_proposals")
    def test_scout_refine_completes_with_scout_only_when_no_proposals(
        self,
        mock_generate_proposals: MagicMock,
        mock_pose_service_class: MagicMock,
        mock_get_path: MagicMock,
        mock_get_video: MagicMock,
        mock_db_session: MagicMock,
        mock_video: MagicMock,
    ) -> None:
        """Test that scout/refine completes with scout data only when no serve windows found."""
        mock_get_video.return_value = mock_video
        mock_get_path.return_value = Path("/local/path/video.mp4")
        mock_pose_service = MagicMock()
        mock_pose_service_class.return_value = mock_pose_service

        # Mock scout results
        mock_pose_service.analyze_video_file.return_value = {
            "processing_time_seconds": 60.0,
            "total_frames": 900,
            "frames_with_poses": 700,
            "detection_rate": 0.78,
            "mode": "scout",
        }

        mock_pose_detection = MagicMock()
        mock_pose_detection.id = 123
        mock_pose_service.save_detection_results.return_value = mock_pose_detection

        # Mock no proposals found
        mock_generate_proposals.return_value = []

        result = analyze_pose_detection_scout_refine_rq(
            video_id=1, video_path="/test/path/video.mp4"
        )

        assert result["status"] == "completed"
        assert result["mode"] == "scout_only"
        assert result["serve_windows_found"] == 0
        assert result["pose_detection_id"] == 123

        # Verify refine was not called
        mock_pose_service.analyze_serve_windows.assert_not_called()

    @patch("app.services.rq_tasks.video_service.get_video_by_id")
    @patch("app.services.rq_tasks.storage_service.get_local_file_path")
    @patch("app.services.pose_detection.PoseDetectionService")
    @patch("app.services.rq_tasks.generate_proposals")
    def test_scout_refine_success_with_windows(
        self,
        mock_generate_proposals: MagicMock,
        mock_pose_service_class: MagicMock,
        mock_get_path: MagicMock,
        mock_get_video: MagicMock,
        mock_db_session: MagicMock,
        mock_video: MagicMock,
    ) -> None:
        """Test successful scout/refine pipeline when serve windows are found."""
        from app.models.serve_window_proposal import ServeWindowProposal

        mock_get_video.return_value = mock_video
        mock_get_path.return_value = Path("/local/path/video.mp4")
        mock_pose_service = MagicMock()
        mock_pose_service_class.return_value = mock_pose_service

        # Mock scout results
        mock_pose_service.analyze_video_file.return_value = {
            "processing_time_seconds": 60.0,
            "total_frames": 900,
            "frames_with_poses": 700,
            "detection_rate": 0.78,
            "mode": "scout",
        }

        scout_pose_detection = MagicMock()
        scout_pose_detection.id = 123
        mock_pose_service.save_detection_results.return_value = scout_pose_detection

        # Mock proposals found
        proposal1 = MagicMock(spec=ServeWindowProposal)
        proposal1.start_timestamp = 1.0
        proposal1.end_timestamp = 3.0
        proposal2 = MagicMock(spec=ServeWindowProposal)
        proposal2.start_timestamp = 5.0
        proposal2.end_timestamp = 7.0
        mock_generate_proposals.return_value = [proposal1, proposal2]

        # Mock refine results
        mock_pose_service.analyze_serve_windows.return_value = {
            "processing_time_seconds": 30.0,
            "total_frames": 900,
            "frames_with_poses": 600,
            "detection_rate": 0.67,
            "mode": "refine",
            "windows_processed": 2,
        }

        refine_pose_detection = MagicMock()
        refine_pose_detection.id = 456
        # Second call to save_detection_results returns refine result
        mock_pose_service.save_detection_results.side_effect = [
            scout_pose_detection,
            refine_pose_detection,
        ]

        result = analyze_pose_detection_scout_refine_rq(
            video_id=1, video_path="/test/path/video.mp4"
        )

        assert result["status"] == "completed"
        assert result["mode"] == "scout_refine"
        assert result["serve_windows_found"] == 2
        assert result["scout_pose_detection_id"] == 123
        assert result["refine_pose_detection_id"] == 456

        # Verify refine was called with correct windows
        mock_pose_service.analyze_serve_windows.assert_called_once()
        call_args = mock_pose_service.analyze_serve_windows.call_args
        windows = call_args[1]["windows"]
        assert len(windows) == 2
        assert windows[0]["start_ms"] == 1000.0
        assert windows[0]["end_ms"] == 3000.0
        assert windows[1]["start_ms"] == 5000.0
        assert windows[1]["end_ms"] == 7000.0
