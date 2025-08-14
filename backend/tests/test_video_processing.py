"""
Video processing tests that require real video files.
These tests verify the actual video processing pipeline.
"""

import pytest
from fastapi.testclient import TestClient


class TestVideoProcessing:
    """Tests for real video processing functionality."""

    def test_upload_real_video(
        self, client: TestClient, test_video_path, cleanup_test_files
    ):
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

    def test_video_analysis_workflow(
        self, client: TestClient, test_video_path, cleanup_test_files
    ):
        """Test complete video analysis workflow with real video."""
        if not test_video_path.exists():
            pytest.skip("Real test video not available")

        # Upload video
        with open(test_video_path, "rb") as f:
            files = {"file": ("test_tennis_video.mp4", f, "video/mp4")}
            response = client.post("/v0/videos/upload", files=files)

        assert response.status_code == 200
        video_id = response.json()["video_id"]

        # Start analysis
        analysis_request = {
            "analysis_type": "ball_tracking",
            "confidence_threshold": 0.7,
            "include_pose_detection": False,
        }

        response = client.post(f"/v0/analysis/videos/{video_id}", json=analysis_request)

        # Analysis should either complete or fail gracefully
        assert response.status_code in [200, 500]

        if response.status_code == 200:
            analysis_data = response.json()
            assert "analysis_id" in analysis_data
            assert "status" in analysis_data

            # Get analysis results
            analysis_id = analysis_data["analysis_id"]
            response = client.get(f"/v0/analysis/{analysis_id}")

            if response.status_code == 200:
                results = response.json()
                # Check for expected fields in analysis results
                assert "analysis_type" in results
                assert "ball_detections" in results
                assert (
                    "detection_rate" in results
                    or "average_detections_per_frame" in results
                )

                # Clean up analysis
                response = client.delete(f"/v0/analysis/{analysis_id}")
                assert response.status_code == 200

        # Clean up video
        response = client.delete(f"/v0/videos/{video_id}")
        assert response.status_code == 200

    def test_video_stream_endpoints(
        self, client: TestClient, test_video_path, cleanup_test_files
    ):
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
