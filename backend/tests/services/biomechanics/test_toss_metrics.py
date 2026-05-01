"""Tests for toss metrics computation (toss_peak_height, toss_laterality)."""

import json
from unittest.mock import MagicMock

from app.services.biomechanics.toss_metrics import _compute_toss_metrics


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

    # --- ground ball gate tests ---

    def test_ground_ball_nulls_all_ball_metrics(self) -> None:
        """When peak is at/below shoulder level (ground ball), all ball metrics are None."""
        # ball_y=300 is BELOW shoulder_y=200 (higher y = lower in frame),
        # so toss_peak_height would be <= 0 — ground ball detected
        ball_list = [
            {"ball_x": 700.0, "ball_y": 300.0, "timestamp_ms": 500.0},
            {"ball_x": 700.0, "ball_y": 350.0, "timestamp_ms": 1000.0},
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
            self._make_serve_window(contact=1.0),
            self._make_ball_detection(ball_list),
            self._make_video(),
            self._make_pose_detection(pose_data),
        )
        assert result is not None
        assert result["toss_peak_height"] is None
        assert result["toss_laterality"] is None
        assert result["toss_drop"] is None

    # --- toss_drop tests ---

    def test_toss_drop_computed_when_ball_tracked_at_contact(self) -> None:
        """toss_drop should be a positive float when ball is tracked near contact."""
        # Peak at 500ms (ball_y=50), contact at 1.0s, ball near contact at 1000ms (ball_y=150)
        ball_list = [
            {"ball_x": 700.0, "ball_y": 50.0, "timestamp_ms": 500.0},
            {"ball_x": 700.0, "ball_y": 150.0, "timestamp_ms": 1000.0},
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
            self._make_serve_window(contact=1.0),
            self._make_ball_detection(ball_list),
            self._make_video(),
            self._make_pose_detection(pose_data),
        )
        assert result is not None
        assert result["toss_drop"] is not None
        # player_height_px = 600 - 200 = 400
        # toss_drop = (150 - 50) / 400 = 0.25
        assert result["toss_drop"] == 0.25

    def test_toss_drop_none_when_no_ball_near_contact(self) -> None:
        """toss_drop should be None when no ball frame is within 67ms tolerance of contact."""
        # Peak at 500ms, contact at 1.0s, but nearest ball frame is at 800ms (200ms away)
        ball_list = [
            {"ball_x": 700.0, "ball_y": 50.0, "timestamp_ms": 500.0},
            {"ball_x": 700.0, "ball_y": 120.0, "timestamp_ms": 800.0},
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
            self._make_serve_window(contact=1.0),
            self._make_ball_detection(ball_list),
            self._make_video(),
            self._make_pose_detection(pose_data),
        )
        assert result is not None
        assert result["toss_drop"] is None

    def test_toss_drop_none_when_contact_timestamp_missing(self) -> None:
        """toss_drop should be None when contact_timestamp is None."""
        ball_list = [
            {"ball_x": 700.0, "ball_y": 50.0, "timestamp_ms": 500.0},
            {"ball_x": 700.0, "ball_y": 150.0, "timestamp_ms": 1000.0},
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
            self._make_serve_window(contact=None),
            self._make_ball_detection(ball_list),
            self._make_video(),
            self._make_pose_detection(pose_data),
        )
        assert result is not None
        assert result["toss_drop"] is None
