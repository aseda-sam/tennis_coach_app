"""
Basic API tests that don't require real video processing.
These tests focus on endpoint availability, schema validation, and error handling.
"""

from fastapi.testclient import TestClient


class TestBasicAPI:
    """Basic API endpoint tests."""

    def test_health_check(self, client: TestClient) -> None:
        """Test health check endpoint."""
        response = client.get("/health")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "healthy"

    def test_list_videos_empty(self, client: TestClient) -> None:
        """Test listing videos when database is empty."""
        response = client.get("/v0/videos/")
        assert response.status_code == 200
        assert response.json() == []

    def test_upload_invalid_format(self, client: TestClient) -> None:
        """Test upload with unsupported file format."""
        test_content = b"fake content"
        files = {"file": ("test.txt", test_content, "text/plain")}

        response = client.post("/v0/videos/upload", files=files)

        assert response.status_code == 400
        error_data = response.json()
        assert "error" in error_data
        assert "format not supported" in error_data["error"]["message"].lower()

    def test_upload_no_file(self, client: TestClient) -> None:
        """Test upload without file."""
        response = client.post("/v0/videos/upload")
        assert response.status_code == 422  # Validation error

    def test_get_nonexistent_video(self, client: TestClient) -> None:
        """Test getting a video that doesn't exist."""
        response = client.get("/v0/videos/999")
        assert response.status_code == 404
        error_data = response.json()
        assert "error" in error_data
        assert "not found" in error_data["error"]["message"].lower()

    def test_delete_nonexistent_video(self, client: TestClient) -> None:
        """Test deleting a video that doesn't exist."""
        response = client.delete("/v0/videos/999")
        assert response.status_code == 404

    def test_upload_minimal_video_file(
        self, client: TestClient, sample_video_content: bytes
    ) -> None:
        """Test upload with minimal video file (for API testing only)."""
        files = {"file": ("test_minimal.mp4", sample_video_content, "video/mp4")}

        response = client.post("/v0/videos/upload", files=files)

        # The minimal video file might be accepted by the API
        # but will fail during video processing (which is expected)
        if response.status_code == 200:
            # If accepted, verify the response structure
            upload_data = response.json()
            assert "video_id" in upload_data
            assert "filename" in upload_data
            assert "status" in upload_data
        else:
            # If rejected, verify error structure
            error_data = response.json()
            assert "error" in error_data
