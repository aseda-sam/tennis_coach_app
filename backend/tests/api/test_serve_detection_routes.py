"""Contract tests for serve detection API routes.

Tests response status codes and shapes using a mock DB and auth client,
so no real database is required.
"""

from datetime import datetime
from unittest.mock import MagicMock, patch

import pytest
from fastapi.testclient import TestClient

from app.core.database import get_db
from app.dependencies.auth import get_current_user
from app.main import app
from app.models.video import Video


def _mock_video(user_id: str = "00000000-0000-0000-0000-000000000000") -> MagicMock:
    video = MagicMock(spec=Video)
    video.id = 1
    video.user_id = user_id
    video.is_demo = False
    video.is_active_demo = False
    return video


def _mock_proposal(video_id: int = 1) -> MagicMock:
    proposal = MagicMock()
    proposal.id = 1
    proposal.video_id = video_id
    proposal.start_timestamp = 0.5
    proposal.end_timestamp = 2.5
    proposal.model_version = "heuristic-v1"
    proposal.confidence = 0.85
    proposal.detection_features = None
    proposal.status = "pending"
    proposal.created_at = datetime(2026, 2, 21, 12, 0, 0)
    proposal.reviewed_at = None
    return proposal


@pytest.fixture
def detection_client():
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

    try:
        with (
            patch("app.main.create_tables_if_not_exists"),
            patch("app.main.start_rq_worker", return_value=None),
            TestClient(app) as client,
        ):
            yield client
    finally:
        app.dependency_overrides.clear()


class TestProposeServeWindows:
    """POST /videos/{video_id}/serve-detection/propose → 201."""

    @patch("app.api.routes.serve_detection.proposal_service")
    @patch("app.api.routes.serve_detection.video_service")
    def test_propose_returns_201(self, mock_vs, mock_ps, detection_client):
        mock_vs.get_video_by_id.return_value = _mock_video()
        mock_ps.generate_proposals.return_value = [_mock_proposal()]

        response = detection_client.post("/v0/videos/1/serve-detection/propose")
        assert response.status_code == 201

    @patch("app.api.routes.serve_detection.proposal_service")
    @patch("app.api.routes.serve_detection.video_service")
    def test_propose_response_shape(self, mock_vs, mock_ps, detection_client):
        mock_vs.get_video_by_id.return_value = _mock_video()
        mock_ps.generate_proposals.return_value = [_mock_proposal()]

        response = detection_client.post("/v0/videos/1/serve-detection/propose")
        data = response.json()
        assert "video_id" in data
        assert "proposals" in data
        assert "count" in data
        assert data["count"] == 1

    @patch("app.api.routes.serve_detection.proposal_service")
    @patch("app.api.routes.serve_detection.video_service")
    def test_propose_empty_result(self, mock_vs, mock_ps, detection_client):
        mock_vs.get_video_by_id.return_value = _mock_video()
        mock_ps.generate_proposals.return_value = []

        response = detection_client.post("/v0/videos/1/serve-detection/propose")
        assert response.status_code == 201
        assert response.json()["count"] == 0

    @patch("app.api.routes.serve_detection.video_service")
    def test_propose_video_not_found_returns_404(self, mock_vs, detection_client):
        mock_vs.get_video_by_id.return_value = None

        response = detection_client.post("/v0/videos/999/serve-detection/propose")
        assert response.status_code == 404


class TestDetectionStatusEndpoint:
    """GET /videos/{video_id}/serve-detection/status → 200."""

    @patch("app.api.routes.serve_detection.proposal_service")
    @patch("app.api.routes.serve_detection.video_service")
    def test_status_returns_200(self, mock_vs, mock_ps, detection_client):
        mock_vs.get_video_by_id.return_value = _mock_video()
        mock_ps.check_existing_proposals_or_attempts.return_value = {
            "pending_proposals": 0,
            "reviewed_proposals": 0,
            "serve_windows": 0,
        }

        response = detection_client.get("/v0/videos/1/serve-detection/status")
        assert response.status_code == 200

    @patch("app.api.routes.serve_detection.proposal_service")
    @patch("app.api.routes.serve_detection.video_service")
    def test_status_response_shape(self, mock_vs, mock_ps, detection_client):
        mock_vs.get_video_by_id.return_value = _mock_video()
        mock_ps.check_existing_proposals_or_attempts.return_value = {
            "pending_proposals": 2,
            "reviewed_proposals": 1,
            "serve_windows": 0,
        }

        response = detection_client.get("/v0/videos/1/serve-detection/status")
        data = response.json()
        assert "video_id" in data
        assert "pending_proposals" in data
        assert "reviewed_proposals" in data
        assert "serve_windows" in data
        assert "can_run_detection" in data
