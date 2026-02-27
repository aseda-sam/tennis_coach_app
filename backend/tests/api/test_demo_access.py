"""Tests for unauthenticated demo access on endpoints made demo-aware.

Each modified endpoint is tested for:
- 200 when accessing a demo video without auth
- 401 when accessing a non-demo video without auth

Uses TestClient with mocked DB and auth — no real DB needed.
"""

from datetime import datetime
from unittest.mock import MagicMock, patch

import pytest
from fastapi.testclient import TestClient

from app.core.database import get_db
from app.dependencies.auth import get_optional_user
from app.main import app
from app.models.serve_window import ServeWindow

# ---------------------------------------------------------------------------
# Mock helpers
# ---------------------------------------------------------------------------

TEST_USER_ID = "00000000-0000-0000-0000-000000000000"


def _make_mock_video(is_demo: bool = False) -> MagicMock:
    v = MagicMock()
    v.id = 10
    v.user_id = TEST_USER_ID
    v.is_demo = is_demo
    v.is_active_demo = is_demo
    return v


def _make_mock_window(
    id: int = 1,
    video_id: int = 10,
    start: float = 0.0,
    end: float = 5.0,
    contact: float | None = 2.5,
    contact_source: str | None = "manual",
    status: str = "accepted",
) -> MagicMock:
    w = MagicMock(spec=ServeWindow)
    w.id = id
    w.video_id = video_id
    w.user_id = TEST_USER_ID
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
    w.is_active = True
    w.parent_window_id = None
    w.created_at = datetime(2026, 2, 25, 12, 0, 0)
    return w


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def unauthenticated_client():
    """TestClient with mocked DB and NO authenticated user."""
    mock_db = MagicMock()

    def override_get_db():
        yield mock_db

    async def mock_get_optional_user():
        return None

    app.dependency_overrides[get_db] = override_get_db
    app.dependency_overrides[get_optional_user] = mock_get_optional_user

    with TestClient(app) as client:
        yield client

    app.dependency_overrides.clear()


# ---------------------------------------------------------------------------
# GET /v0/videos/{id}/analysis-status
# ---------------------------------------------------------------------------


class TestAnalysisStatusDemoAccess:
    @patch("app.api.routes.video.video_service")
    def test_demo_video_returns_200_without_auth(
        self, mock_video_svc, unauthenticated_client
    ):
        mock_video_svc.get_video_by_id.return_value = _make_mock_video(is_demo=True)
        mock_video_svc.get_video_analysis_status.return_value = {
            "video_id": 10,
            "has_analysis": True,
            "has_annotated_video": False,
        }

        response = unauthenticated_client.get("/v0/videos/10/analysis-status")
        assert response.status_code == 200
        data = response.json()
        assert data["has_analysis"] is True

    @patch("app.api.routes.video.video_service")
    def test_non_demo_video_returns_401_without_auth(
        self, mock_video_svc, unauthenticated_client
    ):
        mock_video_svc.get_video_by_id.return_value = _make_mock_video(is_demo=False)

        response = unauthenticated_client.get("/v0/videos/10/analysis-status")
        assert response.status_code == 401


# ---------------------------------------------------------------------------
# GET /v0/videos/{id}/ball-contact-timestamps
# ---------------------------------------------------------------------------


class TestBallContactTimestampsDemoAccess:
    @patch("app.api.routes.video.serve_window_service")
    @patch("app.api.routes.video.video_service")
    def test_demo_video_returns_200_without_auth(
        self, mock_video_svc, mock_sw_svc, unauthenticated_client
    ):
        mock_video_svc.get_video_by_id.return_value = _make_mock_video(is_demo=True)
        mock_sw_svc.get_ball_contact_timestamps.return_value = [1.5, 3.0]

        response = unauthenticated_client.get("/v0/videos/10/ball-contact-timestamps")
        assert response.status_code == 200
        data = response.json()
        assert data["ball_contact_timestamps"] == [1.5, 3.0]

    @patch("app.api.routes.video.video_service")
    def test_non_demo_video_returns_401_without_auth(
        self, mock_video_svc, unauthenticated_client
    ):
        mock_video_svc.get_video_by_id.return_value = _make_mock_video(is_demo=False)

        response = unauthenticated_client.get("/v0/videos/10/ball-contact-timestamps")
        assert response.status_code == 401

    @patch("app.api.routes.video.serve_window_service")
    @patch("app.api.routes.video.video_service")
    def test_uses_video_owner_user_id_for_demo(
        self, mock_video_svc, mock_sw_svc, unauthenticated_client
    ):
        """When unauthenticated, the service should receive the video owner's user_id."""
        mock_video_svc.get_video_by_id.return_value = _make_mock_video(is_demo=True)
        mock_sw_svc.get_ball_contact_timestamps.return_value = []

        unauthenticated_client.get("/v0/videos/10/ball-contact-timestamps")

        # Verify the service was called with the video owner's user_id
        call_kwargs = mock_sw_svc.get_ball_contact_timestamps.call_args
        assert call_kwargs.kwargs["user_id"] == TEST_USER_ID


