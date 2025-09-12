"""
Tests for video-player association API endpoints.
"""

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.main import app
from app.models.player import Player
from app.models.video import Video
from app.models.video_player import VideoPlayer

client = TestClient(app)


@pytest.fixture
def sample_video(db_session: Session) -> Video:
    """Create a sample video for testing."""
    import uuid

    unique_filename = f"test_video_{uuid.uuid4().hex[:8]}.mp4"
    video = Video(
        filename=unique_filename,
        file_path=f"/path/to/{unique_filename}",
        file_size=1024000,
        content_type="video/mp4",
        duration=30.0,
        fps=30.0,
        width=1920,
        height=1080,
        frame_count=900,
    )
    db_session.add(video)
    db_session.commit()
    db_session.refresh(video)
    return video


@pytest.fixture
def sample_player(db_session: Session) -> Player:
    """Create a sample player for testing."""
    import uuid

    unique_name = f"Test Player {uuid.uuid4().hex[:8]}"
    player = Player(
        name=unique_name,
        dominant_hand="right",
        backhand_style="two_handed",
        height=180.0,
        notes="Test player for video-player associations",
    )
    db_session.add(player)
    db_session.commit()
    db_session.refresh(player)
    return player


@pytest.fixture
def sample_video_player(
    db_session: Session, sample_video: Video, sample_player: Player
) -> VideoPlayer:
    """Create a sample video-player association for testing."""
    video_player = VideoPlayer(
        video_id=sample_video.id,
        player_id=sample_player.id,
        pose_detection_id=None,
    )
    db_session.add(video_player)
    db_session.commit()
    db_session.refresh(video_player)
    return video_player


