"""Contract tests for serve window API routes.

Covers the split endpoint (new) and resize/shift validation via PUT.
Uses TestClient with mocked DB and auth — no real DB needed.
"""

from datetime import datetime
from unittest.mock import MagicMock, patch

import pytest
from fastapi.testclient import TestClient

from app.core.database import get_db
from app.dependencies.auth import get_current_user
from app.main import app
from app.models.serve_window import ServeWindow


def _make_mock_window(
    id: int = 1,
    video_id: int = 10,
    start: float = 0.0,
    end: float = 5.0,
    contact: float | None = None,
    contact_source: str | None = None,
    is_active: bool = True,
    parent_window_id: int | None = None,
    status: str = "accepted",
) -> MagicMock:
    """Return a mock ServeWindow ORM object."""
    w = MagicMock(spec=ServeWindow)
    w.id = id
    w.video_id = video_id
    w.user_id = "00000000-0000-0000-0000-000000000000"
    w.player_id = 1
    w.start_timestamp = start
    w.end_timestamp = end
    w.contact_timestamp = contact
    w.contact_source = contact_source
    w.court_side = None
    w.serve_number = None
    w.serve_subtype = None
    w.in_out = None
    w.source = "manual"
    w.status = status
    w.confidence = None
    w.model_version = None
    w.is_active = is_active
    w.parent_window_id = parent_window_id
    w.created_at = datetime(2026, 2, 25, 12, 0, 0)
    return w


def _make_mock_video(is_demo: bool = False) -> MagicMock:
    v = MagicMock()
    v.id = 10
    v.user_id = "00000000-0000-0000-0000-000000000000"
    v.is_demo = is_demo
    return v


@pytest.fixture
def serve_window_client():
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


# ---------------------------------------------------------------------------
# Split endpoint — POST /v0/serve-windows/{id}/split
# ---------------------------------------------------------------------------


class TestSplitServeWindow:
    @patch("app.api.routes.serve_windows.video_service")
    @patch("app.api.routes.serve_windows.serve_window_service")
    @patch("app.api.routes.serve_windows.serve_biomechanics_service")
    def test_split_returns_200_with_two_windows(
        self, mock_bio, mock_svc, mock_vid_svc, serve_window_client
    ):
        original = _make_mock_window(id=1, start=0.0, end=5.0)
        child_a = _make_mock_window(id=2, start=0.0, end=2.5, parent_window_id=1)
        child_b = _make_mock_window(id=3, start=2.5, end=5.0, parent_window_id=1)

        mock_svc.get_serve_window_by_id.return_value = original
        mock_vid_svc.get_video_by_id.return_value = _make_mock_video()
        mock_svc.split_serve_window.return_value = (child_a, child_b)
        mock_bio.compute_analysis.return_value = None

        response = serve_window_client.post(
            "/v0/serve-windows/1/split", json={"split_at": 2.5}
        )

        assert response.status_code == 200
        data = response.json()
        assert "window_a" in data
        assert "window_b" in data
        assert data["window_a"]["id"] == 2
        assert data["window_b"]["id"] == 3

    @patch("app.api.routes.serve_windows.video_service")
    @patch("app.api.routes.serve_windows.serve_window_service")
    @patch("app.api.routes.serve_windows.serve_biomechanics_service")
    def test_split_response_shape(
        self, mock_bio, mock_svc, mock_vid_svc, serve_window_client
    ):
        original = _make_mock_window(id=1, start=0.0, end=5.0)
        child_a = _make_mock_window(id=2, start=0.0, end=2.5, parent_window_id=1)
        child_b = _make_mock_window(id=3, start=2.5, end=5.0, parent_window_id=1)

        mock_svc.get_serve_window_by_id.return_value = original
        mock_vid_svc.get_video_by_id.return_value = _make_mock_video()
        mock_svc.split_serve_window.return_value = (child_a, child_b)

        response = serve_window_client.post(
            "/v0/serve-windows/1/split", json={"split_at": 2.5}
        )

        data = response.json()
        for key in ("window_a", "window_b"):
            w = data[key]
            assert "id" in w
            assert "start_timestamp" in w
            assert "end_timestamp" in w
            assert "is_active" in w
            assert "parent_window_id" in w

    @patch("app.api.routes.serve_windows.video_service")
    @patch("app.api.routes.serve_windows.serve_window_service")
    def test_split_window_not_found_returns_404(
        self, mock_svc, mock_vid_svc, serve_window_client
    ):
        mock_svc.get_serve_window_by_id.side_effect = ValueError(
            "Serve window with ID 999 not found"
        )

        response = serve_window_client.post(
            "/v0/serve-windows/999/split", json={"split_at": 2.5}
        )

        assert response.status_code == 404

    @patch("app.api.routes.serve_windows.video_service")
    @patch("app.api.routes.serve_windows.serve_window_service")
    def test_split_invalid_split_at_returns_400(
        self, mock_svc, mock_vid_svc, serve_window_client
    ):
        original = _make_mock_window(id=1, start=0.0, end=5.0)
        mock_svc.get_serve_window_by_id.return_value = original
        mock_vid_svc.get_video_by_id.return_value = _make_mock_video()
        mock_svc.split_serve_window.side_effect = ValueError(
            "split_at must be strictly inside the window"
        )

        response = serve_window_client.post(
            "/v0/serve-windows/1/split", json={"split_at": 10.0}
        )

        assert response.status_code == 400

    @patch("app.api.routes.serve_windows.video_service")
    @patch("app.api.routes.serve_windows.serve_window_service")
    def test_split_zero_split_at_rejected_by_schema(
        self, mock_svc, mock_vid_svc, serve_window_client
    ):
        # split_at=0 violates gt=0 constraint at schema level
        response = serve_window_client.post(
            "/v0/serve-windows/1/split", json={"split_at": 0.0}
        )

        assert response.status_code == 422

    @patch("app.api.routes.serve_windows.video_service")
    @patch("app.api.routes.serve_windows.serve_window_service")
    def test_split_demo_video_forbidden(
        self, mock_svc, mock_vid_svc, serve_window_client
    ):
        original = _make_mock_window(id=1)
        mock_svc.get_serve_window_by_id.return_value = original
        mock_vid_svc.get_video_by_id.return_value = _make_mock_video(is_demo=True)

        response = serve_window_client.post(
            "/v0/serve-windows/1/split", json={"split_at": 2.5}
        )

        assert response.status_code == 403

    @patch("app.api.routes.serve_windows.video_service")
    @patch("app.api.routes.serve_windows.serve_window_service")
    def test_split_min_duration_first_half_returns_400(
        self, mock_svc, mock_vid_svc, serve_window_client
    ):
        original = _make_mock_window(id=1, start=0.0, end=5.0)
        mock_svc.get_serve_window_by_id.return_value = original
        mock_vid_svc.get_video_by_id.return_value = _make_mock_video()
        mock_svc.split_serve_window.side_effect = ValueError(
            "First half must be at least 0.5 seconds long"
        )

        response = serve_window_client.post(
            "/v0/serve-windows/1/split", json={"split_at": 0.1}
        )

        assert response.status_code == 400