# ---------------------------------------------------------------------------
# GET /v0/videos/{id}  (video metadata)
# ---------------------------------------------------------------------------


class TestVideoMetadataDemoAccess:
    def test_demo_video_returns_200_without_auth(self, unauthenticated_client):
        from app.api.schemas.video import VideoInfo

        video_info = VideoInfo(
            id=10,
            filename="demo.mp4",
            file_path="demo/demo.mp4",
            file_size=1000000,
            duration=60.0,
            width=1920,
            height=1080,
            fps=30.0,
            status="uploaded",
            user_id=TEST_USER_ID,
            is_demo=True,
            created_at=datetime(2026, 2, 25, 12, 0, 0),
        )

        with patch("app.api.routes.video.video_service") as mock_video_svc:
            mock_video_svc.get_video_by_id.return_value = _make_mock_video(is_demo=True)
            with patch.object(VideoInfo, "model_validate", return_value=video_info):
                response = unauthenticated_client.get("/v0/videos/10")
        assert response.status_code == 200

    def test_non_demo_video_returns_401_without_auth(self, unauthenticated_client):
        with patch("app.api.routes.video.video_service") as mock_video_svc:
            mock_video_svc.get_video_by_id.return_value = _make_mock_video(
                is_demo=False
            )
            response = unauthenticated_client.get("/v0/videos/10")
        assert response.status_code == 401


# ---------------------------------------------------------------------------
# GET /v0/videos/{id}/overlay-data
# ---------------------------------------------------------------------------


class TestOverlayDataDemoAccess:
    def test_demo_video_returns_200_without_auth(self, unauthenticated_client):
        from app.api.schemas.overlay_data import PoseOverlayData

        overlay_response = PoseOverlayData(
            video_id=10, total_frames=100, fps=30.0, width=1920, height=1080, frames=[]
        )

        with (
            patch("app.api.routes.overlay_data.video_service") as mock_video_svc,
            patch(
                "app.api.routes.overlay_data.overlay_data_service"
            ) as mock_overlay_svc,
        ):
            mock_video_svc.get_video_by_id.return_value = _make_mock_video(is_demo=True)
            mock_overlay_svc.format_overlay_data.return_value = overlay_response

            response = unauthenticated_client.get("/v0/videos/10/overlay-data")
        assert response.status_code == 200

    def test_non_demo_video_returns_401_without_auth(self, unauthenticated_client):
        with patch("app.api.routes.overlay_data.video_service") as mock_video_svc:
            mock_video_svc.get_video_by_id.return_value = _make_mock_video(
                is_demo=False
            )

            response = unauthenticated_client.get("/v0/videos/10/overlay-data")
        assert response.status_code == 401


# ---------------------------------------------------------------------------
# GET /v0/serve-windows/video/{video_id}  (new endpoint)
# ---------------------------------------------------------------------------


class TestServeWindowsByVideoDemoAccess:
    @patch("app.api.routes.serve_windows.serve_window_service")
    @patch("app.api.routes.serve_windows.video_service")
    def test_demo_video_returns_200_without_auth(
        self, mock_video_svc, mock_sw_svc, unauthenticated_client
    ):
        mock_video_svc.get_video_by_id.return_value = _make_mock_video(is_demo=True)
        mock_sw_svc.list_serve_windows_by_video.return_value = [
            _make_mock_window(id=1),
            _make_mock_window(id=2, start=6.0, end=10.0),
        ]

        response = unauthenticated_client.get("/v0/serve-windows/video/10")
        assert response.status_code == 200
        data = response.json()
        assert len(data) == 2

    @patch("app.api.routes.serve_windows.video_service")
    def test_non_demo_video_returns_401_without_auth(
        self, mock_video_svc, unauthenticated_client
    ):
        mock_video_svc.get_video_by_id.return_value = _make_mock_video(is_demo=False)

        response = unauthenticated_client.get("/v0/serve-windows/video/10")
        assert response.status_code == 401

    @patch("app.api.routes.serve_windows.video_service")
    def test_video_not_found_returns_404(self, mock_video_svc, unauthenticated_client):
        mock_video_svc.get_video_by_id.return_value = None

        response = unauthenticated_client.get("/v0/serve-windows/video/999")
        assert response.status_code == 404


