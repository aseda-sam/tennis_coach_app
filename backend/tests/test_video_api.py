"""
Basic tests for video API endpoints.
"""

import os
import tempfile

import pytest
from fastapi.testclient import TestClient

# Import the app
from app.main import app

client = TestClient(app)


class TestVideoAPI:
    """Basic tests for video API endpoints."""

    def test_health_check(self) -> None:
        """Test the health check endpoint."""
        response = client.get("/health")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "healthy"
        assert data["version"] == "0.1.0"
        assert "timestamp" in data

    def test_root(self) -> None:
        """Test the root endpoint."""
        response = client.get("/")
        assert response.status_code == 200
        data = response.json()
        assert data["message"] == "Tennis Coach API"
        assert data["version"] == "0.1.0"
        assert data["status"] == "alpha"

    def test_api_info(self) -> None:
        """Test the API info endpoint."""
        response = client.get("/v0")
        assert response.status_code == 200
        data = response.json()
        assert data["version"] == "0.1.0"
        assert data["status"] == "alpha"
        assert "warning" in data
        assert "endpoints" in data

    def test_list_videos_empty(self) -> None:
        """Test listing videos when database is empty."""
        response = client.get("/v0/videos/")
        assert response.status_code == 200
        # Should return empty list
        assert isinstance(response.json(), list)

    def test_upload_video_invalid_format(self) -> None:
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

    def test_upload_video_success(self) -> None:
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

    def test_get_video_not_found(self) -> None:
        """Test getting a video that doesn't exist."""
        response = client.get("/v0/videos/999")
        assert response.status_code == 404
        error_data = response.json()
        assert "error" in error_data
        assert "code" in error_data["error"]


if __name__ == "__main__":
    # Run basic tests
    pytest.main([__file__, "-v"])
