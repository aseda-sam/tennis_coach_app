"""
Tests for overlay data API endpoint.
"""

import json

from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.models.pose_detection import PoseDetection
from app.models.video import Video


class TestOverlayDataAPI:
    """Test overlay data API endpoint."""

    def test_get_overlay_data_success(
        self, client: TestClient, db_session: Session, test_user_id: str
    ) -> None:
        """Test successful retrieval of overlay data."""
        # Create a video
        video = Video(
            filename="test.mp4",
            file_path="test.mp4",
            file_size=1000000,
            fps=30.0,
            width=1920,
            height=1080,
            user_id=test_user_id,
        )
        db_session.add(video)
        db_session.commit()

        # Create pose detection with valid data
        pose_data = [
            {
                "left_shoulder": [100.0, 200.0],
                "right_shoulder": [300.0, 200.0],
                "left_elbow": [150.0, 300.0],
            }
        ]
        confidence_scores = [0.95]

        pose_detection = PoseDetection(
            video_id=video.id,
            status="completed",
            total_frames=1,
            pose_data=json.dumps(pose_data),
            confidence_scores=json.dumps(confidence_scores),
        )
        db_session.add(pose_detection)
        db_session.commit()

        # Make request
        response = client.get(
            f"/v0/videos/{video.id}/overlay-data",
        )

        assert response.status_code == 200
        data = response.json()
        assert data["video_id"] == video.id
        assert data["fps"] == 30.0
        assert data["width"] == 1920
        assert data["height"] == 1080
        assert len(data["frames"]) == 1
        assert data["frames"][0]["frame_index"] == 0
        assert "left_shoulder" in data["frames"][0]["keypoints"]

    def test_get_overlay_data_missing_pose_detection(
        self, client: TestClient, db_session: Session, test_user_id: str
    ) -> None:
        """Test overlay data when pose detection doesn't exist."""
        # Create a video
        video = Video(
            filename="test.mp4",
            file_path="test.mp4",
            file_size=1000000,
            user_id=test_user_id,
        )
        db_session.add(video)
        db_session.commit()

        # Make request without pose detection
        response = client.get(
            f"/v0/videos/{video.id}/overlay-data",
        )

        assert response.status_code == 404
        assert "No pose detection found" in response.json()["detail"]

    def test_get_overlay_data_malformed_json(
        self, client: TestClient, db_session: Session, test_user_id: str
    ) -> None:
        """Test overlay data with malformed JSON."""
        # Create a video
        video = Video(
            filename="test.mp4",
            file_path="test.mp4",
            file_size=1000000,
            fps=30.0,
            user_id=test_user_id,
        )
        db_session.add(video)
        db_session.commit()

        # Create pose detection with invalid JSON
        pose_detection = PoseDetection(
            video_id=video.id,
            status="completed",
            total_frames=1,
            pose_data="invalid json {",
            confidence_scores=None,
        )
        db_session.add(pose_detection)
        db_session.commit()

        # Make request
        response = client.get(
            f"/v0/videos/{video.id}/overlay-data",
        )

        assert response.status_code == 500
        assert "Failed to parse pose detection data" in response.json()["detail"]

    def test_get_overlay_data_too_large(
        self, client: TestClient, db_session: Session, test_user_id: str
    ) -> None:
        """Test overlay data with JSON exceeding size limit."""
        # Create a video
        video = Video(
            filename="test.mp4",
            file_path="test.mp4",
            file_size=1000000,
            fps=30.0,
            user_id=test_user_id,
        )
        db_session.add(video)
        db_session.commit()

        # Create pose detection with data exceeding 50MB limit
        large_data = "x" * (51 * 1024 * 1024)  # 51MB

        pose_detection = PoseDetection(
            video_id=video.id,
            status="completed",
            total_frames=1,
            pose_data=large_data,
            confidence_scores=None,
        )
        db_session.add(pose_detection)
        db_session.commit()

        # Make request
        response = client.get(
            f"/v0/videos/{video.id}/overlay-data",
        )

        assert response.status_code == 400
        assert "exceeds maximum size limit" in response.json()["detail"]

    def test_get_overlay_data_video_not_found(
        self, client: TestClient
    ) -> None:
        """Test overlay data when video doesn't exist."""
        response = client.get(
            "/v0/videos/99999/overlay-data",
        )

        assert response.status_code == 404

    def test_get_overlay_data_incomplete_pose_detection(
        self, client: TestClient, db_session: Session, test_user_id: str
    ) -> None:
        """Test overlay data when pose detection is not completed."""
        # Create a video
        video = Video(
            filename="test.mp4",
            file_path="test.mp4",
            file_size=1000000,
            user_id=test_user_id,
        )
        db_session.add(video)
        db_session.commit()

        # Create pose detection with pending status
        pose_detection = PoseDetection(
            video_id=video.id,
            status="processing",
            total_frames=1,
            pose_data=json.dumps([{}]),
            confidence_scores=json.dumps([0.9]),
        )
        db_session.add(pose_detection)
        db_session.commit()

        # Make request
        response = client.get(
            f"/v0/videos/{video.id}/overlay-data",
        )

        assert response.status_code == 400
        assert "not completed" in response.json()["detail"]

    def test_get_overlay_data_no_pose_data(
        self, client: TestClient, db_session: Session, test_user_id: str
    ) -> None:
        """Test overlay data when pose_data is None."""
        # Create a video
        video = Video(
            filename="test.mp4",
            file_path="test.mp4",
            file_size=1000000,
            user_id=test_user_id,
        )
        db_session.add(video)
        db_session.commit()

        # Create pose detection without pose_data
        pose_detection = PoseDetection(
            video_id=video.id,
            status="completed",
            total_frames=1,
            pose_data=None,
            confidence_scores=None,
        )
        db_session.add(pose_detection)
        db_session.commit()

        # Make request
        response = client.get(
            f"/v0/videos/{video.id}/overlay-data",
        )

        assert response.status_code == 404
        assert "No pose data available" in response.json()["detail"]

    def test_get_overlay_data_default_fps(
        self, client: TestClient, db_session: Session, test_user_id: str
    ) -> None:
        """Test overlay data with invalid FPS (should default to 30.0)."""
        # Create a video with invalid FPS
        video = Video(
            filename="test.mp4",
            file_path="test.mp4",
            file_size=1000000,
            fps=0,  # Invalid FPS
            user_id=test_user_id,
        )
        db_session.add(video)
        db_session.commit()

        # Create pose detection
        pose_data = [{"left_shoulder": [100.0, 200.0]}]
        pose_detection = PoseDetection(
            video_id=video.id,
            status="completed",
            total_frames=1,
            pose_data=json.dumps(pose_data),
            confidence_scores=json.dumps([0.9]),
        )
        db_session.add(pose_detection)
        db_session.commit()

        # Make request
        response = client.get(
            f"/v0/videos/{video.id}/overlay-data",
        )

        assert response.status_code == 200
        data = response.json()
        assert data["fps"] == 30.0  # Should default to 30.0
