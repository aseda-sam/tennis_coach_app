"""
Unit tests for serve_analysis_service module.

Tests the keypoint extraction helper and pose timestamp lookup functions,
ensuring compatibility with both old and new pose data formats.
"""

import json
from unittest.mock import MagicMock

from app.services.serve_analysis_service import (
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
