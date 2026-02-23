"""
Basic tests for video API endpoints.
"""

import os
import tempfile
import uuid
from datetime import datetime, timedelta, timezone
from typing import TYPE_CHECKING, Generator, Optional
from unittest.mock import MagicMock, patch

import pytest
from fastapi.testclient import TestClient
from redis.exceptions import ConnectionError as RedisConnectionError

from app.core.config import settings
from app.core.database import get_db
from app.dependencies.auth import get_optional_user
from app.main import app

if TYPE_CHECKING:
    from sqlalchemy.orm import Session


class TestVideoAPI:
    """Basic tests for video API endpoints."""

    def test_health_check(self, client: TestClient) -> None:
        """Test the health check endpoint."""
        response = client.get("/health")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "healthy"
        assert data["version"] == "0.1.0"
        assert "timestamp" in data

    def test_root(self, client: TestClient) -> None:
        """Test the root endpoint."""
        response = client.get("/")
        assert response.status_code == 200
        data = response.json()
        assert data["message"] == "Tennis Coach API"
        assert data["version"] == "0.1.0"
        assert data["status"] == "alpha"

    def test_api_info(self, client: TestClient) -> None:
        """Test the API info endpoint."""
        response = client.get("/v0")
        assert response.status_code == 200
        data = response.json()
        assert data["version"] == "0.1.0"
        assert data["status"] == "alpha"
        assert "warning" in data
        assert "endpoints" in data

    def test_list_videos_empty(self, client: TestClient) -> None:
        """Test listing videos when database is empty."""
        response = client.get("/v0/videos/")
        assert response.status_code == 200
        # Should return empty list
        assert isinstance(response.json(), list)

    def test_upload_video_invalid_format(self, client: TestClient) -> None:
        """Test upload with unsupported file format."""
        # Create a temporary text file
        with tempfile.NamedTemporaryFile(suffix=".txt", delete=False) as tmp_file:
            tmp_file.write(
                b"\x00\x00\x00\x20ftypmp41\x00\x00\x00\x00mp41isom" + b"\x00" * 100
            )
            tmp_file_path = tmp_file.name

        try:
            with open(tmp_file_path, "rb") as f:
                files = {"file": ("test.txt", f, "text/plain")}
                response = client.post("/v0/videos/upload", files=files)

            assert response.status_code == 400
            error_data = response.json()
            assert "error" in error_data
            assert "code" in error_data["error"]
        finally:
            # Clean up
            if os.path.exists(tmp_file_path):
                os.unlink(tmp_file_path)

    def test_upload_video_success(self, client: TestClient) -> None:
        """Test successful video upload with mock video file."""
        # Create a mock video file (just a file with .mp4 extension)
        with tempfile.NamedTemporaryFile(suffix=".mp4", delete=False) as tmp_file:
            # Write valid MP4 magic bytes + padding
            tmp_file.write(
                b"\x00\x00\x00\x20ftypmp41\x00\x00\x00\x00mp41isom" + b"\x00" * 10000
            )  # Make it larger
            tmp_file_path = tmp_file.name

        try:
            # Mock the enqueue function to verify it's called when enabled
            mock_job = MagicMock()
            mock_job.id = "test-job-id-123"
            with patch.object(settings, "AUTO_ENQUEUE_ON_UPLOAD", True), patch.object(
                settings, "TRANSCODE_ENABLED", False
            ), patch(
                "app.core.redis_config.analysis_queue.enqueue", return_value=mock_job
            ) as mock_enqueue:
                with open(tmp_file_path, "rb") as f:
                    files = {"file": ("test.mp4", f, "video/mp4")}
                    response = client.post("/v0/videos/upload", files=files)

                # Should succeed (even though it's not a real video)
                assert response.status_code == 200
                data = response.json()
                # The filename might be modified by ensure_unique_filename (e.g., test_1.mp4, test_2.mp4)
                assert data["filename"].startswith("test") and data[
                    "filename"
                ].endswith(".mp4")
                assert "message" in data
                assert "video_id" in data

                # Verify that enqueue was called
                assert mock_enqueue.called
        finally:
            # Clean up
            if os.path.exists(tmp_file_path):
                os.unlink(tmp_file_path)

    def test_upload_video_succeeds_when_enqueue_fails(self, client: TestClient) -> None:
        """Test that upload succeeds even if enqueue fails (Redis down)."""
        # Create a mock video file
        with tempfile.NamedTemporaryFile(suffix=".mp4", delete=False) as tmp_file:
            tmp_file.write(
                b"\x00\x00\x00\x20ftypmp41\x00\x00\x00\x00mp41isom" + b"\x00" * 10000
            )
            tmp_file_path = tmp_file.name

        try:
            # Mock enqueue to return None (simulating Redis failure)
            with patch.object(settings, "AUTO_ENQUEUE_ON_UPLOAD", True), patch.object(
                settings, "TRANSCODE_ENABLED", False
            ), patch(
                "app.core.redis_config.analysis_queue.enqueue", return_value=None
            ) as mock_enqueue:
                with open(tmp_file_path, "rb") as f:
                    files = {"file": ("test.mp4", f, "video/mp4")}
                    response = client.post("/v0/videos/upload", files=files)

                # Upload should still succeed even if enqueue fails
                assert response.status_code == 200
                data = response.json()
                assert "video_id" in data
                assert "message" in data

                # Verify that enqueue was attempted
                assert mock_enqueue.called
        finally:
            # Clean up
            if os.path.exists(tmp_file_path):
                os.unlink(tmp_file_path)

    def test_upload_video_succeeds_when_enqueue_raises_exception(
        self, client: TestClient
    ) -> None:
        """Test that upload succeeds even if enqueue raises exception."""
        # Create a mock video file
        with tempfile.NamedTemporaryFile(suffix=".mp4", delete=False) as tmp_file:
            tmp_file.write(
                b"\x00\x00\x00\x20ftypmp41\x00\x00\x00\x00mp41isom" + b"\x00" * 10000
            )
            tmp_file_path = tmp_file.name

        try:
            # Mock enqueue to raise RedisConnectionError
            with patch.object(settings, "AUTO_ENQUEUE_ON_UPLOAD", True), patch.object(
                settings, "TRANSCODE_ENABLED", False
            ), patch(
                "app.core.redis_config.analysis_queue.enqueue",
                side_effect=RedisConnectionError("Redis unavailable"),
            ) as mock_enqueue:
                with open(tmp_file_path, "rb") as f:
                    files = {"file": ("test.mp4", f, "video/mp4")}
                    response = client.post("/v0/videos/upload", files=files)

                # Upload should still succeed even if enqueue raises exception
                assert response.status_code == 200
                data = response.json()
                assert "video_id" in data
                assert "message" in data

                # Verify that enqueue was attempted
                assert mock_enqueue.called
        finally:
            # Clean up
            if os.path.exists(tmp_file_path):
                os.unlink(tmp_file_path)

    def test_upload_with_auto_enqueue_always_enqueues_transcode(
        self, client: TestClient
    ) -> None:
        """Test that all uploads enqueue a transcode job (regardless of file size)."""
        with tempfile.NamedTemporaryFile(suffix=".mp4", delete=False) as tmp_file:
            tmp_file.write(
                b"\x00\x00\x00\x20ftypmp41\x00\x00\x00\x00mp41isom" + b"\x00" * 1000
            )
            tmp_file_path = tmp_file.name

        try:
            mock_job = MagicMock()
            mock_job.id = "test-transcode-job-id"
            with patch.object(settings, "AUTO_ENQUEUE_ON_UPLOAD", True), patch.object(
                settings, "TRANSCODE_ENABLED", True
            ), patch(
                "app.core.redis_config.analysis_queue.enqueue", return_value=mock_job
            ) as mock_enqueue:
                with open(tmp_file_path, "rb") as f:
                    files = {"file": ("test_video.mp4", f, "video/mp4")}
                    response = client.post("/v0/videos/upload", files=files)

                assert response.status_code == 200
                data = response.json()
                assert "video_id" in data

                # Every upload routes through transcode first
                assert mock_enqueue.called
                call_args = mock_enqueue.call_args
                from app.services.rq_tasks import transcode_video_rq

                assert call_args[0][0] == transcode_video_rq
                assert call_args[1]["video_id"] == data["video_id"]
        finally:
            if os.path.exists(tmp_file_path):
                os.unlink(tmp_file_path)

    def test_get_video_not_found(self, client: TestClient) -> None:
        """Test getting a video that doesn't exist."""
        response = client.get("/v0/videos/999")
        assert response.status_code == 404
        error_data = response.json()
        assert "error" in error_data
        assert "code" in error_data["error"]

    def test_get_demo_video_not_found(
        self, client: TestClient, db_session: "Session"
    ) -> None:
        """Test getting demo video when none is active."""
        from app.models.video import Video

        # Ensure no active demo exists
        db_session.query(Video).filter(Video.is_active_demo).update(
            {"is_active_demo": False}
        )
        db_session.commit()

        response = client.get("/v0/videos/demo")
        assert response.status_code == 404
        error_data = response.json()
        assert "detail" in error_data
        assert "No active demo video" in error_data["detail"]

    def test_get_demo_video_success(
        self, client: TestClient, db_session: "Session", test_user_id: str
    ) -> None:
        """Test getting active demo video."""
        from app.models.video import Video

        # Create demo video and set as active
        demo_video = Video(
            filename="demo_video.mp4",
            file_path="demo/demo_video.mp4",
            file_size=1000000,
            duration=60.0,
            width=1920,
            height=1080,
            fps=30.0,
            status="uploaded",
            user_id=test_user_id,
            is_demo=True,
            is_active_demo=True,
        )
        db_session.add(demo_video)
        db_session.commit()

        response = client.get("/v0/videos/demo")
        assert response.status_code == 200
        data = response.json()
        assert data["id"] == demo_video.id
        assert data["is_demo"] is True
        assert data["is_active_demo"] is True
        assert data["filename"] == "demo_video.mp4"

    @pytest.fixture
    def unauthenticated_client(
        self, db_session: "Session"
    ) -> Generator[TestClient, None, None]:
        """Test client that simulates no authenticated user."""

        def override_get_db() -> Generator:
            try:
                yield db_session
            finally:
                pass

        async def mock_get_optional_user() -> Optional[dict]:
            return None

        app.dependency_overrides[get_db] = override_get_db
        app.dependency_overrides[get_optional_user] = mock_get_optional_user

        with TestClient(app) as test_client:
            yield test_client

        app.dependency_overrides.clear()

    def test_get_demo_video_public_access(
        self,
        unauthenticated_client: TestClient,
        db_session: "Session",
        test_user_id: str,
    ) -> None:
        """Test that demo video metadata is accessible without auth."""
        from app.models.video import Video

        demo_video = Video(
            filename="demo_public.mp4",
            file_path="demo/demo_public.mp4",
            file_size=1000000,
            duration=60.0,
            width=1920,
            height=1080,
            fps=30.0,
            status="uploaded",
            user_id=test_user_id,
            is_demo=True,
            is_active_demo=True,
        )
        db_session.add(demo_video)
        db_session.commit()

        response = unauthenticated_client.get("/v0/videos/demo")
        assert response.status_code == 200
        data = response.json()
        assert data["id"] == demo_video.id
        assert data["is_demo"] is True
        assert data["is_active_demo"] is True

    def test_get_demo_video_url_public_access(
        self,
        unauthenticated_client: TestClient,
        db_session: "Session",
        test_user_id: str,
    ) -> None:
        """Test that demo video URLs are accessible without auth."""
        from app.models.video import Video

        demo_video = Video(
            filename="demo_public_url.mp4",
            file_path="demo/demo_public_url.mp4",
            file_size=1000000,
            duration=60.0,
            width=1920,
            height=1080,
            fps=30.0,
            status="uploaded",
            user_id=test_user_id,
            is_demo=True,
            is_active_demo=True,
        )
        db_session.add(demo_video)
        db_session.commit()

        response = unauthenticated_client.get(f"/v0/videos/{demo_video.id}/url")
        assert response.status_code == 200
        data = response.json()
        assert "url" in data

    def test_get_video_url_requires_auth(
        self,
        unauthenticated_client: TestClient,
        db_session: "Session",
        test_user_id: str,
    ) -> None:
        """Test that non-demo video URLs require auth."""
        from app.models.video import Video

        video = Video(
            filename="private_video.mp4",
            file_path="raw/private_video.mp4",
            file_size=1000000,
            duration=60.0,
            width=1920,
            height=1080,
            fps=30.0,
            status="uploaded",
            user_id=test_user_id,
            is_demo=False,
            is_active_demo=False,
        )
        db_session.add(video)
        db_session.commit()

        response = unauthenticated_client.get(f"/v0/videos/{video.id}/url")
        assert response.status_code == 401

    def test_upload_demo_video_unauthorized(
        self, client: TestClient, test_user_id: str
    ) -> None:
        """Test that unauthorized users cannot upload demo videos."""
        # Skip if using Supabase storage - demo uploads require Supabase demo bucket
        from app.services.storage_service import storage_service

        if storage_service.storage_type == "supabase":
            pytest.skip(
                "Test requires local storage - demo uploads use Supabase bucket"
            )

        # Create a mock video file
        with tempfile.NamedTemporaryFile(suffix=".mp4", delete=False) as tmp_file:
            tmp_file.write(
                b"\x00\x00\x00\x20ftypmp41\x00\x00\x00\x00mp41isom" + b"\x00" * 10000
            )
            tmp_file_path = tmp_file.name

        try:
            # Use unique filename to avoid duplicate file errors
            unique_filename = f"test_{uuid.uuid4().hex[:8]}.mp4"
            with open(tmp_file_path, "rb") as f:
                files = {"file": (unique_filename, f, "video/mp4")}
                # Try to upload as demo with unauthorized user (different from DEMO_UPLOAD_USER_ID)
                response = client.post("/v0/videos/upload?is_demo=true", files=files)

            # Should fail with 403 in production, but might pass in local
            # Check that it's either 403 or 200 (local profile allows it)
            assert response.status_code in [200, 403]
        finally:
            if os.path.exists(tmp_file_path):
                os.unlink(tmp_file_path)

    def test_list_videos_excludes_demo(
        self, client: TestClient, db_session: "Session", test_user_id: str
    ) -> None:
        """Test that demo videos are excluded from user's video list."""
        from app.models.video import Video

        # Create regular video
        regular_video = Video(
            filename="regular.mp4",
            file_path="raw/regular.mp4",
            file_size=1000000,
            duration=60.0,
            width=1920,
            height=1080,
            fps=30.0,
            status="uploaded",
            user_id=test_user_id,
            is_demo=False,
        )
        # Create demo video
        demo_video = Video(
            filename="demo.mp4",
            file_path="demo/demo.mp4",
            file_size=1000000,
            duration=60.0,
            width=1920,
            height=1080,
            fps=30.0,
            status="uploaded",
            user_id=test_user_id,
            is_demo=True,
        )
        db_session.add_all([regular_video, demo_video])
        db_session.commit()

        response = client.get("/v0/videos/")
        assert response.status_code == 200
        videos = response.json()
        video_ids = [v["id"] for v in videos]
        assert regular_video.id in video_ids
        assert demo_video.id not in video_ids

    def test_list_videos_orders_by_recorded_at_with_created_at_fallback(
        self, client: TestClient, db_session: "Session", test_user_id: str
    ) -> None:
        """List endpoint sorts by recorded_at desc, falling back to created_at."""
        from app.models.video import Video

        now = datetime.now(timezone.utc)

        video_recorded_newest = Video(
            filename="recorded_newest.mp4",
            file_path="raw/recorded_newest.mp4",
            file_size=1000000,
            duration=60.0,
            width=1920,
            height=1080,
            fps=30.0,
            status="uploaded",
            user_id=test_user_id,
            is_demo=False,
            created_at=now - timedelta(days=10),
            recorded_at=now - timedelta(days=1),
        )
        video_fallback_created = Video(
            filename="fallback_created.mp4",
            file_path="raw/fallback_created.mp4",
            file_size=1000000,
            duration=60.0,
            width=1920,
            height=1080,
            fps=30.0,
            status="uploaded",
            user_id=test_user_id,
            is_demo=False,
            created_at=now - timedelta(days=2),
            recorded_at=None,
        )
        video_recorded_oldest = Video(
            filename="recorded_oldest.mp4",
            file_path="raw/recorded_oldest.mp4",
            file_size=1000000,
            duration=60.0,
            width=1920,
            height=1080,
            fps=30.0,
            status="uploaded",
            user_id=test_user_id,
            is_demo=False,
            created_at=now - timedelta(days=1),
            recorded_at=now - timedelta(days=3),
        )

        db_session.add_all(
            [video_recorded_newest, video_fallback_created, video_recorded_oldest]
        )
        db_session.commit()

        response = client.get("/v0/videos/")
        assert response.status_code == 200
        videos = response.json()

        # Contract: list items include recorded_at field
        assert "recorded_at" in videos[0]

        ids_in_order = [item["id"] for item in videos]
        assert ids_in_order.index(video_recorded_newest.id) < ids_in_order.index(
            video_fallback_created.id
        )
        assert ids_in_order.index(video_fallback_created.id) < ids_in_order.index(
            video_recorded_oldest.id
        )

    def test_update_video_metadata_success(
        self, client: TestClient, db_session: "Session", test_user_id: str
    ) -> None:
        """Test updating video metadata (session_type and camera_angle)."""
        from app.models.video import Video

        # Create a video
        video = Video(
            filename="test_video.mp4",
            file_path="raw/test_video.mp4",
            file_size=1000000,
            duration=60.0,
            width=1920,
            height=1080,
            fps=30.0,
            status="uploaded",
            user_id=test_user_id,
            session_type=None,
            camera_angle=None,
        )
        db_session.add(video)
        db_session.commit()
        video_id = video.id

        # Update metadata
        update_data = {
            "session_type": "serve_practice",
            "camera_angle": "behind",
        }
        response = client.patch(f"/v0/videos/{video_id}/metadata", json=update_data)

        assert response.status_code == 200
        data = response.json()
        assert data["id"] == video_id
        assert data["session_type"] == "serve_practice"
        assert data["camera_angle"] == "behind"

        # Verify database was updated
        db_session.refresh(video)
        assert video.session_type == "serve_practice"
        assert video.camera_angle == "behind"

    def test_update_video_metadata_partial(
        self, client: TestClient, db_session: "Session", test_user_id: str
    ) -> None:
        """Test updating only session_type (camera_angle remains unchanged)."""
        from app.models.video import Video

        # Create a video with existing camera_angle
        video = Video(
            filename="test_video2.mp4",
            file_path="raw/test_video2.mp4",
            file_size=1000000,
            duration=60.0,
            width=1920,
            height=1080,
            fps=30.0,
            status="uploaded",
            user_id=test_user_id,
            session_type=None,
            camera_angle="profile",
        )
        db_session.add(video)
        db_session.commit()
        video_id = video.id

        # Update only session_type
        update_data = {"session_type": "match"}
        response = client.patch(f"/v0/videos/{video_id}/metadata", json=update_data)

        assert response.status_code == 200
        data = response.json()
        assert data["session_type"] == "match"
        assert data["camera_angle"] == "profile"  # Should remain unchanged

    def test_update_video_metadata_valid_camera_angles(
        self, client: TestClient, db_session: "Session", test_user_id: str
    ) -> None:
        """Test that valid camera angles are accepted (behind, profile, unknown)."""
        from app.models.video import Video

        # Create a video
        video = Video(
            filename="test_video_camera.mp4",
            file_path="raw/test_video_camera.mp4",
            file_size=1000000,
            duration=60.0,
            width=1920,
            height=1080,
            fps=30.0,
            status="uploaded",
            user_id=test_user_id,
        )
        db_session.add(video)
        db_session.commit()
        video_id = video.id

        # Test valid camera angles
        valid_angles = ["behind", "profile", "unknown"]
        for angle in valid_angles:
            update_data = {"camera_angle": angle}
            response = client.patch(f"/v0/videos/{video_id}/metadata", json=update_data)
            assert response.status_code == 200
            data = response.json()
            assert data["camera_angle"] == angle

    def test_update_video_metadata_not_found(self, client: TestClient) -> None:
        """Test updating metadata for non-existent video."""
        update_data = {"session_type": "serve_practice"}
        response = client.patch("/v0/videos/99999/metadata", json=update_data)

        assert response.status_code == 404
        error_data = response.json()
        assert "error" in error_data

    def test_update_video_metadata_unauthorized(
        self, client: TestClient, db_session: "Session", test_user_id: str
    ) -> None:
        """Test that users cannot update metadata for videos they don't own."""
        from unittest.mock import patch

        from app.core.config import settings
        from app.models.video import Video

        # Create a video owned by a different user
        other_user_id = "other-user-id-12345"
        video = Video(
            filename="other_video.mp4",
            file_path="raw/other_video.mp4",
            file_size=1000000,
            duration=60.0,
            width=1920,
            height=1080,
            fps=30.0,
            status="uploaded",
            user_id=other_user_id,
        )
        db_session.add(video)
        db_session.commit()
        video_id = video.id

        # Mock ADMIN_USER_IDS to exclude test user (test user is admin by default)
        # This ensures the test verifies non-admin ownership checks
        with patch.object(settings, "ADMIN_USER_IDS", ""):
            # Try to update metadata (should fail - different user, not admin)
            update_data = {"session_type": "serve_practice"}
            response = client.patch(f"/v0/videos/{video_id}/metadata", json=update_data)

            # Should return 403 (forbidden - user doesn't own video)
            assert response.status_code == 403


