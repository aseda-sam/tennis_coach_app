"""Integration tests for the serve biomechanics service pipeline.

Tests the full flow: phase segmentation → metrics → report creation.
Only DB access is mocked — biomechanics computations are real.
No scoring or coaching.
"""

import json
from unittest.mock import MagicMock, patch

import pytest

from app.services.biomechanics.serve_biomechanics_service import (
    ServeBiomechanicsService,
)
from tests.biomechanics_fixtures import _make_serve_sequence


def _mock_serve_window() -> MagicMock:
    sa = MagicMock()
    sa.id = 1
    sa.video_id = 10
    sa.player_id = 100
    sa.user_id = "user-1"
    sa.start_timestamp = 0.0
    sa.end_timestamp = 2.0
    sa.contact_timestamp = 1.33
    return sa


def _mock_video(camera_angle: str = "behind") -> MagicMock:
    v = MagicMock()
    v.id = 10
    v.fps = 30.0
    v.width = 1280
    v.height = 720
    v.camera_angle = camera_angle
    return v


def _mock_player(dominant_hand: str = "right") -> MagicMock:
    p = MagicMock()
    p.id = 100
    p.dominant_hand = dominant_hand
    return p


def _mock_pose_detection() -> MagicMock:
    pd = MagicMock()
    pd.id = 1
    return pd


class TestServeBiomechanicsServicePipeline:
    """Integration: full pipeline with real biomechanics, mocked DB."""

    @patch(
        "app.services.biomechanics.serve_biomechanics_service.get_pose_frames_in_window"
    )
    @patch(
        "app.services.biomechanics.serve_biomechanics_service._select_best_pose_detection"
    )
    def test_compute_produces_report(
        self, mock_best_pose: MagicMock, mock_get_frames: MagicMock
    ) -> None:
        mock_best_pose.return_value = _mock_pose_detection()
        mock_get_frames.return_value = _make_serve_sequence()

        db = MagicMock()
        db.query.return_value.filter.return_value.first.side_effect = [
            _mock_serve_window(),
            _mock_video(),
            _mock_player(),
        ]
        db.query.return_value.filter.return_value.order_by.return_value.first.return_value = None

        service = ServeBiomechanicsService()
        service.compute_analysis(db, serve_window_id=1, user_id="user-1")

        db.add.assert_called_once()
        db.commit.assert_called_once()

        saved = db.add.call_args[0][0]
        assert saved.serve_window_id == 1
        assert saved.user_id == "user-1"
        assert saved.phase_segmentation_json is not None
        assert saved.metrics is not None
        assert saved.analysis_version == "phase-metrics-v8"

    @patch(
        "app.services.biomechanics.serve_biomechanics_service.get_pose_frames_in_window"
    )
    @patch(
        "app.services.biomechanics.serve_biomechanics_service._select_best_pose_detection"
    )
    def test_report_has_phase_segmentation(
        self, mock_best_pose: MagicMock, mock_get_frames: MagicMock
    ) -> None:
        mock_best_pose.return_value = _mock_pose_detection()
        mock_get_frames.return_value = _make_serve_sequence()

        db = MagicMock()
        db.query.return_value.filter.return_value.first.side_effect = [
            _mock_serve_window(),
            _mock_video(),
            _mock_player(),
        ]
        db.query.return_value.filter.return_value.order_by.return_value.first.return_value = None

        service = ServeBiomechanicsService()
        service.compute_analysis(db, serve_window_id=1, user_id="user-1")

        saved = db.add.call_args[0][0]
        seg = json.loads(saved.phase_segmentation_json)
        assert "phases" in seg
        assert len(seg["phases"]) > 0
        for pw in seg["phases"]:
            assert "phase" in pw
            assert "start_timestamp" in pw
            assert "end_timestamp" in pw
            assert pw["start_timestamp"] <= pw["end_timestamp"]

    @patch(
        "app.services.biomechanics.serve_biomechanics_service.get_pose_frames_in_window"
    )
    @patch(
        "app.services.biomechanics.serve_biomechanics_service._select_best_pose_detection"
    )
    def test_report_has_metrics(
        self, mock_best_pose: MagicMock, mock_get_frames: MagicMock
    ) -> None:
        mock_best_pose.return_value = _mock_pose_detection()
        mock_get_frames.return_value = _make_serve_sequence()

        db = MagicMock()
        db.query.return_value.filter.return_value.first.side_effect = [
            _mock_serve_window(),
            _mock_video(),
            _mock_player(),
        ]
        db.query.return_value.filter.return_value.order_by.return_value.first.return_value = None

        service = ServeBiomechanicsService()
        service.compute_analysis(db, serve_window_id=1, user_id="user-1")

        saved = db.add.call_args[0][0]
        metrics = saved.metrics
        assert isinstance(metrics, dict)
        # Nested format: {phase: {metric_name: value}}
        assert "toss_and_load" in metrics
        assert "knee_flexion_min_deg" in metrics["toss_and_load"]

    def test_compute_raises_on_missing_serve(self) -> None:
        db = MagicMock()
        db.query.return_value.filter.return_value.first.return_value = None

        service = ServeBiomechanicsService()
        with pytest.raises(ValueError, match="not found"):
            service.compute_analysis(db, serve_window_id=999, user_id="user-1")

    @patch(
        "app.services.biomechanics.serve_biomechanics_service._get_best_ball_detection"
    )
    @patch(
        "app.services.biomechanics.serve_biomechanics_service.get_pose_frames_in_window"
    )
    @patch(
        "app.services.biomechanics.serve_biomechanics_service._select_best_pose_detection"
    )
    def test_laterality_excluded_for_profile_camera(
        self,
        mock_best_pose: MagicMock,
        mock_get_frames: MagicMock,
        mock_ball_det: MagicMock,
    ) -> None:
        """toss_laterality should be null when camera_angle is 'profile'."""
        mock_best_pose.return_value = _mock_pose_detection()
        mock_get_frames.return_value = _make_serve_sequence()

        # Return toss metrics including laterality
        mock_ball_det.return_value = MagicMock()

        db = MagicMock()
        video = _mock_video(camera_angle="profile")
        db.query.return_value.filter.return_value.first.side_effect = [
            _mock_serve_window(),
            video,
            _mock_player(),
        ]
        db.query.return_value.filter.return_value.order_by.return_value.first.return_value = None

        with patch(
            "app.services.biomechanics.serve_biomechanics_service._compute_toss_metrics"
        ) as mock_toss:
            mock_toss.return_value = {
                "toss_peak_height": 1.5,
                "toss_peak_timestamp": 0.5,
                "toss_laterality": 0.12,
            }
            service = ServeBiomechanicsService()
            service.compute_analysis(db, serve_window_id=1, user_id="user-1")

        saved = db.add.call_args[0][0]
        metrics = saved.metrics
        # Nested format: {phase: {metric_name: value}}
        assert metrics.get("toss_and_load", {}).get("toss_peak_height") == 1.5
        assert metrics.get("toss_and_load", {}).get("toss_laterality") is None

    @patch(
        "app.services.biomechanics.serve_biomechanics_service._select_best_pose_detection"
    )
    def test_compute_raises_on_no_pose_data(self, mock_best_pose: MagicMock) -> None:
        mock_best_pose.return_value = None

        db = MagicMock()
        db.query.return_value.filter.return_value.first.side_effect = [
            _mock_serve_window(),
            _mock_video(),
            _mock_player(),
        ]

        service = ServeBiomechanicsService()
        with pytest.raises(ValueError, match="No pose detection"):
            service.compute_analysis(db, serve_window_id=1, user_id="user-1")
