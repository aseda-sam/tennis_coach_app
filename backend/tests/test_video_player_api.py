"""Tests for Video-Player association API endpoints."""

from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.models.video import Video


class TestVideoPlayerAPI:
    """Test cases for Video-Player association API endpoints."""

    def test_associate_player_with_video(
        self, client: TestClient, db_session: Session, test_user_id: str
    ) -> None:
        """Test associating a player with a video."""
        # Create player through API
        player_data = {
            "name": "Test Player",
            "dominant_hand": "right",
            "backhand_style": "two_handed",
        }
        player_response = client.post("/v0/players/", json=player_data)
        player_id = player_response.json()["id"]

        # Create video directly in database
        test_video = Video(
            filename="test_video.mp4",
            file_path="/path/to/test_video.mp4",
            file_size=1000000,
            duration=60.0,
            width=1920,
            height=1080,
            status="uploaded",
            user_id=test_user_id,
        )
        db_session.add(test_video)
        db_session.commit()
        video_id = test_video.id

        # Associate player with video
        association_data = {
            "player_id": player_id,
            "pose_detection_id": None,
        }

        response = client.post(f"/v0/videos/{video_id}/players/", json=association_data)

        assert response.status_code == 200
        data = response.json()
        assert data["video_id"] == video_id
        assert data["player_id"] == player_id
        assert data["player"]["name"] == "Test Player"

    def test_associate_player_with_nonexistent_video(
        self, client: TestClient, db_session: Session
    ) -> None:
        """Test associating a player with a nonexistent video."""
        # Create player through API
        player_data = {
            "name": "Test Player",
            "dominant_hand": "right",
        }
        player_response = client.post("/v0/players/", json=player_data)
        player_id = player_response.json()["id"]

        # Try to associate with nonexistent video
        association_data = {
            "player_id": player_id,
            "pose_detection_id": None,
        }

        response = client.post("/v0/videos/999/players/", json=association_data)

        assert response.status_code == 404

    def test_associate_nonexistent_player_with_video(
        self, client: TestClient, db_session: Session, test_user_id: str
    ) -> None:
        """Test associating a nonexistent player with a video."""
        # Create video directly in database
        test_video = Video(
            filename="test_video.mp4",
            file_path="/path/to/test_video.mp4",
            file_size=1000000,
            duration=60.0,
            width=1920,
            height=1080,
            status="uploaded",
            user_id=test_user_id,
        )
        db_session.add(test_video)
        db_session.commit()
        video_id = test_video.id

        # Try to associate nonexistent player
        association_data = {
            "player_id": 999,
            "pose_detection_id": None,
        }

        response = client.post(f"/v0/videos/{video_id}/players/", json=association_data)

        assert response.status_code == 404

    def test_associate_duplicate_player_with_video(
        self, client: TestClient, db_session: Session, test_user_id: str
    ) -> None:
        """Test associating the same player with a video twice."""
        # Create player through API
        player_data = {
            "name": "Test Player",
            "dominant_hand": "right",
        }
        player_response = client.post("/v0/players/", json=player_data)
        player_id = player_response.json()["id"]

        # Create video directly in database
        test_video = Video(
            filename="test_video.mp4",
            file_path="/path/to/test_video.mp4",
            file_size=1000000,
            duration=60.0,
            width=1920,
            height=1080,
            status="uploaded",
            user_id=test_user_id,
        )
        db_session.add(test_video)
        db_session.commit()
        video_id = test_video.id

        # First association should succeed
        association_data = {
            "player_id": player_id,
            "pose_detection_id": None,
        }

        response1 = client.post(
            f"/v0/videos/{video_id}/players/", json=association_data
        )
        assert response1.status_code == 200

        # Second association should fail
        response2 = client.post(
            f"/v0/videos/{video_id}/players/", json=association_data
        )
        assert response2.status_code == 409

    def test_get_video_players(
        self, client: TestClient, db_session: Session, test_user_id: str
    ) -> None:
        """Test getting all players associated with a video."""
        # Create player through API
        player_data = {
            "name": "Test Player",
            "dominant_hand": "right",
        }
        player_response = client.post("/v0/players/", json=player_data)
        player_id = player_response.json()["id"]

        # Create video directly in database
        test_video = Video(
            filename="test_video.mp4",
            file_path="/path/to/test_video.mp4",
            file_size=1000000,
            duration=60.0,
            width=1920,
            height=1080,
            status="uploaded",
            user_id=test_user_id,
        )
        db_session.add(test_video)
        db_session.commit()
        video_id = test_video.id

        # Associate player with video
        association_data = {
            "player_id": player_id,
            "pose_detection_id": None,
        }
        client.post(f"/v0/videos/{video_id}/players/", json=association_data)

        # Get video players
        response = client.get(f"/v0/videos/{video_id}/players/")

        assert response.status_code == 200
        data = response.json()
        assert len(data) == 1
        assert data[0]["player_id"] == player_id

    def test_get_video_players_summary(
        self, client: TestClient, db_session: Session, test_user_id: str
    ) -> None:
        """Test getting video players summary."""
        # Create player through API
        player_data = {
            "name": "Test Player",
            "dominant_hand": "right",
        }
        player_response = client.post("/v0/players/", json=player_data)
        player_id = player_response.json()["id"]

        # Create video directly in database
        test_video = Video(
            filename="test_video.mp4",
            file_path="/path/to/test_video.mp4",
            file_size=1000000,
            duration=60.0,
            width=1920,
            height=1080,
            status="uploaded",
            user_id=test_user_id,
        )
        db_session.add(test_video)
        db_session.commit()
        video_id = test_video.id

        # Associate player with video
        association_data = {
            "player_id": player_id,
            "pose_detection_id": None,
        }
        client.post(f"/v0/videos/{video_id}/players/", json=association_data)

        # Get video players summary
        response = client.get(f"/v0/videos/{video_id}/players-summary/")

        assert response.status_code == 200
        data = response.json()
        assert data["id"] == video_id
        assert data["total_players"] == 1
        assert len(data["players"]) == 1
        assert data["players"][0]["name"] == "Test Player"

    def test_update_video_player_association(
        self, client: TestClient, db_session: Session, test_user_id: str
    ) -> None:
        """Test updating a video-player association."""
        # Create player through API
        player_data = {
            "name": "Test Player",
            "dominant_hand": "right",
        }
        player_response = client.post("/v0/players/", json=player_data)
        player_id = player_response.json()["id"]

        # Create video directly in database
        test_video = Video(
            filename="test_video.mp4",
            file_path="/path/to/test_video.mp4",
            file_size=1000000,
            duration=60.0,
            width=1920,
            height=1080,
            status="uploaded",
            user_id=test_user_id,
        )
        db_session.add(test_video)
        db_session.commit()
        video_id = test_video.id

        # Associate player with video
        association_data = {
            "player_id": player_id,
            "pose_detection_id": None,
        }
        client.post(f"/v0/videos/{video_id}/players/", json=association_data)

        # Update association
        update_data = {"pose_detection_id": 123}

        response = client.put(
            f"/v0/videos/{video_id}/players/{player_id}/", json=update_data
        )

        assert response.status_code == 200
        data = response.json()
        assert data["pose_detection_id"] == 123

    def test_remove_player_from_video(
        self, client: TestClient, db_session: Session, test_user_id: str
    ) -> None:
        """Test removing a player from a video."""
        # Create player through API
        player_data = {
            "name": "Test Player",
            "dominant_hand": "right",
        }
        player_response = client.post("/v0/players/", json=player_data)
        player_id = player_response.json()["id"]

        # Create video directly in database
        test_video = Video(
            filename="test_video.mp4",
            file_path="/path/to/test_video.mp4",
            file_size=1000000,
            duration=60.0,
            width=1920,
            height=1080,
            status="uploaded",
            user_id=test_user_id,
        )
        db_session.add(test_video)
        db_session.commit()
        video_id = test_video.id

        # Associate player with video
        association_data = {
            "player_id": player_id,
            "pose_detection_id": None,
        }
        client.post(f"/v0/videos/{video_id}/players/", json=association_data)

        # Remove player from video
        response = client.delete(f"/v0/videos/{video_id}/players/{player_id}/")

        assert response.status_code == 204

        # Verify the association was removed
        response = client.get(f"/v0/videos/{video_id}/players/")
        assert response.status_code == 200
        data = response.json()
        assert len(data) == 0

    def test_get_player_videos(
        self, client: TestClient, db_session: Session, test_user_id: str
    ) -> None:
        """Test getting all videos where a player appears."""
        # Create player through API
        player_data = {
            "name": "Test Player",
            "dominant_hand": "right",
        }
        player_response = client.post("/v0/players/", json=player_data)
        player_id = player_response.json()["id"]

        # Create video directly in database
        test_video = Video(
            filename="test_video.mp4",
            file_path="/path/to/test_video.mp4",
            file_size=1000000,
            duration=60.0,
            width=1920,
            height=1080,
            status="uploaded",
            user_id=test_user_id,
        )
        db_session.add(test_video)
        db_session.commit()
        video_id = test_video.id

        # Associate player with video
        association_data = {
            "player_id": player_id,
            "pose_detection_id": None,
        }
        client.post(f"/v0/videos/{video_id}/players/", json=association_data)

        # Get player videos
        response = client.get(f"/v0/players/{player_id}/videos/")

        assert response.status_code == 200
        data = response.json()
        assert data["id"] == player_id
        assert data["total_videos"] == 1
        assert len(data["videos"]) == 1
        assert data["videos"][0]["id"] == video_id
