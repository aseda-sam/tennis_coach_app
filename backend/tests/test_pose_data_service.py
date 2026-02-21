"""
Unit tests for pose_data_service module.

Tests the keypoint extraction helper and pose timestamp lookup functions,
ensuring compatibility with both old and new pose data formats.
"""

import json
from unittest.mock import MagicMock

from app.services.pose_data_service import (
    _compute_toss_metrics,
    _extract_keypoints,
    get_pose_at_timestamp,
)


class TestExtractKeypoints:
    """Unit tests for _extract_keypoints helper function."""

    def test_extract_keypoints_from_new_format(self) -> None:
        """Test extracting keypoints from new format with wrapper dict."""
        frame_data = {
            "frame_index": 42,
            "timestamp_ms": 1400.0,
            "keypoints": {
                "right_shoulder": [100.0, 50.0, 0.9],
                "right_elbow": [120.0, 80.0, 0.85],
                "right_wrist": [140.0, 100.0, 0.88],
            },
        }

        result = _extract_keypoints(frame_data)

        assert result is not None
        assert "right_shoulder" in result
        assert "right_elbow" in result
        assert "right_wrist" in result
        assert result["right_shoulder"] == [100.0, 50.0, 0.9]

    def test_extract_keypoints_from_old_format(self) -> None:
        """Test extracting keypoints from old format (keypoints dict directly)."""
        frame_data = {
            "right_shoulder": [100.0, 50.0, 0.9],
            "right_elbow": [120.0, 80.0, 0.85],
            "right_wrist": [140.0, 100.0, 0.88],
        }

        result = _extract_keypoints(frame_data)

        assert result is not None
        assert "right_shoulder" in result
        assert result["right_shoulder"] == [100.0, 50.0, 0.9]

    def test_extract_keypoints_from_none(self) -> None:
        """Test extracting keypoints when frame_data is None."""
        result = _extract_keypoints(None)
        assert result is None

    def test_extract_keypoints_new_format_with_null_keypoints(self) -> None:
        """Test extracting keypoints when new format has null keypoints."""
        frame_data = {
            "frame_index": 42,
            "timestamp_ms": 1400.0,
            "keypoints": None,
        }

        result = _extract_keypoints(frame_data)
        assert result is None


class TestGetPoseAtTimestamp:
    """Unit tests for get_pose_at_timestamp function."""

    def _create_mock_pose_detection(self, pose_data: list) -> MagicMock:
        """Create mock PoseDetection with given pose data."""
        mock = MagicMock()
        mock.pose_data = json.dumps(pose_data)
        return mock

    def _create_mock_video(self, fps: float = 30.0) -> MagicMock:
        """Create mock Video with given FPS."""
        mock = MagicMock()
        mock.fps = fps
        return mock

    def test_get_pose_at_timestamp_new_format(self) -> None:
        """Test getting pose at timestamp with new format pose data."""
        # Create pose data in new format
        pose_data = [
            {
                "frame_index": 0,
                "timestamp_ms": 0.0,
                "keypoints": {"right_shoulder": [100.0, 50.0, 0.9]},
            },
            {
                "frame_index": 1,
                "timestamp_ms": 33.33,
                "keypoints": {"right_shoulder": [101.0, 51.0, 0.9]},
            },
            {
                "frame_index": 2,
                "timestamp_ms": 66.67,
                "keypoints": {"right_shoulder": [102.0, 52.0, 0.9]},
            },
        ]

        pose_detection = self._create_mock_pose_detection(pose_data)
        video = self._create_mock_video(fps=30.0)

        # Request timestamp at frame 2 (2/30 = 0.0667s -> int(0.0667 * 30) = 2)
        result = get_pose_at_timestamp(pose_detection, video, 0.0667)

        assert result is not None
        assert "right_shoulder" in result
        assert result["right_shoulder"] == [102.0, 52.0, 0.9]

    def test_get_pose_at_timestamp_old_format(self) -> None:
        """Test getting pose at timestamp with old format pose data."""
        # Create pose data in old format (keypoints directly)
        pose_data = [
            {"right_shoulder": [100.0, 50.0, 0.9]},
            {"right_shoulder": [101.0, 51.0, 0.9]},
            {"right_shoulder": [102.0, 52.0, 0.9]},
        ]

        pose_detection = self._create_mock_pose_detection(pose_data)
        video = self._create_mock_video(fps=30.0)

        # Request timestamp at frame 2 (2/30 = 0.0667s -> int(0.0667 * 30) = 2)
        result = get_pose_at_timestamp(pose_detection, video, 0.0667)

        assert result is not None
        assert "right_shoulder" in result
        assert result["right_shoulder"] == [102.0, 52.0, 0.9]

    def test_get_pose_at_timestamp_finds_nearby_frame(self) -> None:
        """Test that function finds nearby frame when exact frame has no pose."""
        # Create pose data with null keypoints at target frame
        pose_data = [
            {
                "frame_index": 0,
                "timestamp_ms": 0.0,
                "keypoints": {"right_shoulder": [100.0, 50.0, 0.9]},
            },
            {
                "frame_index": 1,
                "timestamp_ms": 33.33,
                "keypoints": None,  # No pose at target frame
            },
            {
                "frame_index": 2,
                "timestamp_ms": 66.67,
                "keypoints": {"right_shoulder": [102.0, 52.0, 0.9]},
            },
        ]

        pose_detection = self._create_mock_pose_detection(pose_data)
        video = self._create_mock_video(fps=30.0)

        # Request timestamp at frame 1 (which has null keypoints)
        result = get_pose_at_timestamp(pose_detection, video, 0.0333)

        # Should find nearby frame (frame 0 or 2)
        assert result is not None
        assert "right_shoulder" in result

    def test_get_pose_at_timestamp_returns_none_when_no_data(self) -> None:
        """Test returns None when pose detection has no data."""
        pose_detection = MagicMock()
        pose_detection.pose_data = None

        video = self._create_mock_video()

        result = get_pose_at_timestamp(pose_detection, video, 1.0)
        assert result is None

    def test_get_pose_at_timestamp_empty_pose_data(self) -> None:
        """Test returns None when pose data is empty."""
        pose_detection = self._create_mock_pose_detection([])
        video = self._create_mock_video()

        result = get_pose_at_timestamp(pose_detection, video, 1.0)
        assert result is None

    def test_get_pose_at_timestamp_uses_default_fps(self) -> None:
        """Test uses default 30 FPS when video has no FPS."""
        pose_data = [
            {
                "frame_index": 0,
                "timestamp_ms": 0.0,
                "keypoints": {"right_shoulder": [100.0, 50.0, 0.9]},
            },
        ]

        pose_detection = self._create_mock_pose_detection(pose_data)
        video = MagicMock()
        video.fps = None  # No FPS set

        # Should use default 30 FPS, so timestamp 0 = frame 0
        result = get_pose_at_timestamp(pose_detection, video, 0.0)
        assert result is not None


