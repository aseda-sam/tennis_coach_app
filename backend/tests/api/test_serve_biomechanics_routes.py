"""Contract tests for serve biomechanics API routes.

Tests response status codes and shapes. Uses TestClient directly
with mock DB and auth to avoid needing a real database.
"""

import json
from datetime import datetime
from unittest.mock import MagicMock, patch

import pytest
from fastapi.testclient import TestClient

from app.core.database import get_db
from app.dependencies.auth import get_current_user
from app.main import app
from app.models.serve_biomechanics_report import ServeBiomechanicsReport


def _make_mock_report(serve_window_id: int = 1) -> ServeBiomechanicsReport:
    """Create a mock ServeBiomechanicsReport DB model."""
    report = MagicMock(spec=ServeBiomechanicsReport)
    report.id = 1
    report.serve_window_id = serve_window_id
    report.user_id = "00000000-0000-0000-0000-000000000000"
    report.player_id = 1
    report.analysis_version = "phase-metrics-v1"
    report.created_at = datetime(2026, 2, 16, 12, 0, 0)
    report.phase_segmentation_json = json.dumps(
        {
            "phases": [
                {
                    "phase": "toss_and_load",
                    "start_timestamp": 0.0,
                    "end_timestamp": 0.97,
                    "start_frame": 0,
                    "end_frame": 29,
                    "confidence": 0.8,
                    "detected": True,
                },
                {
                    "phase": "acceleration",
                    "start_timestamp": 0.97,
                    "end_timestamp": 1.3,
                    "start_frame": 29,
                    "end_frame": 39,
                    "confidence": 0.7,
                    "detected": True,
                },
                {
                    "phase": "follow_through",
                    "start_timestamp": 1.3,
                    "end_timestamp": 2.0,
                    "start_frame": 39,
                    "end_frame": 59,
                    "confidence": 0.7,
                    "detected": True,
                },
            ],
            "moments": [
                {
                    "moment": "ball_release",
                    "timestamp": 0.2,
                    "frame": 6,
                    "confidence": 0.7,
                    "detected": True,
                    "method": "toss_wrist_above_shoulder",
                },
                {
                    "moment": "ball_impact",
                    "timestamp": 1.3,
                    "frame": 39,
                    "confidence": 0.7,
                    "detected": True,
                    "method": "user_tagged",
                },
            ],
            "analysis_version": "phase-seg-v5",
            "total_phases_detected": 3,
            "total_phases_possible": 3,
            "detection_meta": {
                "ktps": {
                    "ball_release": {
                        "frame": 6,
                        "method": "toss_wrist_above_shoulder",
                        "search_window": [0, 24],
                    },
                    "trophy_position": {
                        "frame": 21,
                        "method": "peak_wrist_height_with_knee_validation",
                        "search_window": [6, 42],
                    },
                    "racket_low_point": {
                        "frame": 29,
                        "method": "max_dominant_wrist_y",
                        "search_window": [21, 39],
                    },
                    "ball_impact": {
                        "frame": 39,
                        "method": "user_tagged",
                    },
                },
                "feature_curves": {
                    "max_wrist_height": [0.1, 0.2, 0.3],
                    "knee_hip_ratio": [0.5, 0.6, 0.7],
                    "max_wrist_velocity": [0.0, 50.0, 100.0],
                },
                "fps": 30.0,
                "total_frames": 60,
            },
        }
    )
    report.metrics = {
        "toss_and_load": {
            "knee_flexion_min_deg": 95.0,
            "toss_peak_height": 1.8,
            "toss_laterality": 0.15,
        },
    }
    return report


@pytest.fixture
def biomechanics_client():
    """TestClient with mocked DB and auth — no real DB needed."""
    mock_db = MagicMock()

    def override_get_db():
        yield mock_db

    async def mock_get_current_user():
        return {
            "id": "00000000-0000-0000-0000-000000000000",
            "email": "test@example.com",
            "user_metadata": {},
        }

    app.dependency_overrides[get_db] = override_get_db
    app.dependency_overrides[get_current_user] = mock_get_current_user

    with TestClient(app) as client:
        yield client

    app.dependency_overrides.clear()


