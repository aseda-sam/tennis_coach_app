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
                    "phase": "contact",
                    "start_timestamp": 1.0,
                    "end_timestamp": 1.2,
                    "start_frame": 30,
                    "end_frame": 36,
                    "confidence": 1.0,
                    "detected": True,
                }
            ],
            "analysis_version": "phase-seg-v1",
            "total_phases_detected": 1,
            "total_phases_possible": 8,
        }
    )
    report.metrics_json = json.dumps(
        {
            "knee_flexion_min_deg": 95.0,
            "toss_peak_height": 1.8,
            "toss_laterality": 0.15,
        }
    )
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


class TestGetPlayerBiomechanicsHistory:
    @patch("app.api.routes.serve_biomechanics.serve_biomechanics_service")
    def test_returns_200_list(self, mock_service, biomechanics_client):
        mock_service.get_player_history.return_value = [_make_mock_report()]
        response = biomechanics_client.get("/v0/players/1/biomechanics/history")
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        assert len(data) == 1

    @patch("app.api.routes.serve_biomechanics.serve_biomechanics_service")
    def test_empty_history(self, mock_service, biomechanics_client):
        mock_service.get_player_history.return_value = []
        response = biomechanics_client.get("/v0/players/1/biomechanics/history")
        assert response.status_code == 200
        assert response.json() == []
