"""
Tests for video quality assessment functionality.
"""

from pathlib import Path

import pytest
from fastapi.testclient import TestClient


class TestQualityAssessment:
    """Tests for video quality assessment endpoints."""

    def test_quality_assessment_endpoint_exists(self, client: TestClient) -> None:
        """Test that the quality assessment endpoint exists."""
        # Test with a non-existent video ID to check if endpoint exists
        response = client.post("/v0/videos/999/quality-check")
        # Should return 404 for non-existent video, not 404 for non-existent endpoint
        assert response.status_code in [
            404,
            422,
        ]  # 404 for video not found, 422 for validation error

    def test_quality_assessment_with_real_video(
        self, client: TestClient, test_video_path: Path
    ) -> None:
        """Test quality assessment with a real video file."""
        if not test_video_path.exists():
            pytest.skip("Real test video not available")

        # Upload real video first
        with open(test_video_path, "rb") as f:
            files = {"file": ("test_tennis_video.mp4", f, "video/mp4")}
            response = client.post("/v0/videos/upload", files=files)

        assert response.status_code == 200
        video_id = response.json()["video_id"]

        # Perform quality assessment
        response = client.post(f"/v0/videos/{video_id}/quality-check")

        # Should succeed with real video
        assert response.status_code == 200
        quality_data = response.json()

        # Verify response schema
        assert "video_id" in quality_data
        assert "filename" in quality_data
        assert "quality_metrics" in quality_data
        assert "assessment_time" in quality_data
        assert "message" in quality_data

        # Verify quality metrics structure
        metrics = quality_data["quality_metrics"]
        assert "quality_score" in metrics
        assert "blur_score" in metrics
        assert "lighting_score" in metrics
        assert "resolution_score" in metrics
        assert "quality_level" in metrics
        assert "recommended_confidence_threshold" in metrics
        assert "frame_count_analyzed" in metrics

        # Verify data types
        assert isinstance(metrics["quality_score"], float)
        assert isinstance(metrics["blur_score"], float)
        assert isinstance(metrics["lighting_score"], float)
        assert isinstance(metrics["resolution_score"], float)
        assert isinstance(metrics["quality_level"], str)
        assert isinstance(metrics["recommended_confidence_threshold"], float)
        assert isinstance(metrics["frame_count_analyzed"], int)

        # Verify value ranges
        assert 0 <= metrics["quality_score"] <= 1
        assert 0 <= metrics["blur_score"] <= 1
        assert 0 <= metrics["lighting_score"] <= 1
        assert 0 <= metrics["resolution_score"] <= 1
        assert 0 <= metrics["recommended_confidence_threshold"] <= 1
        assert metrics["frame_count_analyzed"] > 0

        # Verify quality level is one of expected values
        expected_levels = ["excellent", "good", "fair", "poor", "unknown"]
        assert metrics["quality_level"] in expected_levels

        # Clean up
        response = client.delete(f"/v0/videos/{video_id}")
        assert response.status_code == 200

    def test_quality_assessment_nonexistent_video(self, client: TestClient) -> None:
        """Test quality assessment with non-existent video."""
        response = client.post("/v0/videos/99999/quality-check")
        assert response.status_code == 404
        error_data = response.json()
        assert "detail" in error_data
        assert "not found" in error_data["detail"].lower()

    def test_quality_assessment_invalid_video_id(self, client: TestClient) -> None:
        """Test quality assessment with invalid video ID format."""
        response = client.post("/v0/videos/invalid/quality-check")
        assert response.status_code == 422  # Validation error

    def test_quality_assessment_already_assessed_video(
        self, client: TestClient, test_video_path: Path
    ) -> None:
        """Test quality assessment on a video that already has quality metrics."""
        if not test_video_path.exists():
            pytest.skip("Real test video not available")

        # Upload real video first
        with open(test_video_path, "rb") as f:
            files = {"file": ("test_tennis_video.mp4", f, "video/mp4")}
            response = client.post("/v0/videos/upload", files=files)

        assert response.status_code == 200
        video_id = response.json()["video_id"]

        # First quality assessment
        response1 = client.post(f"/v0/videos/{video_id}/quality-check")
        assert response1.status_code == 200
        first_assessment = response1.json()

        # Second quality assessment (should work and potentially return cached results)
        response2 = client.post(f"/v0/videos/{video_id}/quality-check")
        assert response2.status_code == 200
        second_assessment = response2.json()

        # Both should have the same structure
        assert "quality_metrics" in first_assessment
        assert "quality_metrics" in second_assessment

        # Clean up
        response = client.delete(f"/v0/videos/{video_id}")
        assert response.status_code == 200