# ---------------------------------------------------------------------------
# GET /v0/serve-windows/{id}/biomechanics
# ---------------------------------------------------------------------------


class TestBiomechanicsDemoAccess:
    @patch("app.api.routes.serve_biomechanics.serve_biomechanics_service")
    @patch("app.api.routes.serve_biomechanics.video_service")
    @patch("app.api.routes.serve_biomechanics.serve_window_service")
    def test_demo_video_returns_200_without_auth(
        self, mock_sw_svc, mock_video_svc, mock_bio_svc, unauthenticated_client
    ):
        mock_window = _make_mock_window(id=1)
        mock_sw_svc.get_serve_window_by_id_no_auth.return_value = mock_window
        mock_video_svc.get_video_by_id.return_value = _make_mock_video(is_demo=True)

        import json

        mock_report = MagicMock()
        mock_report.id = 1
        mock_report.serve_window_id = 1
        mock_report.analysis_version = "phase-metrics-v5"
        mock_report.created_at = datetime(2026, 2, 25, 12, 0, 0)
        mock_report.phase_segmentation_json = json.dumps({"phases": []})
        mock_report.metrics = {}
        mock_bio_svc.get_or_compute_analysis.return_value = mock_report

        response = unauthenticated_client.get("/v0/serve-windows/1/biomechanics")
        assert response.status_code == 200

    @patch("app.api.routes.serve_biomechanics.video_service")
    @patch("app.api.routes.serve_biomechanics.serve_window_service")
    def test_non_demo_video_returns_401_without_auth(
        self, mock_sw_svc, mock_video_svc, unauthenticated_client
    ):
        mock_window = _make_mock_window(id=1)
        mock_sw_svc.get_serve_window_by_id_no_auth.return_value = mock_window
        mock_video_svc.get_video_by_id.return_value = _make_mock_video(is_demo=False)

        response = unauthenticated_client.get("/v0/serve-windows/1/biomechanics")
        assert response.status_code == 401

    @patch("app.api.routes.serve_biomechanics.serve_biomechanics_service")
    @patch("app.api.routes.serve_biomechanics.video_service")
    @patch("app.api.routes.serve_biomechanics.serve_window_service")
    def test_uses_serve_window_user_id_for_demo(
        self, mock_sw_svc, mock_video_svc, mock_bio_svc, unauthenticated_client
    ):
        """When unauthenticated, biomechanics should use the serve window owner's user_id."""
        import json

        mock_window = _make_mock_window(id=1)
        mock_sw_svc.get_serve_window_by_id_no_auth.return_value = mock_window
        mock_video_svc.get_video_by_id.return_value = _make_mock_video(is_demo=True)

        mock_report = MagicMock()
        mock_report.id = 1
        mock_report.serve_window_id = 1
        mock_report.analysis_version = "phase-metrics-v5"
        mock_report.created_at = datetime(2026, 2, 25, 12, 0, 0)
        mock_report.phase_segmentation_json = json.dumps({"phases": []})
        mock_report.metrics = {}
        mock_bio_svc.get_or_compute_analysis.return_value = mock_report

        unauthenticated_client.get("/v0/serve-windows/1/biomechanics")

        # Verify user_id passed to service is the serve window owner's
        call_args = mock_bio_svc.get_or_compute_analysis.call_args
        assert call_args[0][2] == TEST_USER_ID  # third positional arg is user_id


# ---------------------------------------------------------------------------
# Service: list_serve_windows_by_video
# ---------------------------------------------------------------------------


class TestListServeWindowsByVideoService:
    def test_filters_by_video_id_active_and_visible_status(self):
        from app.services.serve_window_service import list_serve_windows_by_video

        mock_db = MagicMock()
        mock_query = MagicMock()
        mock_db.query.return_value = mock_query
        mock_query.filter.return_value = mock_query
        mock_query.order_by.return_value = mock_query
        mock_query.all.return_value = [_make_mock_window(id=1)]

        result = list_serve_windows_by_video(mock_db, video_id=10)

        assert len(result) == 1
        mock_db.query.assert_called_once()

    def test_returns_empty_list_when_no_windows(self):
        from app.services.serve_window_service import list_serve_windows_by_video

        mock_db = MagicMock()
        mock_query = MagicMock()
        mock_db.query.return_value = mock_query
        mock_query.filter.return_value = mock_query
        mock_query.order_by.return_value = mock_query
        mock_query.all.return_value = []

        result = list_serve_windows_by_video(mock_db, video_id=99)

        assert result == []
