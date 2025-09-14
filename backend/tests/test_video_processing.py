"""
Video processing tests that require real video files.
These tests verify the actual video processing pipeline.
"""

from pathlib import Path
from typing import Generator

import pytest
from fastapi.testclient import TestClient


class TestVideoProcessing:
    """Tests for real video processing functionality."""

    def test_upload_real_video(
        self,
        client: TestClient,
        test_video_path: Path,
        cleanup_test_files: Generator[None, None, None],
    ) -> None:
        """Test uploading and processing a real video file."""
        if not test_video_path.exists():
            pytest.skip("Real test video not available")

        # Upload real video
        with open(test_video_path, "rb") as f:
            files = {"file": ("test_tennis_video.mp4", f, "video/mp4")}
            response = client.post("/v0/videos/upload", files=files)

        assert response.status_code == 200
        upload_data = response.json()

        # Verify upload response
        assert "video_id" in upload_data
        assert "filename" in upload_data
        assert "file_size" in upload_data
        assert "status" in upload_data
        video_id = upload_data["video_id"]

        # Get video details
        response = client.get(f"/v0/videos/{video_id}")
        assert response.status_code == 200
        video_data = response.json()

        # Verify video metadata was extracted
        assert video_data["id"] == video_id
        assert video_data["filename"].startswith(
            "test_tennis_video"
        )  # May have _2, _3, etc.
        assert video_data["file_size"] > 0
        assert video_data["status"] == "uploaded"

        # Verify video metadata fields are present
        assert "duration" in video_data
        assert "fps" in video_data
        assert "width" in video_data
        assert "height" in video_data
        assert "frame_count" in video_data

        # Clean up
        response = client.delete(f"/v0/videos/{video_id}")
        assert response.status_code == 200

    def test_video_stream(
        self,
        client: TestClient,
        test_video_path: Path,
        cleanup_test_files: Generator[None, None, None],
    ) -> None:
        """Test video streaming endpoints."""
        if not test_video_path.exists():
            pytest.skip("Real test video not available")

        # Upload video
        with open(test_video_path, "rb") as f:
            files = {"file": ("test_tennis_video.mp4", f, "video/mp4")}
            response = client.post("/v0/videos/upload", files=files)

        assert response.status_code == 200
        video_id = response.json()["video_id"]

        # Test original video stream
        response = client.get(f"/v0/videos/{video_id}/stream")
        assert response.status_code == 200
        assert response.headers["content-type"] == "video/mp4"

        # Test annotated video stream (will return 400/404 if no annotated video exists)
        response = client.get(f"/v0/videos/{video_id}/annotated/stream")
        # This will return 400/404 if no annotated video exists (which is expected)
        assert response.status_code in [200, 400, 404]

        # Clean up
        response = client.delete(f"/v0/videos/{video_id}")
        assert response.status_code == 200
