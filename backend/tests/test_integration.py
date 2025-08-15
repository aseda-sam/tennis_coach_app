"""
Legacy integration tests - being replaced by more focused test files.
These tests use real test video files for comprehensive testing.
"""

import os
import tempfile
from pathlib import Path

import pytest
from fastapi.testclient import TestClient


class TestVideoIntegration:
    """Integration tests for video endpoints."""

    def test_video_upload_and_retrieval(self, client: TestClient) -> None:
        """Test complete video upload and retrieval workflow."""
        # Create a temporary video file
        with tempfile.NamedTemporaryFile(suffix=".mp4", delete=False) as tmp_file:
            tmp_file.write(b"fake video content" * 1000)
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
            tmp_file.write(b"fake video content" * 1000)
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


class TestAnalysisIntegration:
    """Integration tests for analysis endpoints."""

    def test_analysis_creation_and_retrieval(self, client: TestClient) -> None:
        """Test complete analysis creation and retrieval workflow."""
        # Use the real test video file
        test_video_path = Path(__file__).parent / "test_data" / "test_tennis_video.mp4"
        if not test_video_path.exists():
            pytest.skip("Test video file not found")

        # Upload the test video
        with open(test_video_path, "rb") as f:
            files = {"file": ("test_tennis_video.mp4", f, "video/mp4")}
            response = client.post("/v0/videos/upload", files=files)

        assert response.status_code == 200
        video_id = response.json()["video_id"]

        # Start analysis (synchronous mode for testing)
        analysis_request = {
            "analysis_type": "ball_tracking",
            "confidence_threshold": 0.5,
            "include_pose_detection": False,
            "synchronous": True,
        }

        response = client.post(f"/v0/analysis/videos/{video_id}", json=analysis_request)

        # With real video file, analysis should succeed
        assert response.status_code == 200
        analysis_data = response.json()
        assert "analysis_id" in analysis_data
        assert "status" in analysis_data
        assert analysis_data["status"] == "completed"

        # Get analysis results
        response = client.get(f"/v0/analysis/{analysis_data['analysis_id']}")
        assert response.status_code == 200
        analysis_info = response.json()

        # Verify analysis results
        assert analysis_info["video_id"] == video_id
        assert analysis_info["analysis_type"] == "ball_tracking"
        assert analysis_info["status"] == "completed"
        assert "detection_rate" in analysis_info

    def test_analysis_deletion(self, client: TestClient) -> None:
        """Test analysis deletion workflow."""
        # Use the real test video file
        test_video_path = Path(__file__).parent / "test_data" / "test_tennis_video.mp4"
        if not test_video_path.exists():
            pytest.skip("Test video file not found")

        # Upload the test video
        with open(test_video_path, "rb") as f:
            files = {"file": ("test_tennis_video.mp4", f, "video/mp4")}
            response = client.post("/v0/videos/upload", files=files)

        assert response.status_code == 200
        video_id = response.json()["video_id"]

        # Start analysis (synchronous mode for testing)
        analysis_request = {
            "analysis_type": "ball_tracking",
            "confidence_threshold": 0.5,
            "include_pose_detection": False,
            "synchronous": True,
        }

        response = client.post(f"/v0/analysis/videos/{video_id}", json=analysis_request)

        # Analysis should succeed with real video
        assert response.status_code == 200
        analysis_data = response.json()
        analysis_id = analysis_data["analysis_id"]

        # Delete the analysis
        response = client.delete(f"/v0/analysis/{analysis_id}")
        assert response.status_code == 200
        delete_data = response.json()
        assert "message" in delete_data
        assert delete_data["analysis_id"] == analysis_id

        # Verify analysis is deleted
        response = client.get(f"/v0/analysis/{analysis_id}")
        assert response.status_code == 404

    def test_analysis_schema_validation(self, client: TestClient) -> None:
        """Test that analysis response schemas match database models."""
        # Use the real test video file
        test_video_path = Path(__file__).parent / "test_data" / "test_tennis_video.mp4"
        if not test_video_path.exists():
            pytest.skip("Test video file not found")

        # Upload the test video
        with open(test_video_path, "rb") as f:
            files = {"file": ("test_tennis_video.mp4", f, "video/mp4")}
            response = client.post("/v0/videos/upload", files=files)

        assert response.status_code == 200
        video_id = response.json()["video_id"]

        # Start analysis (synchronous mode for testing)
        analysis_request = {
            "analysis_type": "ball_tracking",
            "confidence_threshold": 0.5,
            "include_pose_detection": False,
            "synchronous": True,
        }

        response = client.post(f"/v0/analysis/videos/{video_id}", json=analysis_request)

        # Analysis should succeed with real video
        assert response.status_code == 200
        analysis_data = response.json()
        analysis_id = analysis_data["analysis_id"]

        # Get analysis results and verify schema
        response = client.get(f"/v0/analysis/{analysis_id}")
        assert response.status_code == 200
        analysis_info = response.json()

        # Verify all required fields are present
        required_fields = [
            "id",
            "video_id",
            "video_filename",
            "analysis_type",
            "status",
            "total_frames",
            "frames_with_balls",
            "total_ball_detections",
            "average_detections_per_frame",
            "detection_rate",
            "processing_time",
            "model_used",
            "confidence_threshold",
            "created_at",
        ]

        for field in required_fields:
            assert field in analysis_info, f"Missing field: {field}"

        # Verify data types
        assert isinstance(analysis_info["id"], int)
        assert isinstance(analysis_info["video_id"], int)
        assert isinstance(analysis_info["video_filename"], str)
        assert isinstance(analysis_info["analysis_type"], str)
        assert isinstance(analysis_info["total_frames"], int)
        assert isinstance(analysis_info["detection_rate"], float)
        assert isinstance(analysis_info["processing_time"], float)


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

    def test_invalid_analysis_id(self, client: TestClient) -> None:
        """Test handling of invalid analysis IDs."""
        # Test with non-existent analysis ID
        response = client.get("/v0/analysis/99999")
        assert response.status_code == 404
        error_data = response.json()
        assert "error" in error_data
        assert "message" in error_data["error"]

    def test_malformed_requests(self, client: TestClient) -> None:
        """Test handling of malformed requests."""
        # Test upload without file
        response = client.post("/v0/videos/upload")
        assert response.status_code == 422  # Validation error

        # Test analysis with invalid video ID
        analysis_request = {
            "analysis_type": "ball_tracking",
            "confidence_threshold": 0.5,
            "include_pose_detection": False,
        }
        response = client.post("/v0/analysis/videos/99999", json=analysis_request)
        assert response.status_code == 404