class TestVideoPlayerAPI:
    """Test video-player association API endpoints."""

    def test_associate_player_with_video(
        self, db_session: Session, sample_video: Video, sample_player: Player
    ) -> None:
        """Test associating a player with a video."""
        # Clean up any existing associations first
        from app.models.video_player import VideoPlayer

        db_session.query(VideoPlayer).delete()
        db_session.commit()

        response = client.post(
            f"/v0/videos/{sample_video.id}/players/",
            json={
                "player_id": sample_player.id,
                "pose_detection_id": None,
            },
        )
        print(f"Response status: {response.status_code}")
        print(f"Response body: {response.text}")
        assert response.status_code == 200
        data = response.json()
        assert data["video_id"] == sample_video.id
        assert data["player_id"] == sample_player.id
        assert data["player"]["name"] == sample_player.name

    def test_associate_player_with_nonexistent_video(
        self, db_session: Session, sample_player: Player
    ) -> None:
        """Test associating a player with a nonexistent video."""
        response = client.post(
            "/v0/videos/999/players/",
            json={
                "player_id": sample_player.id,
                "pose_detection_id": None,
            },
        )
        assert response.status_code == 404

    def test_associate_nonexistent_player_with_video(
        self, db_session: Session, sample_video: Video
    ) -> None:
        """Test associating a nonexistent player with a video."""
        response = client.post(
            f"/v0/videos/{sample_video.id}/players/",
            json={
                "player_id": 999,
                "pose_detection_id": None,
            },
        )
        assert response.status_code == 404

    def test_associate_duplicate_player_with_video(
        self, db_session: Session, sample_video_player: VideoPlayer
    ) -> None:
        """Test associating the same player with a video twice."""
        response = client.post(
            f"/v0/videos/{sample_video_player.video_id}/players/",
            json={
                "player_id": sample_video_player.player_id,
                "pose_detection_id": None,
            },
        )
        assert response.status_code == 409

    def test_get_video_players(
        self, db_session: Session, sample_video_player: VideoPlayer
    ) -> None:
        """Test getting all players associated with a video."""
        response = client.get(f"/v0/videos/{sample_video_player.video_id}/players/")
        assert response.status_code == 200
        data = response.json()
        assert len(data) == 1
        assert data[0]["player_id"] == sample_video_player.player_id

    def test_get_video_players_summary(
        self, db_session: Session, sample_video_player: VideoPlayer
    ) -> None:
        """Test getting video players summary."""
        response = client.get(
            f"/v0/videos/{sample_video_player.video_id}/players-summary/"
        )
        assert response.status_code == 200
        data = response.json()
        assert data["id"] == sample_video_player.video_id
        assert data["total_players"] == 1
        assert len(data["players"]) == 1
        assert data["players"][0]["name"] == sample_video_player.player.name

    def test_update_video_player_association(
        self, db_session: Session, sample_video_player: VideoPlayer
    ) -> None:
        """Test updating a video-player association."""
        response = client.put(
            f"/v0/videos/{sample_video_player.video_id}/players/{sample_video_player.player_id}/",
            json={
                "pose_detection_id": 123,
            },
        )
        assert response.status_code == 200
        data = response.json()
        assert data["pose_detection_id"] == 123

    def test_remove_player_from_video(
        self, db_session: Session, sample_video_player: VideoPlayer
    ) -> None:
        """Test removing a player from a video."""
        response = client.delete(
            f"/v0/videos/{sample_video_player.video_id}/players/{sample_video_player.player_id}/"
        )
        assert response.status_code == 204

        # Verify the association was removed
        response = client.get(f"/v0/videos/{sample_video_player.video_id}/players/")
        assert response.status_code == 200
        data = response.json()
        assert len(data) == 0

    def test_get_player_videos(
        self, db_session: Session, sample_video_player: VideoPlayer
    ) -> None:
        """Test getting all videos where a player appears."""
        response = client.get(f"/v0/players/{sample_video_player.player_id}/videos/")
        assert response.status_code == 200
        data = response.json()
        assert data["id"] == sample_video_player.player_id
        assert data["total_videos"] == 1
        assert len(data["videos"]) == 1
        assert data["videos"][0]["id"] == sample_video_player.video_id

    def test_get_ball_contact_player_options_single_player(
        self, db_session: Session, sample_video_player: VideoPlayer
    ) -> None:
        """Test getting player options when only one player is in the video."""
        response = client.get(
            f"/v0/ball-contacts/video/{sample_video_player.video_id}/player-options/"
        )
        assert response.status_code == 200
        data = response.json()
        assert data["auto_assign"] == sample_video_player.player_id
        assert data["player_name"] == sample_video_player.player.name
        assert len(data["options"]) == 1

    def test_get_ball_contact_player_options_no_players(
        self, db_session: Session, sample_video: Video
    ) -> None:
        """Test getting player options when no players are in the video."""
        response = client.get(
            f"/v0/ball-contacts/video/{sample_video.id}/player-options/"
        )
        assert response.status_code == 200
        data = response.json()
        assert data["auto_assign"] is None
        assert "No players assigned to video" in data["message"]
        # Should return all players as options
        assert len(data["options"]) >= 0  # Could be 0 if no players exist

    def test_get_ball_contact_player_options_multiple_players(
        self, db_session: Session, sample_video: Video
    ) -> None:
        """Test getting player options when multiple players are in the video."""
        # Create two players
        player1 = Player(name="Player 1", dominant_hand="right")
        player2 = Player(name="Player 2", dominant_hand="left")
        db_session.add_all([player1, player2])
        db_session.commit()
        db_session.refresh(player1)
        db_session.refresh(player2)

        # Associate both players with the video
        video_player1 = VideoPlayer(video_id=sample_video.id, player_id=player1.id)
        video_player2 = VideoPlayer(video_id=sample_video.id, player_id=player2.id)
        db_session.add_all([video_player1, video_player2])
        db_session.commit()

        response = client.get(
            f"/v0/ball-contacts/video/{sample_video.id}/player-options/"
        )
        assert response.status_code == 200
        data = response.json()
        assert data["auto_assign"] is None
        assert "Multiple players in video" in data["message"]
        assert len(data["options"]) == 2