# ---------------------------------------------------------------------------
# Update (resize/shift) endpoint — PUT /v0/serve-windows/{id}
# ---------------------------------------------------------------------------


class TestUpdateServeWindowValidation:
    @patch("app.api.routes.serve_windows.video_service")
    @patch("app.api.routes.serve_windows.serve_window_service")
    @patch("app.api.routes.serve_windows.serve_biomechanics_service")
    def test_update_returns_200(
        self, mock_bio, mock_svc, mock_vid_svc, serve_window_client
    ):
        original = _make_mock_window(id=1, start=0.0, end=5.0)
        updated = _make_mock_window(id=1, start=1.0, end=5.0, status="edited")
        mock_svc.get_serve_window_by_id.return_value = original
        mock_vid_svc.get_video_by_id.return_value = _make_mock_video()
        mock_svc.update_serve_window.return_value = updated
        mock_bio.compute_analysis.return_value = None

        response = serve_window_client.put(
            "/v0/serve-windows/1", json={"start_timestamp": 1.0}
        )

        assert response.status_code == 200

    @patch("app.api.routes.serve_windows.video_service")
    @patch("app.api.routes.serve_windows.serve_window_service")
    @patch("app.api.routes.serve_windows.serve_biomechanics_service")
    def test_update_response_includes_is_active(
        self, mock_bio, mock_svc, mock_vid_svc, serve_window_client
    ):
        original = _make_mock_window(id=1)
        updated = _make_mock_window(id=1, status="edited")
        mock_svc.get_serve_window_by_id.return_value = original
        mock_vid_svc.get_video_by_id.return_value = _make_mock_video()
        mock_svc.update_serve_window.return_value = updated

        response = serve_window_client.put(
            "/v0/serve-windows/1", json={"court_side": "deuce"}
        )

        data = response.json()
        assert "is_active" in data
        assert "parent_window_id" in data

    @patch("app.api.routes.serve_windows.video_service")
    @patch("app.api.routes.serve_windows.serve_window_service")
    def test_update_overlap_returns_400(
        self, mock_svc, mock_vid_svc, serve_window_client
    ):
        original = _make_mock_window(id=1)
        mock_svc.get_serve_window_by_id.return_value = original
        mock_vid_svc.get_video_by_id.return_value = _make_mock_video()
        mock_svc.update_serve_window.side_effect = ValueError(
            "Updated window would overlap with an existing serve window"
        )

        response = serve_window_client.put(
            "/v0/serve-windows/1",
            json={"start_timestamp": 0.0, "end_timestamp": 10.0},
        )

        assert response.status_code == 400

    @patch("app.api.routes.serve_windows.video_service")
    @patch("app.api.routes.serve_windows.serve_window_service")
    def test_update_too_short_returns_400(
        self, mock_svc, mock_vid_svc, serve_window_client
    ):
        original = _make_mock_window(id=1)
        mock_svc.get_serve_window_by_id.return_value = original
        mock_vid_svc.get_video_by_id.return_value = _make_mock_video()
        mock_svc.update_serve_window.side_effect = ValueError(
            "Window must be at least 0.5 seconds long"
        )

        response = serve_window_client.put(
            "/v0/serve-windows/1",
            json={"start_timestamp": 0.0, "end_timestamp": 0.1},
        )

        assert response.status_code == 400
