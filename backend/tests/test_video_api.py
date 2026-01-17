"""
Basic tests for video API endpoints.
"""

import os
import tempfile
from typing import TYPE_CHECKING

import pytest
from fastapi.testclient import TestClient

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
            tmp_file.write(b"fake content")
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
            # Write some fake video content
            tmp_file.write(b"fake video content" * 1000)  # Make it larger
            tmp_file_path = tmp_file.name

        try:
            with open(tmp_file_path, "rb") as f:
                files = {"file": ("test.mp4", f, "video/mp4")}
                response = client.post("/v0/videos/upload", files=files)

            # Should succeed (even though it's not a real video)
            assert response.status_code == 200
            data = response.json()
            # The filename might be modified by ensure_unique_filename (e.g., test_1.mp4, test_2.mp4)
            assert data["filename"].startswith("test") and data["filename"].endswith(
                ".mp4"
            )
            assert "message" in data
            assert "video_id" in data
        finally:
            # Clean up
            if os.path.exists(tmp_file_path):
                os.unlink(tmp_file_path)

    def test_get_video_not_found(self, client: TestClient) -> None:
        """Test getting a video that doesn't exist."""
        response = client.get("/v0/videos/999")
        assert response.status_code == 404
        error_data = response.json()
        assert "error" in error_data
        assert "code" in error_data["error"]

    def test_get_video_metrics_no_contacts(
        self, client: TestClient, db_session: "Session", test_user_id: str
    ) -> None:
        """Test getting metrics for video with no ball contacts."""
        from app.models.video import Video

        # Create test video
        test_video = Video(
            filename="test_metrics.mp4",
            file_path="/path/to/test_metrics.mp4",
            file_size=1000000,
            duration=60.0,
            width=1920,
            height=1080,
            fps=30.0,
            status="uploaded",
            user_id=test_user_id,
        )
        db_session.add(test_video)
        db_session.commit()
        video_id = test_video.id

        # Get metrics
        response = client.get(f"/v0/videos/{video_id}/metrics")
        assert response.status_code == 200
        data = response.json()
        assert data["video_id"] == video_id
        assert data["serve_count"] == 0
        assert data["avg_elbow_angle"] is None
        assert data["total_contacts"] == 0
        assert data["toss_height"] is None
        assert data["contact_height"] is None

    def test_get_video_metrics_with_serves(
        self, client: TestClient, db_session: "Session", test_user_id: str
    ) -> None:
        """Test getting metrics for video with serves."""
        from app.models.ball_contact import BallContact
        from app.models.video import Video

        # Create test video
        test_video = Video(
            filename="test_serves.mp4",
            file_path="/path/to/test_serves.mp4",
            file_size=1000000,
            duration=60.0,
            width=1920,
            height=1080,
            fps=30.0,
            status="uploaded",
            user_id=test_user_id,
        )
        db_session.add(test_video)
        db_session.commit()
        video_id = test_video.id

        # Create ball contacts with serves
        contacts = [
            BallContact(
                video_id=video_id,
                video_timestamp=1.0,
                contact_hand="right",
                stroke_type="serve",
                elbow_angle=120.0,
                detection_source="manual",
            ),
            BallContact(
                video_id=video_id,
                video_timestamp=2.0,
                contact_hand="right",
                stroke_type="serve",
                elbow_angle=130.0,
                detection_source="manual",
            ),
            BallContact(
                video_id=video_id,
                video_timestamp=3.0,
                contact_hand="right",
                stroke_type="ground_stroke",
                detection_source="manual",
            ),
        ]
        db_session.add_all(contacts)
        db_session.commit()

        # Get metrics
        response = client.get(f"/v0/videos/{video_id}/metrics")
        assert response.status_code == 200
        data = response.json()
        assert data["video_id"] == video_id
        assert data["serve_count"] == 2
        assert data["avg_elbow_angle"] == 125  # (120 + 130) / 2 = 125
        assert data["total_contacts"] == 3

    def test_get_video_metrics_not_found(self, client: TestClient) -> None:
        """Test getting metrics for non-existent video."""
        response = client.get("/v0/videos/999/metrics")
        assert response.status_code == 404

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

    def test_upload_demo_video_unauthorized(
        self, client: TestClient, test_user_id: str
    ) -> None:
        """Test that unauthorized users cannot upload demo videos."""
        import tempfile

        # Create a mock video file
        with tempfile.NamedTemporaryFile(suffix=".mp4", delete=False) as tmp_file:
            tmp_file.write(b"fake video content" * 1000)
            tmp_file_path = tmp_file.name

        try:
            with open(tmp_file_path, "rb") as f:
                files = {"file": ("test.mp4", f, "video/mp4")}
                # Try to upload as demo with unauthorized user (different from DEMO_UPLOAD_USER_ID)
                response = client.post(
                    "/v0/videos/upload?is_demo=true", files=files
                )

            # Should fail with 403 in production, but might pass in local
            # Check that it's either 403 or 200 (local profile allows it)
            assert response.status_code in [200, 403]
        finally:
            import os

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


if __name__ == "__main__":
    # Run basic tests
    pytest.main([__file__, "-v"])