class TestGetServeBiomechanics:
    @patch("app.api.routes.serve_biomechanics.serve_biomechanics_service")
    def test_returns_200(self, mock_service, biomechanics_client):
        mock_service.get_or_compute_analysis.return_value = _make_mock_report()
        response = biomechanics_client.get("/v0/serve-windows/1/biomechanics")
        assert response.status_code == 200

    @patch("app.api.routes.serve_biomechanics.serve_biomechanics_service")
    def test_response_shape(self, mock_service, biomechanics_client):
        """Response must include all fields expected by UI."""
        mock_service.get_or_compute_analysis.return_value = _make_mock_report()
        response = biomechanics_client.get("/v0/serve-windows/1/biomechanics")
        data = response.json()
        assert "id" in data
        assert "serve_window_id" in data
        assert "phase_segmentation" in data
        assert "moments" in data
        assert "metrics" in data
        assert "analysis_version" in data
        assert "created_at" in data
        assert "overall_score" not in data
        assert "overall_rating" not in data
        assert "top_priority" not in data
        assert "phase_scores" not in data

    @patch("app.api.routes.serve_biomechanics.serve_biomechanics_service")
    def test_phase_segmentation_shape(self, mock_service, biomechanics_client):
        mock_service.get_or_compute_analysis.return_value = _make_mock_report()
        response = biomechanics_client.get("/v0/serve-windows/1/biomechanics")
        data = response.json()
        seg = data["phase_segmentation"]
        assert isinstance(seg, list)
        if seg:
            pw = seg[0]
            assert "phase" in pw
            assert "phase_label" in pw
            assert "start_timestamp" in pw
            assert "end_timestamp" in pw
            assert "confidence" in pw
            assert "detected" in pw

    @patch("app.api.routes.serve_biomechanics.serve_biomechanics_service")
    def test_metrics_shape(self, mock_service, biomechanics_client):
        mock_service.get_or_compute_analysis.return_value = _make_mock_report()
        response = biomechanics_client.get("/v0/serve-windows/1/biomechanics")
        data = response.json()
        metrics = data["metrics"]
        assert isinstance(metrics, list)
        if metrics:
            m = metrics[0]
            assert "metric_name" in m
            assert "value" in m
            assert "unit" in m
            assert "phase" in m
            assert "rating" not in m
            assert "feedback_text" not in m

    @patch("app.api.routes.serve_biomechanics.serve_biomechanics_service")
    def test_detection_meta_in_response(self, mock_service, biomechanics_client):
        """detection_meta should be passed through from phase_segmentation_json."""
        mock_service.get_or_compute_analysis.return_value = _make_mock_report()
        response = biomechanics_client.get("/v0/serve-windows/1/biomechanics")
        data = response.json()
        assert "detection_meta" in data
        meta = data["detection_meta"]
        assert meta is not None
        assert "ktps" in meta
        assert "feature_curves" in meta
        assert "fps" in meta

    @patch("app.api.routes.serve_biomechanics.serve_biomechanics_service")
    def test_moments_in_response(self, mock_service, biomechanics_client):
        """Response should include moments list with correct structure."""
        mock_service.get_or_compute_analysis.return_value = _make_mock_report()
        response = biomechanics_client.get("/v0/serve-windows/1/biomechanics")
        data = response.json()
        moments = data["moments"]
        assert isinstance(moments, list)
        assert len(moments) == 2
        mm = moments[0]
        assert "moment" in mm
        assert "moment_label" in mm
        assert "timestamp" in mm
        assert "confidence" in mm
        assert "detected" in mm

    @patch("app.api.routes.serve_biomechanics.serve_biomechanics_service")
    def test_not_found_returns_404(self, mock_service, biomechanics_client):
        mock_service.get_or_compute_analysis.side_effect = ValueError("Not found")
        response = biomechanics_client.get("/v0/serve-windows/999/biomechanics")
        assert response.status_code == 404


class TestComputeServeBiomechanics:
    @patch("app.api.routes.serve_biomechanics.serve_biomechanics_service")
    def test_returns_201(self, mock_service, biomechanics_client):
        mock_service.compute_analysis.return_value = _make_mock_report()
        response = biomechanics_client.post("/v0/serve-windows/1/biomechanics/compute")
        assert response.status_code == 201

    @patch("app.api.routes.serve_biomechanics.serve_biomechanics_service")
    def test_response_has_id(self, mock_service, biomechanics_client):
        mock_service.compute_analysis.return_value = _make_mock_report()
        response = biomechanics_client.post("/v0/serve-windows/1/biomechanics/compute")
        data = response.json()
        assert "id" in data
        assert data["id"] == 1


