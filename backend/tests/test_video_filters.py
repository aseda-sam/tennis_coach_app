"""Tests for video library filter functionality."""

import uuid
from typing import Generator

import pytest
from fastapi.testclient import TestClient

from app.models.player import Player
from app.models.video import Video


class TestVideoFilters:
    """Tests for GET /v0/videos/ filter query params."""

    @pytest.fixture(autouse=True)
    def seed_videos(self, db_session: Generator) -> None:
        """Create a diverse set of videos for filter testing."""
        # Create player records for FK references
        player1 = Player(
            id=1,
            name="Alice",
            dominant_hand="right",
            user_id="00000000-0000-0000-0000-000000000000",
        )
        player2 = Player(
            id=2,
            name="Bob",
            dominant_hand="left",
            user_id="00000000-0000-0000-0000-000000000000",
        )
        db_session.add_all([player1, player2])
        db_session.flush()

        self.videos = []
        user_id = "00000000-0000-0000-0000-000000000000"

        configs = [
            {
                "camera_angle": "behind",
                "session_type": "serve_practice",
                "status": "completed",
                "primary_player_id": 1,
            },
            {
                "camera_angle": "behind",
                "session_type": "match",
                "status": "processing",
                "primary_player_id": 1,
            },
            {
                "camera_angle": "profile",
                "session_type": "serve_practice",
                "status": "completed",
                "primary_player_id": 2,
            },
            {
                "camera_angle": "profile",
                "session_type": "other",
                "status": "uploaded",
                "primary_player_id": None,
            },
            {
                "camera_angle": "unknown",
                "session_type": "match",
                "status": "failed",
                "primary_player_id": 2,
            },
        ]

        for i, cfg in enumerate(configs):
            video = Video(
                filename=f"test_filter_{uuid.uuid4().hex[:8]}.mp4",
                file_path=f"/videos/test_{i}.mp4",
                file_size=1000,
                user_id=user_id,
                camera_angle=cfg["camera_angle"],
                session_type=cfg["session_type"],
                status=cfg["status"],
                primary_player_id=cfg["primary_player_id"],
            )
            db_session.add(video)
            self.videos.append(video)

        db_session.commit()

    def test_no_filters_returns_all(self, client: TestClient) -> None:
        response = client.get("/v0/videos/")
        assert response.status_code == 200
        assert len(response.json()) == 5

    def test_filter_by_camera_angle(self, client: TestClient) -> None:
        response = client.get("/v0/videos/?camera_angle=behind")
        assert response.status_code == 200
        data = response.json()
        assert len(data) == 2
        assert all(v["camera_angle"] == "behind" for v in data)

    def test_filter_by_camera_angle_profile(self, client: TestClient) -> None:
        response = client.get("/v0/videos/?camera_angle=profile")
        assert response.status_code == 200
        assert len(response.json()) == 2

    def test_filter_by_player_id(self, client: TestClient) -> None:
        response = client.get("/v0/videos/?player_id=1")
        assert response.status_code == 200
        data = response.json()
        assert len(data) == 2
        assert all(v["primary_player_id"] == 1 for v in data)

    def test_combined_filters(self, client: TestClient) -> None:
        response = client.get("/v0/videos/?camera_angle=behind&player_id=1")
        assert response.status_code == 200
        data = response.json()
        assert len(data) == 2
        assert all(v["camera_angle"] == "behind" for v in data)
        assert all(v["primary_player_id"] == 1 for v in data)

    def test_exclude_player_id(self, client: TestClient) -> None:
        """exclude_player_id returns videos NOT belonging to that player."""
        response = client.get("/v0/videos/?exclude_player_id=1")
        assert response.status_code == 200
        data = response.json()
        # Videos with player_id=2 (indices 2, 4). player_id=None (index 3) excluded.
        assert len(data) == 2
        assert all(v["primary_player_id"] != 1 for v in data)
        assert all(v["primary_player_id"] is not None for v in data)

    def test_invalid_camera_angle_returns_422(self, client: TestClient) -> None:
        response = client.get("/v0/videos/?camera_angle=invalid")
        assert response.status_code == 422

    def test_filter_with_no_matches_returns_empty(self, client: TestClient) -> None:
        response = client.get("/v0/videos/?camera_angle=profile&player_id=1")
        assert response.status_code == 200
        assert len(response.json()) == 0