class TestComputeTossMetrics:
    """Tests for toss_laterality computation in _compute_toss_metrics."""

    def _make_serve_window(
        self, start: float = 0.0, end: float = 2.0, contact: float | None = 1.0
    ) -> MagicMock:
        sw = MagicMock()
        sw.start_timestamp = start
        sw.end_timestamp = end
        sw.contact_timestamp = contact
        return sw

    def _make_video(self, height: int = 720, fps: float = 30.0) -> MagicMock:
        v = MagicMock()
        v.height = height
        v.fps = fps
        return v

    def _make_ball_detection(self, ball_list: list) -> MagicMock:
        bd = MagicMock()
        bd.ball_data = json.dumps(ball_list)
        return bd

    def _make_pose_detection(self, pose_data: list) -> MagicMock:
        pd = MagicMock()
        pd.pose_data = json.dumps(pose_data)
        return pd

    def test_laterality_computed_at_peak_frame(self) -> None:
        """Laterality uses ball_x at peak frame and shoulder center from pose at start."""
        ball_list = [
            {"ball_x": 700.0, "ball_y": 50.0, "timestamp_ms": 500.0},
        ]
        # Pose at frame 0 (start=0.0, fps=30 → frame 0)
        pose_data = [
            {
                "left_shoulder": [600.0, 200.0],
                "right_shoulder": [680.0, 200.0],
                "left_ankle": [610.0, 600.0],
                "right_ankle": [670.0, 600.0],
            }
        ]
        sw = self._make_serve_window()
        video = self._make_video()
        bd = self._make_ball_detection(ball_list)
        pd = self._make_pose_detection(pose_data)

        result = _compute_toss_metrics(sw, bd, video, pd)
        assert result is not None
        assert result["toss_laterality"] is not None
        # body_center_x = (600+680)/2 = 640
        # player_height_px = ankle_y - shoulder_y = 600 - 200 = 400
        # laterality = (700 - 640) / 400 = 0.15
        assert result["toss_laterality"] == 0.15

    def test_laterality_positive_when_ball_right_of_center(self) -> None:
        """Ball right of body center should produce positive laterality."""
        ball_list = [
            {"ball_x": 800.0, "ball_y": 50.0, "timestamp_ms": 500.0},
        ]
        pose_data = [
            {
                "left_shoulder": [600.0, 200.0],
                "right_shoulder": [680.0, 200.0],
                "left_ankle": [610.0, 600.0],
                "right_ankle": [670.0, 600.0],
            }
        ]
        result = _compute_toss_metrics(
            self._make_serve_window(),
            self._make_ball_detection(ball_list),
            self._make_video(),
            self._make_pose_detection(pose_data),
        )
        assert result is not None
        assert result["toss_laterality"] is not None
        assert result["toss_laterality"] > 0

    def test_laterality_none_when_ball_x_missing(self) -> None:
        """toss_laterality should be None when ball_x is missing."""
        ball_list = [
            {"ball_y": 50.0, "timestamp_ms": 500.0},  # no ball_x
        ]
        pose_data = [
            {
                "left_shoulder": [600.0, 200.0],
                "right_shoulder": [680.0, 200.0],
                "left_ankle": [610.0, 600.0],
                "right_ankle": [670.0, 600.0],
            }
        ]
        result = _compute_toss_metrics(
            self._make_serve_window(),
            self._make_ball_detection(ball_list),
            self._make_video(),
            self._make_pose_detection(pose_data),
        )
        assert result is not None
        assert result["toss_laterality"] is None

    def test_laterality_none_when_pose_missing(self) -> None:
        """toss_laterality should be None when no pose detection is provided."""
        ball_list = [
            {"ball_x": 700.0, "ball_y": 50.0, "timestamp_ms": 500.0},
        ]
        result = _compute_toss_metrics(
            self._make_serve_window(),
            self._make_ball_detection(ball_list),
            self._make_video(),
            None,  # no pose detection
        )
        assert result is not None
        assert result["toss_laterality"] is None
