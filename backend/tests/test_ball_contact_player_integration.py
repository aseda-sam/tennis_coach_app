"""Tests for BallContact-Player integration."""

from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.models.video import Video


class TestBallContactPlayerIntegration:
    """Test cases for BallContact-Player integration."""

    def test_create_ball_contact_with_player(
        self, client: TestClient, db_session: Session, test_user_id: str
    ) -> None:
        """Test creating a ball contact with a player."""
        # Create player
        player_data = {
            "name": "Test Player",
            "dominant_hand": "right",
            "backhand_style": "two_handed",
        }
        player_response = client.post("/v0/players/", json=player_data)
        player_id = player_response.json()["id"]

        # Create video directly in the database for testing
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

        # Create ball contact with player
        ball_contact_data = {
            "video_id": video_id,
            "video_timestamp": 1.0,
            "contact_hand": "right",
            "stroke_type": "ground_stroke",
            "player_id": player_id,
        }

        response = client.post("/v0/ball-contacts/", json=ball_contact_data)

        assert response.status_code == 201
        data = response.json()
        assert data["player_id"] == player_id
        assert data["player"]["name"] == "Test Player"
        assert data["player"]["dominant_hand"] == "right"

    def test_create_ball_contact_with_player_no_backhand_style(
        self, client: TestClient, db_session: Session, test_user_id: str
    ) -> None:
        """Test creating a ball contact with a player who has no backhand style."""
        # Create player without backhand style
        player_data = {
            "name": "Test Player No Backhand",
            "dominant_hand": "left",
        }
        player_response = client.post("/v0/players/", json=player_data)
        player_id = player_response.json()["id"]

        # Create video directly in the database for testing
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

        # Create ball contact with player
        ball_contact_data = {
            "video_id": video_id,
            "video_timestamp": 1.0,
            "contact_hand": "left",
            "stroke_type": "ground_stroke",
            "player_id": player_id,
        }

        response = client.post("/v0/ball-contacts/", json=ball_contact_data)

        assert response.status_code == 201
        data = response.json()
        assert data["player_id"] == player_id
        assert data["player"]["name"] == "Test Player No Backhand"
        assert data["player"]["dominant_hand"] == "left"

    def test_create_ball_contact_without_player(
        self, client: TestClient, db_session: Session, test_user_id: str
    ) -> None:
        """Test creating a ball contact without a player."""
        # Create video directly in the database for testing
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

        # Create ball contact without player
        ball_contact_data = {
            "video_id": video_id,
            "video_timestamp": 1.0,
            "contact_hand": "right",
            "stroke_type": "ground_stroke",
        }

        response = client.post("/v0/ball-contacts/", json=ball_contact_data)

        assert response.status_code == 201
        data = response.json()
        assert data["player_id"] is None
        assert data["player"] is None

    def test_create_ball_contact_invalid_player(
        self, client: TestClient, db_session: Session, test_user_id: str
    ) -> None:
        """Test creating a ball contact with invalid player ID fails."""
        # Create video directly in the database for testing
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

        # Create ball contact with invalid player ID
        ball_contact_data = {
            "video_id": video_id,
            "video_timestamp": 1.0,
            "contact_hand": "right",
            "stroke_type": "ground_stroke",
            "player_id": 999,  # Non-existent player
        }

        response = client.post("/v0/ball-contacts/", json=ball_contact_data)

        assert response.status_code == 400
        assert "not found" in response.json()["detail"]

    def test_update_ball_contact_player(
        self, client: TestClient, db_session: Session, test_user_id: str
    ) -> None:
        """Test updating a ball contact's player assignment."""
        # Create players
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

        player1_response = client.post("/v0/players/", json=player1_data)
        player2_response = client.post("/v0/players/", json=player2_data)
        player1_id = player1_response.json()["id"]
        player2_id = player2_response.json()["id"]

        # Create video directly in the database for testing
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

        # Create ball contact with first player
        ball_contact_data = {
            "video_id": video_id,
            "video_timestamp": 1.0,
            "contact_hand": "right",
            "stroke_type": "ground_stroke",
            "player_id": player1_id,
        }
        create_response = client.post("/v0/ball-contacts/", json=ball_contact_data)
        ball_contact_id = create_response.json()["id"]

        # Update to second player
        update_data = {"player_id": player2_id}
        response = client.put(f"/v0/ball-contacts/{ball_contact_id}", json=update_data)

        assert response.status_code == 200
        data = response.json()
        assert data["player_id"] == player2_id
        assert data["player"]["name"] == "Player 2"

    def test_update_ball_contact_remove_player(
        self, client: TestClient, db_session: Session, test_user_id: str
    ) -> None:
        """Test updating a ball contact to remove player assignment."""
        # Create player
        player_data = {
            "name": "Test Player",
            "dominant_hand": "right",
            "backhand_style": "two_handed",
        }
        player_response = client.post("/v0/players/", json=player_data)
        player_id = player_response.json()["id"]

        # Create video directly in the database for testing
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

        # Create ball contact with player
        ball_contact_data = {
            "video_id": video_id,
            "video_timestamp": 1.0,
            "contact_hand": "right",
            "stroke_type": "ground_stroke",
            "player_id": player_id,
        }
        create_response = client.post("/v0/ball-contacts/", json=ball_contact_data)
        ball_contact_id = create_response.json()["id"]

        # Remove player assignment
        update_data = {"player_id": None}
        response = client.put(f"/v0/ball-contacts/{ball_contact_id}", json=update_data)

        assert response.status_code == 200
        data = response.json()
        assert data["player_id"] is None
        assert data["player"] is None

    def test_get_ball_contacts_by_player(
        self, client: TestClient, db_session: Session, test_user_id: str
    ) -> None:
        """Test getting ball contacts by player ID."""
        # Create player
        player_data = {
            "name": "Test Player",
            "dominant_hand": "right",
            "backhand_style": "two_handed",
        }
        player_response = client.post("/v0/players/", json=player_data)
        player_id = player_response.json()["id"]

        # Create video directly in the database for testing
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

        # Create ball contacts for the player
        ball_contacts_data = [
            {
                "video_id": video_id,
                "video_timestamp": 1.0,
                "contact_hand": "right",
                "stroke_type": "ground_stroke",
                "player_id": player_id,
            },
            {
                "video_id": video_id,
                "video_timestamp": 20.0,
                "contact_hand": "left",
                "stroke_type": "volley",
                "player_id": player_id,
            },
        ]

        for ball_contact_data in ball_contacts_data:
            client.post("/v0/ball-contacts/", json=ball_contact_data)

        # Get ball contacts by player
        response = client.get(f"/v0/ball-contacts/player/{player_id}")

        assert response.status_code == 200
        data = response.json()
        assert len(data) == 2
        assert all(contact["player_id"] == player_id for contact in data)
        assert all(contact["player_name"] == "Test Player" for contact in data)

    def test_get_ball_contacts_by_player_not_found(
        self, client: TestClient, db_session: Session
    ) -> None:
        """Test getting ball contacts by non-existent player returns 404."""
        response = client.get("/v0/ball-contacts/player/999")

        assert response.status_code == 404
        assert "not found" in response.json()["detail"]

    def test_get_ball_contacts_by_video_with_players(
        self, client: TestClient, db_session: Session, test_user_id: str
    ) -> None:
        """Test getting ball contacts by video includes player information."""
        # Create players
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

        player1_response = client.post("/v0/players/", json=player1_data)
        player2_response = client.post("/v0/players/", json=player2_data)
        player1_id = player1_response.json()["id"]
        player2_id = player2_response.json()["id"]

        # Create video directly in the database for testing
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

        # Create ball contacts with different players
        ball_contacts_data = [
            {
                "video_id": video_id,
                "video_timestamp": 1.0,
                "contact_hand": "right",
                "stroke_type": "ground_stroke",
                "player_id": player1_id,
            },
            {
                "video_id": video_id,
                "video_timestamp": 20.0,
                "contact_hand": "left",
                "stroke_type": "volley",
                "player_id": player2_id,
            },
            {
                "video_id": video_id,
                "video_timestamp": 30.0,
                "contact_hand": "right",
                "stroke_type": "serve",
                # No player_id
            },
        ]

        for ball_contact_data in ball_contacts_data:
            client.post("/v0/ball-contacts/", json=ball_contact_data)

        # Get ball contacts by video
        response = client.get(f"/v0/ball-contacts/video/{video_id}")

        assert response.status_code == 200
        data = response.json()
        assert len(data) == 3

        # Check player information is included
        player_contacts = [c for c in data if c["player_id"] is not None]
        assert len(player_contacts) == 2

        player_names = {c["player_name"] for c in player_contacts}
        assert player_names == {"Player 1", "Player 2"}

        # Check contact without player
        no_player_contacts = [c for c in data if c["player_id"] is None]
        assert len(no_player_contacts) == 1
        assert no_player_contacts[0]["player_name"] is None

    def test_delete_player_cascades_to_ball_contacts(
        self, client: TestClient, db_session: Session, test_user_id: str
    ) -> None:
        """Test that deleting a player sets ball contact player_id to NULL."""
        # Create player
        player_data = {
            "name": "Test Player",
            "dominant_hand": "right",
            "backhand_style": "two_handed",
        }
        player_response = client.post("/v0/players/", json=player_data)
        player_id = player_response.json()["id"]

        # Create video directly in the database for testing
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

        # Create ball contact with player
        ball_contact_data = {
            "video_id": video_id,
            "video_timestamp": 1.0,
            "contact_hand": "right",
            "stroke_type": "ground_stroke",
            "player_id": player_id,
        }
        create_response = client.post("/v0/ball-contacts/", json=ball_contact_data)
        ball_contact_id = create_response.json()["id"]

        # Verify ball contact has player
        get_response = client.get(f"/v0/ball-contacts/{ball_contact_id}")
        assert get_response.json()["player_id"] == player_id

        # Delete player
        delete_response = client.delete(f"/v0/players/{player_id}")
        assert delete_response.status_code == 200

        # Verify ball contact no longer has player
        get_response = client.get(f"/v0/ball-contacts/{ball_contact_id}")
        assert get_response.json()["player_id"] is None
        assert get_response.json()["player"] is None

    def test_create_ball_contact_with_valid_subtype(
        self, client: TestClient, db_session: Session, test_user_id: str
    ) -> None:
        """Test creating a ball contact with valid subtype."""
        # Create video directly in the database for testing
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

        # Create ball contact with valid subtype
        ball_contact_data = {
            "video_id": video_id,
            "video_timestamp": 1.0,
            "contact_hand": "right",
            "stroke_type": "ground_stroke",
            "stroke_subtype": "forehand_topspin",
        }

        response = client.post("/v0/ball-contacts/", json=ball_contact_data)

        assert response.status_code == 201
        data = response.json()
        assert data["stroke_type"] == "ground_stroke"
        assert data["stroke_subtype"] == "forehand_topspin"

    def test_create_ball_contact_with_invalid_subtype(
        self, client: TestClient, db_session: Session, test_user_id: str
    ) -> None:
        """Test creating a ball contact with invalid subtype fails."""
        # Create video directly in the database for testing
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

        # Create ball contact with invalid subtype (smash is for overhead, not ground_stroke)
        ball_contact_data = {
            "video_id": video_id,
            "video_timestamp": 1.0,
            "contact_hand": "right",
            "stroke_type": "ground_stroke",
            "stroke_subtype": "smash",  # Invalid for ground_stroke
        }

        response = client.post("/v0/ball-contacts/", json=ball_contact_data)

        assert response.status_code == 422  # Validation error
        assert "Invalid subtype" in response.json()["detail"][0]["msg"]

    def test_create_ball_contact_with_return_type(
        self, client: TestClient, db_session: Session, test_user_id: str
    ) -> None:
        """Test creating a ball contact with return stroke type."""
        # Create video directly in the database for testing
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

        # Create ball contact with return type
        ball_contact_data = {
            "video_id": video_id,
            "video_timestamp": 1.0,
            "contact_hand": "right",
            "stroke_type": "return",
            "stroke_subtype": "forehand",
        }

        response = client.post("/v0/ball-contacts/", json=ball_contact_data)

        assert response.status_code == 201
        data = response.json()
        assert data["stroke_type"] == "return"
        assert data["stroke_subtype"] == "forehand"

    def test_update_ball_contact_subtype_only(
        self, client: TestClient, db_session: Session, test_user_id: str
    ) -> None:
        """Test updating only stroke_subtype without providing stroke_type."""
        # Create video directly in the database for testing
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

        # Create ball contact with ground_stroke and no subtype
        ball_contact_data = {
            "video_id": video_id,
            "video_timestamp": 1.0,
            "contact_hand": "right",
            "stroke_type": "ground_stroke",
            "stroke_subtype": None,
        }

        create_response = client.post("/v0/ball-contacts/", json=ball_contact_data)
        assert create_response.status_code == 201
        ball_contact_id = create_response.json()["id"]

        # Update only stroke_subtype without providing stroke_type
        # The validator should skip validation and let service layer use existing stroke_type
        update_data = {
            "stroke_subtype": "forehand_topspin",
            # Note: stroke_type is NOT provided
        }

        update_response = client.put(
            f"/v0/ball-contacts/{ball_contact_id}", json=update_data
        )

        assert update_response.status_code == 200
        data = update_response.json()
        assert data["stroke_type"] == "ground_stroke"  # Should remain unchanged
        assert data["stroke_subtype"] == "forehand_topspin"  # Should be updated

    def test_update_ball_contact_subtype_only_invalid(
        self, client: TestClient, db_session: Session, test_user_id: str
    ) -> None:
        """Test that invalid subtype still fails validation when stroke_type is provided."""
        # Create video directly in the database for testing
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

        # Create ball contact with ground_stroke
        ball_contact_data = {
            "video_id": video_id,
            "video_timestamp": 1.0,
            "contact_hand": "right",
            "stroke_type": "ground_stroke",
            "stroke_subtype": "forehand_topspin",
        }

        create_response = client.post("/v0/ball-contacts/", json=ball_contact_data)
        assert create_response.status_code == 201
        ball_contact_id = create_response.json()["id"]

        # Try to update with invalid subtype (smash is for overhead, not ground_stroke)
        # This should fail validation since stroke_type is explicitly provided
        update_data = {
            "stroke_type": "ground_stroke",  # Explicitly provided
            "stroke_subtype": "smash",  # Invalid for ground_stroke
        }

        update_response = client.put(
            f"/v0/ball-contacts/{ball_contact_id}", json=update_data
        )

        assert update_response.status_code == 422  # Validation error
        assert "Invalid subtype" in str(update_response.json())
