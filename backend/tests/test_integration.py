"""
Integration tests for end-to-end workflows.
These tests use real test video files for comprehensive testing of complete user workflows.
"""

import os
import tempfile

from fastapi.testclient import TestClient


class TestVideoIntegration:
    """Integration tests for video endpoints."""

    def test_video_upload_and_retrieval(self, client: TestClient) -> None:
        """Test complete video upload and retrieval workflow."""
        # Create a temporary video file
        with tempfile.NamedTemporaryFile(suffix=".mp4", delete=False) as tmp_file:
            tmp_file.write(
                b"\x00\x00\x00\x20ftypmp41\x00\x00\x00\x00mp41isom" + b"\x00" * 10000
            )
            tmp_file_path = tmp_file.name

        try:
            # Upload video
            with open(tmp_file_path, "rb") as f:
                files = {"file": ("test_integration.mp4", f, "video/mp4")}
                response = client.post("/v0/videos/upload", files=files)

            assert response.status_code == 200
            upload_data = response.json()

            # Verify upload response schema
            assert "video_id" in upload_data
            assert "filename" in upload_data
            assert "file_size" in upload_data
            assert "status" in upload_data
            assert "message" in upload_data
            video_id = upload_data["video_id"]

            # Get video details
            response = client.get(f"/v0/videos/{video_id}")
            assert response.status_code == 200
            video_data = response.json()

            # Verify schema alignment - all database fields should be present
            required_fields = [
                "id",
                "filename",
                "file_path",
                "file_size",
                "content_type",
                "duration",
                "fps",
                "width",
                "height",
                "frame_count",
                "created_at",
                "updated_at",
                "status",
                "error_message",
            ]

            for field in required_fields:
                assert field in video_data, f"Missing field: {field}"

            # Verify data types match schema expectations
            assert isinstance(video_data["id"], int)
            assert isinstance(video_data["filename"], str)
            assert isinstance(video_data["file_size"], int)
            assert video_data["id"] == video_id

            # List videos
            response = client.get("/v0/videos/")
            assert response.status_code == 200
            videos_list = response.json()

            # Verify list response contains our video
            assert len(videos_list) > 0
            video_found = any(v["id"] == video_id for v in videos_list)
            assert video_found, "Uploaded video not found in list"

            # Delete video
            response = client.delete(f"/v0/videos/{video_id}")
            assert response.status_code == 200
            delete_data = response.json()

            # Verify deletion response schema
            assert "message" in delete_data
            assert "video_id" in delete_data
            assert "filename" in delete_data
            assert delete_data["video_id"] == video_id

            # Verify video is actually deleted
            response = client.get(f"/v0/videos/{video_id}")
            assert response.status_code == 404

        finally:
            # Clean up temporary file
            if os.path.exists(tmp_file_path):
                os.unlink(tmp_file_path)

    def test_schema_validation(self, client: TestClient) -> None:
        """Test that all response schemas match database models."""
        # Upload a video first
        with tempfile.NamedTemporaryFile(suffix=".mp4", delete=False) as tmp_file:
            tmp_file.write(
                b"\x00\x00\x00\x20ftypmp41\x00\x00\x00\x00mp41isom" + b"\x00" * 10000
            )
            tmp_file_path = tmp_file.name

        try:
            with open(tmp_file_path, "rb") as f:
                files = {"file": ("test_schema.mp4", f, "video/mp4")}
                response = client.post("/v0/videos/upload", files=files)

            assert response.status_code == 200
            video_id = response.json()["video_id"]

            # Get video and verify schema
            response = client.get(f"/v0/videos/{video_id}")
            assert response.status_code == 200
            video_data = response.json()

            # These should match the database model exactly
            expected_fields = {
                "id": int,
                "filename": str,
                "file_path": str,
                "file_size": int,
                "content_type": (str, type(None)),
                "duration": (float, type(None)),
                "fps": (float, type(None)),
                "width": (int, type(None)),
                "height": (int, type(None)),
                "frame_count": (int, type(None)),
                "created_at": str,  # ISO datetime string
                "updated_at": (str, type(None)),
                "status": str,
                "error_message": (str, type(None)),
            }

            for field, expected_type in expected_fields.items():
                assert field in video_data, f"Missing field: {field}"
                if isinstance(expected_type, tuple):
                    assert isinstance(video_data[field], expected_type), (
                        f"Field {field} has wrong type"
                    )
                else:
                    assert isinstance(video_data[field], expected_type), (
                        f"Field {field} has wrong type"
                    )

        finally:
            if os.path.exists(tmp_file_path):
                os.unlink(tmp_file_path)


class TestErrorHandling:
    """Test error handling and edge cases."""

    def test_invalid_video_id(self, client: TestClient) -> None:
        """Test handling of invalid video IDs."""
        # Test with non-existent video ID
        response = client.get("/v0/videos/99999")
        assert response.status_code == 404
        error_data = response.json()
        assert "error" in error_data
        assert "message" in error_data["error"]

        # Test with invalid video ID format
        response = client.get("/v0/videos/invalid")
        assert response.status_code == 422  # Validation error

    def test_malformed_requests(self, client: TestClient) -> None:
        """Test handling of malformed requests."""
        # Test upload without file
        response = client.post("/v0/videos/upload")
        assert response.status_code == 422  # Validation error
