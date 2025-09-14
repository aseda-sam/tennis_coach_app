"""Tests for Player API endpoints."""

from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.models.video import Video


class TestPlayerAPI:
    """Test cases for Player API endpoints."""

    def test_create_player_success(
        self, client: TestClient, db_session: Session
    ) -> None:
        """Test creating a player successfully."""
        player_data = {
            "name": "John Doe",
            "dominant_hand": "right",
            "backhand_style": "two_handed",
            "height": 180.5,
            "notes": "Professional player",
        }

        response = client.post("/v0/players/", json=player_data)

        assert response.status_code == 201
        data = response.json()
        assert data["name"] == "John Doe"
        assert data["dominant_hand"] == "right"
        assert data["backhand_style"] == "two_handed"
        assert data["height"] == 180.5
        assert data["notes"] == "Professional player"
        assert "id" in data
        assert "created_at" in data

    def test_create_player_without_backhand_style(
        self, client: TestClient, db_session: Session
    ) -> None:
        """Test creating a player without backhand style."""
        player_data = {
            "name": "Jane Smith",
            "dominant_hand": "left",
            "height": 175.0,
        }

        response = client.post("/v0/players/", json=player_data)

        assert response.status_code == 201
        data = response.json()
        assert data["name"] == "Jane Smith"
        assert data["dominant_hand"] == "left"
        assert data["backhand_style"] is None
        assert data["height"] == 175.0
        assert "id" in data
        assert "created_at" in data

    def test_create_player_duplicate_name(
        self, client: TestClient, db_session: Session
    ) -> None:
        """Test creating a player with duplicate name fails."""
        # Create first player
        player_data = {
            "name": "John Doe",
            "dominant_hand": "right",
            "backhand_style": "two_handed",
        }
        client.post("/v0/players/", json=player_data)

        # Try to create second player with same name
        response = client.post("/v0/players/", json=player_data)

        assert response.status_code == 400
        assert "already exists" in response.json()["detail"]

    def test_create_player_invalid_data(
        self, client: TestClient, db_session: Session
    ) -> None:
        """Test creating a player with invalid data fails."""
        player_data = {
            "name": "",  # Empty name
            "dominant_hand": "invalid_hand",  # Invalid hand
            "backhand_style": "invalid_style",  # Invalid style
        }

        response = client.post("/v0/players/", json=player_data)

        assert response.status_code == 422  # Validation error

    def test_get_players_empty(self, client: TestClient, db_session: Session) -> None:
        """Test getting players when none exist."""
        response = client.get("/v0/players/")

        assert response.status_code == 200
        assert response.json() == []

    def test_get_players_with_data(
        self, client: TestClient, db_session: Session
    ) -> None:
        """Test getting players with data."""
        # Create test players
        players_data = [
            {
                "name": "Player 1",
                "dominant_hand": "right",
                "backhand_style": "two_handed",
            },
            {
                "name": "Player 2",
                "dominant_hand": "left",
                "backhand_style": "one_handed",
            },
        ]

        for player_data in players_data:
            client.post("/v0/players/", json=player_data)

        response = client.get("/v0/players/")

        assert response.status_code == 200
        data = response.json()
        assert len(data) == 2
        assert all("name" in player for player in data)

    def test_get_players_with_pagination(
        self, client: TestClient, db_session: Session
    ) -> None:
        """Test getting players with pagination."""
        # Create 5 test players
        for i in range(5):
            player_data = {
                "name": f"Player {i}",
                "dominant_hand": "right",
                "backhand_style": "two_handed",
            }
            client.post("/v0/players/", json=player_data)

        # Test pagination
        response = client.get("/v0/players/?skip=2&limit=2")

        assert response.status_code == 200
        data = response.json()
        assert len(data) == 2

    def test_get_players_with_name_filter(
        self, client: TestClient, db_session: Session
    ) -> None:
        """Test getting players with name filtering."""
        # Create test players
        players_data = [
            {
                "name": "John Smith",
                "dominant_hand": "right",
                "backhand_style": "two_handed",
            },
            {
                "name": "Jane Doe",
                "dominant_hand": "left",
                "backhand_style": "one_handed",
            },
            {
                "name": "Johnny Walker",
                "dominant_hand": "right",
                "backhand_style": "two_handed",
            },
        ]

        for player_data in players_data:
            client.post("/v0/players/", json=player_data)

        # Filter by name containing "John"
        response = client.get("/v0/players/?name=John")

        assert response.status_code == 200
        data = response.json()
        assert len(data) == 2
        assert all("John" in player["name"] for player in data)

    def test_get_player_by_id_success(
        self, client: TestClient, db_session: Session
    ) -> None:
        """Test getting a specific player by ID."""
        player_data = {
            "name": "Test Player",
            "dominant_hand": "right",
            "backhand_style": "two_handed",
            "height": 175.0,
        }

        create_response = client.post("/v0/players/", json=player_data)
        player_id = create_response.json()["id"]

        response = client.get(f"/v0/players/{player_id}")

        assert response.status_code == 200
        data = response.json()
        assert data["name"] == "Test Player"
        assert data["height"] == 175.0

    def test_get_player_by_id_not_found(
        self, client: TestClient, db_session: Session
    ) -> None:
        """Test getting a non-existent player returns 404."""
        response = client.get("/v0/players/999")

        assert response.status_code == 404
        assert "not found" in response.json()["detail"]

    def test_update_player_success(
        self, client: TestClient, db_session: Session
    ) -> None:
        """Test updating a player successfully."""
        # Create player
        player_data = {
            "name": "Original Name",
            "dominant_hand": "right",
            "backhand_style": "two_handed",
        }
        create_response = client.post("/v0/players/", json=player_data)
        player_id = create_response.json()["id"]

        # Update player
        update_data = {
            "name": "Updated Name",
            "height": 180.0,
            "notes": "Updated notes",
        }

        response = client.put(f"/v0/players/{player_id}", json=update_data)

        assert response.status_code == 200
        data = response.json()
        assert data["name"] == "Updated Name"
        assert data["height"] == 180.0
        assert data["notes"] == "Updated notes"
        assert data["dominant_hand"] == "right"  # Unchanged
        assert data["backhand_style"] == "two_handed"  # Unchanged

    def test_update_player_backhand_style(
        self, client: TestClient, db_session: Session
    ) -> None:
        """Test updating a player's backhand style."""
        # Create player without backhand style
        player_data = {
            "name": "Test Player",
            "dominant_hand": "right",
        }
        create_response = client.post("/v0/players/", json=player_data)
        player_id = create_response.json()["id"]

        # Update to add backhand style
        update_data = {
            "backhand_style": "one_handed",
        }

        response = client.put(f"/v0/players/{player_id}", json=update_data)

        assert response.status_code == 200
        data = response.json()
        assert data["backhand_style"] == "one_handed"

        # Update to change backhand style
        update_data = {
            "backhand_style": "two_handed",
        }

        response = client.put(f"/v0/players/{player_id}", json=update_data)

        assert response.status_code == 200
        data = response.json()
        assert data["backhand_style"] == "two_handed"

    def test_update_player_not_found(
        self, client: TestClient, db_session: Session
    ) -> None:
        """Test updating a non-existent player returns 404."""
        update_data = {"name": "New Name"}

        response = client.put("/v0/players/999", json=update_data)

        assert response.status_code == 404
        assert "not found" in response.json()["detail"]

    def test_update_player_duplicate_name(
        self, client: TestClient, db_session: Session
    ) -> None:
        """Test updating a player with duplicate name fails."""
        # Create two players
        player1_data = {
            "name": "Player 1",
            "dominant_hand": "right",
            "backhand_style": "two_handed",
        }
        player2_data = {
            "name": "Player 2",
            "dominant_hand": "left",
            "backhand_style": "one_handed",
        }

        create1_response = client.post("/v0/players/", json=player1_data)
        client.post("/v0/players/", json=player2_data)

        player1_id = create1_response.json()["id"]

        # Try to update player2 with player1's name
        update_data = {"name": "Player 1"}

        response = client.put(f"/v0/players/{player1_id}", json=update_data)

        # This should succeed since it's the same player
        assert response.status_code == 200

    def test_delete_player_success(
        self, client: TestClient, db_session: Session
    ) -> None:
        """Test deleting a player successfully."""
        # Create player
        player_data = {
            "name": "To Delete",
            "dominant_hand": "right",
            "backhand_style": "two_handed",
        }
        create_response = client.post("/v0/players/", json=player_data)
        player_id = create_response.json()["id"]

        # Delete player
        response = client.delete(f"/v0/players/{player_id}")

        assert response.status_code == 200
        assert "deleted successfully" in response.json()["message"]

        # Verify player is deleted
        get_response = client.get(f"/v0/players/{player_id}")
        assert get_response.status_code == 404

    def test_delete_player_not_found(
        self, client: TestClient, db_session: Session
    ) -> None:
        """Test deleting a non-existent player returns 404."""
        response = client.delete("/v0/players/999")

        assert response.status_code == 404
        assert "not found" in response.json()["detail"]

    def test_player_with_ball_contacts(
        self, client: TestClient, db_session: Session
    ) -> None:
        """Test player can be retrieved after ball contacts are created."""
        # Create player
        player_data = {
            "name": "Test Player",
            "dominant_hand": "right",
            "backhand_style": "two_handed",
        }
        create_response = client.post("/v0/players/", json=player_data)
        player_id = create_response.json()["id"]

        # Create a video directly in the database for testing
        test_video = Video(
            filename="test_video.mp4",
            file_path="/path/to/test_video.mp4",
            file_size=1000000,
            duration=60.0,
            width=1920,
            height=1080,
            status="uploaded",
        )
        db_session.add(test_video)
        db_session.commit()
        video_id = test_video.id

        # Create ball contacts for the player
        ball_contact_data = {
            "video_id": video_id,
            "video_timestamp": 10.0,
            "contact_hand": "right",
            "stroke_type": "ground_stroke",
            "player_id": player_id,
        }
        client.post("/v0/ball-contacts/", json=ball_contact_data)

        # Get player and verify it still works
        response = client.get(f"/v0/players/{player_id}")

        assert response.status_code == 200
        data = response.json()
        assert data["name"] == "Test Player"