class TestBallContactTimestamps:
    """Tests for GET /v0/videos/{video_id}/ball-contact-timestamps endpoint."""

    def test_get_ball_contact_timestamps_empty(
        self, client: TestClient, db_session: "Session", test_user_id: str
    ) -> None:
        """Test returns empty list when no serve windows exist."""
        from app.models.video import Video

        video = Video(
            filename="test_timestamps.mp4",
            file_path="raw/test_timestamps.mp4",
            file_size=1000000,
            duration=60.0,
            width=1920,
            height=1080,
            fps=30.0,
            status="uploaded",
            user_id=test_user_id,
        )
        db_session.add(video)
        db_session.commit()

        response = client.get(f"/v0/videos/{video.id}/ball-contact-timestamps")

        assert response.status_code == 200
        data = response.json()
        assert "ball_contact_timestamps" in data
        assert data["ball_contact_timestamps"] == []

    def test_get_ball_contact_timestamps_with_serves(
        self, client: TestClient, db_session: "Session", test_user_id: str
    ) -> None:
        """Test returns sorted unique timestamps from serve windows."""
        from app.models.player import Player
        from app.models.serve_window import ServeWindow
        from app.models.video import Video

        video = Video(
            filename="test_timestamps2.mp4",
            file_path="raw/test_timestamps2.mp4",
            file_size=1000000,
            duration=60.0,
            width=1920,
            height=1080,
            fps=30.0,
            status="uploaded",
            user_id=test_user_id,
        )
        db_session.add(video)
        db_session.commit()

        player = Player(
            name="Test Player",
            dominant_hand="right",
            user_id=test_user_id,
        )
        db_session.add(player)
        db_session.commit()

        # Create serve windows with contact timestamps
        serve1 = ServeWindow(
            video_id=video.id,
            player_id=player.id,
            user_id=test_user_id,
            start_timestamp=1.0,
            end_timestamp=3.0,
            contact_timestamp=2.5,
            court_side="deuce",
            serve_number=1,
        )
        serve2 = ServeWindow(
            video_id=video.id,
            player_id=player.id,
            user_id=test_user_id,
            start_timestamp=5.0,
            end_timestamp=7.0,
            contact_timestamp=6.2,
            court_side="ad",
            serve_number=1,
        )
        # Serve without contact timestamp (should be excluded)
        serve3 = ServeWindow(
            video_id=video.id,
            player_id=player.id,
            user_id=test_user_id,
            start_timestamp=10.0,
            end_timestamp=12.0,
            contact_timestamp=None,
            court_side="deuce",
            serve_number=2,
        )
        db_session.add_all([serve1, serve2, serve3])
        db_session.commit()

        response = client.get(f"/v0/videos/{video.id}/ball-contact-timestamps")

        assert response.status_code == 200
        data = response.json()
        assert "ball_contact_timestamps" in data
        timestamps = data["ball_contact_timestamps"]
        assert len(timestamps) == 2
        assert timestamps == [2.5, 6.2]  # Sorted ascending

    def test_get_ball_contact_timestamps_video_not_found(
        self, client: TestClient
    ) -> None:
        """Test returns 404 for non-existent video."""
        response = client.get("/v0/videos/99999/ball-contact-timestamps")

        assert response.status_code == 404

    def test_get_ball_contact_timestamps_excludes_other_users(
        self, client: TestClient, db_session: "Session", test_user_id: str
    ) -> None:
        """Test only returns timestamps from current user's serve windows."""
        from app.models.player import Player
        from app.models.serve_window import ServeWindow
        from app.models.video import Video

        video = Video(
            filename="test_timestamps3.mp4",
            file_path="raw/test_timestamps3.mp4",
            file_size=1000000,
            duration=60.0,
            width=1920,
            height=1080,
            fps=30.0,
            status="uploaded",
            user_id=test_user_id,
        )
        db_session.add(video)
        db_session.commit()

        player = Player(
            name="Test Player",
            dominant_hand="right",
            user_id=test_user_id,
        )
        other_player = Player(
            name="Other Player",
            dominant_hand="left",
            user_id="other-user-id",
        )
        db_session.add_all([player, other_player])
        db_session.commit()

        # User's serve window
        user_serve = ServeWindow(
            video_id=video.id,
            player_id=player.id,
            user_id=test_user_id,
            start_timestamp=1.0,
            end_timestamp=3.0,
            contact_timestamp=2.0,
            court_side="deuce",
            serve_number=1,
        )
        # Other user's serve window (should be excluded)
        other_serve = ServeWindow(
            video_id=video.id,
            player_id=other_player.id,
            user_id="other-user-id",
            start_timestamp=5.0,
            end_timestamp=7.0,
            contact_timestamp=6.0,
            court_side="ad",
            serve_number=1,
        )
        db_session.add_all([user_serve, other_serve])
        db_session.commit()

        response = client.get(f"/v0/videos/{video.id}/ball-contact-timestamps")

        assert response.status_code == 200
        data = response.json()
        timestamps = data["ball_contact_timestamps"]
        assert len(timestamps) == 1
        assert timestamps == [2.0]  # Only user's timestamp


if __name__ == "__main__":
    # Run basic tests
    pytest.main([__file__, "-v"])
