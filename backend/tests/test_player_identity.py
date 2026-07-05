"""
Tests for player self-identity (is_self flag).

Contract: the account owner's player is identified by an explicit is_self
flag, not by creation order. Creation order is an accident (a user may tag
a "someone else" player before their own profile exists) and must not
determine who "you" are.
"""

from datetime import datetime, timedelta, timezone

from app.models.player import Player
from app.services import player_service

TEST_USER_ID = "00000000-0000-0000-0000-000000000000"


def _make_player(db, name: str, created_offset_min: int = 0, **kwargs) -> Player:
    player = Player(
        name=name,
        dominant_hand="right",
        user_id=TEST_USER_ID,
        created_at=datetime.now(timezone.utc) + timedelta(minutes=created_offset_min),
        **kwargs,
    )
    db.add(player)
    db.commit()
    db.refresh(player)
    return player


class TestDefaultPlayerIdentity:
    def test_created_default_player_is_flagged_as_self(self, db_session):
        player = player_service.get_or_create_default_player(db_session, TEST_USER_ID)

        assert player.is_self is True

    def test_returns_self_player_even_when_older_player_exists(self, db_session):
        # An opponent/"someone else" player created BEFORE the owner's profile
        _make_player(db_session, "Perricard", created_offset_min=0, is_self=False)
        me = _make_player(db_session, "Aseda", created_offset_min=5, is_self=True)

        result = player_service.get_or_create_default_player(db_session, TEST_USER_ID)

        assert result.id == me.id
        assert result.name == "Aseda"

    def test_self_heals_when_no_player_is_flagged(self, db_session):
        # Legacy data: players exist but none is flagged (pre-migration state).
        # The earliest-created player is adopted as self, matching the old
        # creation-order behaviour, and the flag is persisted.
        first = _make_player(db_session, "Me", created_offset_min=0, is_self=False)
        _make_player(db_session, "Opponent", created_offset_min=5, is_self=False)

        result = player_service.get_or_create_default_player(db_session, TEST_USER_ID)

        assert result.id == first.id
        assert result.is_self is True
        db_session.refresh(first)
        assert first.is_self is True

    def test_self_heal_never_adopts_someone_else_player(self, db_session):
        # The dedicated "Someone Else" player must never become "you",
        # even when it is the earliest-created player.
        _make_player(db_session, "Someone Else", created_offset_min=0, is_self=False)
        me = _make_player(db_session, "Me", created_offset_min=5, is_self=False)

        result = player_service.get_or_create_default_player(db_session, TEST_USER_ID)

        assert result.id == me.id
        assert result.is_self is True

    def test_does_not_adopt_another_users_player(self, db_session):
        other = Player(
            name="Other user's player",
            dominant_hand="right",
            user_id="11111111-1111-1111-1111-111111111111",
            is_self=True,
        )
        db_session.add(other)
        db_session.commit()

        result = player_service.get_or_create_default_player(db_session, TEST_USER_ID)

        assert result.id != other.id
        assert result.user_id == TEST_USER_ID


class TestMeEndpointContract:
    def test_me_endpoint_reports_is_self(self, client):
        response = client.get("/v0/players/me")

        assert response.status_code == 200
        data = response.json()
        assert data["is_self"] is True