class TestGetServeWindowFrame:
    """Contract tests for GET /serve-windows/{id}/frame."""

    @patch("app.api.routes.serve_biomechanics.extract_ktp_frame")
    def test_returns_200_jpeg(self, mock_extract, biomechanics_client):
        # Minimal JPEG bytes (not a valid image, but enough for contract test)
        mock_extract.return_value = b"\xff\xd8\xff\xe0fake-jpeg-bytes"
        response = biomechanics_client.get(
            "/v0/serve-windows/1/frame?ktp=trophy_position"
        )
        assert response.status_code == 200
        assert response.headers["content-type"] == "image/jpeg"
        assert "cache-control" in response.headers
        assert response.content == b"\xff\xd8\xff\xe0fake-jpeg-bytes"

    @patch("app.api.routes.serve_biomechanics.extract_ktp_frame")
    def test_missing_ktp_returns_404(self, mock_extract, biomechanics_client):
        mock_extract.side_effect = ValueError("KTP 'bad_ktp' not found")
        response = biomechanics_client.get("/v0/serve-windows/1/frame?ktp=bad_ktp")
        assert response.status_code == 404

    @patch("app.api.routes.serve_biomechanics.extract_ktp_frame")
    def test_missing_serve_window_returns_404(self, mock_extract, biomechanics_client):
        mock_extract.side_effect = ValueError("No biomechanics report")
        response = biomechanics_client.get(
            "/v0/serve-windows/999/frame?ktp=trophy_position"
        )
        assert response.status_code == 404

    def test_missing_both_params_returns_400(self, biomechanics_client):
        """Either ktp or timestamp is required; omitting both returns 400."""
        response = biomechanics_client.get("/v0/serve-windows/1/frame")
        assert response.status_code == 400


def _make_mock_report_with_video(serve_window_id: int = 1) -> ServeBiomechanicsReport:
    """Create a mock report with serve_window.video populated for history tests."""
    report = _make_mock_report(serve_window_id)

    mock_video = MagicMock()
    mock_video.id = 10
    mock_video.filename = "test_serve.mp4"

    mock_sw = MagicMock()
    mock_sw.video = mock_video
    report.serve_window = mock_sw

    return report


class TestGetPlayerBiomechanicsHistory:
    @patch("app.api.routes.serve_biomechanics.require_player_access")
    @patch("app.api.routes.serve_biomechanics.get_player_by_id")
    @patch("app.api.routes.serve_biomechanics.serve_biomechanics_service")
    def test_returns_200_list(
        self, mock_service, mock_get_player, mock_require_access, biomechanics_client
    ):
        mock_get_player.return_value = MagicMock(id=1)
        mock_service.get_player_history.return_value = [_make_mock_report_with_video()]
        response = biomechanics_client.get("/v0/players/1/biomechanics/history")
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        assert len(data) == 1

    @patch("app.api.routes.serve_biomechanics.require_player_access")
    @patch("app.api.routes.serve_biomechanics.get_player_by_id")
    @patch("app.api.routes.serve_biomechanics.serve_biomechanics_service")
    def test_empty_history(
        self, mock_service, mock_get_player, mock_require_access, biomechanics_client
    ):
        mock_get_player.return_value = MagicMock(id=1)
        mock_service.get_player_history.return_value = []
        response = biomechanics_client.get("/v0/players/1/biomechanics/history")
        assert response.status_code == 200
        assert response.json() == []

    @patch("app.api.routes.serve_biomechanics.require_player_access")
    @patch("app.api.routes.serve_biomechanics.get_player_by_id")
    @patch("app.api.routes.serve_biomechanics.serve_biomechanics_service")
    def test_history_includes_video_context(
        self, mock_service, mock_get_player, mock_require_access, biomechanics_client
    ):
        """History response should include video_id and video_filename."""
        mock_get_player.return_value = MagicMock(id=1)
        mock_service.get_player_history.return_value = [_make_mock_report_with_video()]
        response = biomechanics_client.get("/v0/players/1/biomechanics/history")
        data = response.json()
        assert data[0]["video_id"] == 10
        assert data[0]["video_filename"] == "test_serve.mp4"
