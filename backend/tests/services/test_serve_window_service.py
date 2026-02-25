"""Unit tests for serve_window_service.

Tests split_serve_window, resize/shift logic in update_serve_window,
and is_active filtering in list functions.
Uses real DB session via conftest fixtures.
"""

import pytest

from app.models.player import Player
from app.models.serve_window import ServeWindow
from app.models.video import Video
from app.services import serve_window_service
from app.services.serve_window_service import split_serve_window

USER_ID = "00000000-0000-0000-0000-000000000001"


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def player(db_session):
    """Create a minimal player for test serve windows."""
    p = Player(
        user_id=USER_ID,
        name="Test Player",
        dominant_hand="right",
    )
    db_session.add(p)
    db_session.commit()
    db_session.refresh(p)
    return p


@pytest.fixture
def video(db_session):
    """Create a minimal video for test serve windows."""
    v = Video(
        user_id=USER_ID,
        filename="test.mp4",
        file_path="/data/videos/raw/test.mp4",
        file_size=1000,
        content_type="video/mp4",
        status="ready",
    )
    db_session.add(v)
    db_session.commit()
    db_session.refresh(v)
    return v


def _make_window(
    db_session,
    video,
    player,
    start: float,
    end: float,
    contact: float | None = None,
    contact_source: str | None = None,
    is_active: bool = True,
    status: str = "accepted",
) -> ServeWindow:
    w = ServeWindow(
        video_id=video.id,
        user_id=USER_ID,
        player_id=player.id,
        start_timestamp=start,
        end_timestamp=end,
        contact_timestamp=contact,
        contact_source=contact_source,
        source="manual",
        status=status,
        is_active=is_active,
    )
    db_session.add(w)
    db_session.commit()
    db_session.refresh(w)
    return w


# ---------------------------------------------------------------------------
# split_serve_window — success cases
# ---------------------------------------------------------------------------


class TestSplitServeWindowSuccess:
    def test_original_deactivated(self, db_session, video, player):
        original = _make_window(db_session, video, player, start=0.0, end=5.0)
        split_serve_window(db_session, original.id, 2.5, USER_ID)

        db_session.refresh(original)
        assert original.is_active is False

    def test_original_status_edited(self, db_session, video, player):
        original = _make_window(db_session, video, player, start=0.0, end=5.0)
        split_serve_window(db_session, original.id, 2.5, USER_ID)

        db_session.refresh(original)
        assert original.status == "edited"

    def test_two_children_created(self, db_session, video, player):
        original = _make_window(db_session, video, player, start=0.0, end=5.0)
        child_a, child_b = split_serve_window(db_session, original.id, 2.5, USER_ID)

        assert child_a.id != original.id
        assert child_b.id != original.id
        assert child_a.id != child_b.id

    def test_child_a_timestamps(self, db_session, video, player):
        original = _make_window(db_session, video, player, start=1.0, end=6.0)
        child_a, _ = split_serve_window(db_session, original.id, 3.5, USER_ID)

        assert child_a.start_timestamp == 1.0
        assert child_a.end_timestamp == 3.5

    def test_child_b_timestamps(self, db_session, video, player):
        original = _make_window(db_session, video, player, start=1.0, end=6.0)
        _, child_b = split_serve_window(db_session, original.id, 3.5, USER_ID)

        assert child_b.start_timestamp == 3.5
        assert child_b.end_timestamp == 6.0

    def test_children_have_parent_window_id(self, db_session, video, player):
        original = _make_window(db_session, video, player, start=0.0, end=5.0)
        child_a, child_b = split_serve_window(db_session, original.id, 2.5, USER_ID)

        assert child_a.parent_window_id == original.id
        assert child_b.parent_window_id == original.id

    def test_children_are_active(self, db_session, video, player):
        original = _make_window(db_session, video, player, start=0.0, end=5.0)
        child_a, child_b = split_serve_window(db_session, original.id, 2.5, USER_ID)

        assert child_a.is_active is True
        assert child_b.is_active is True

    def test_children_status_accepted(self, db_session, video, player):
        original = _make_window(db_session, video, player, start=0.0, end=5.0)
        child_a, child_b = split_serve_window(db_session, original.id, 2.5, USER_ID)

        assert child_a.status == "accepted"
        assert child_b.status == "accepted"

    def test_contact_in_first_half_assigned_to_a(self, db_session, video, player):
        original = _make_window(
            db_session,
            video,
            player,
            start=0.0,
            end=5.0,
            contact=1.5,
            contact_source="manual",
        )
        child_a, child_b = split_serve_window(db_session, original.id, 2.5, USER_ID)

        assert child_a.contact_timestamp == 1.5
        assert child_a.contact_source == "manual"
        assert child_b.contact_timestamp is None
        assert child_b.contact_source is None

    def test_contact_at_split_point_assigned_to_a(self, db_session, video, player):
        # contact_timestamp == split_at goes to child_a (<=)
        original = _make_window(
            db_session,
            video,
            player,
            start=0.0,
            end=5.0,
            contact=2.5,
            contact_source="auto",
        )
        child_a, child_b = split_serve_window(db_session, original.id, 2.5, USER_ID)

        assert child_a.contact_timestamp == 2.5
        assert child_b.contact_timestamp is None

    def test_contact_in_second_half_assigned_to_b(self, db_session, video, player):
        original = _make_window(
            db_session,
            video,
            player,
            start=0.0,
            end=5.0,
            contact=3.5,
            contact_source="auto",
        )
        child_a, child_b = split_serve_window(db_session, original.id, 2.5, USER_ID)

        assert child_a.contact_timestamp is None
        assert child_b.contact_timestamp == 3.5
        assert child_b.contact_source == "auto"

    def test_no_contact_both_children_have_none(self, db_session, video, player):
        original = _make_window(db_session, video, player, start=0.0, end=5.0)
        child_a, child_b = split_serve_window(db_session, original.id, 2.5, USER_ID)

        assert child_a.contact_timestamp is None
        assert child_b.contact_timestamp is None

    def test_metadata_inherited(self, db_session, video, player):
        original = _make_window(db_session, video, player, start=0.0, end=5.0)
        original.court_side = "deuce"
        original.serve_number = 1
        original.serve_subtype = "flat"
        original.in_out = "in"
        db_session.commit()

        child_a, child_b = split_serve_window(db_session, original.id, 2.5, USER_ID)

        for child in (child_a, child_b):
            assert child.court_side == "deuce"
            assert child.serve_number == 1
            assert child.serve_subtype == "flat"
            assert child.in_out == "in"
            assert child.source == "manual"


# ---------------------------------------------------------------------------
# split_serve_window — validation errors
# ---------------------------------------------------------------------------


class TestSplitServeWindowValidation:
    def test_split_at_outside_window_raises(self, db_session, video, player):
        original = _make_window(db_session, video, player, start=1.0, end=5.0)

        with pytest.raises(ValueError, match="strictly inside"):
            split_serve_window(db_session, original.id, 0.5, USER_ID)

    def test_split_at_equal_to_start_raises(self, db_session, video, player):
        original = _make_window(db_session, video, player, start=1.0, end=5.0)

        with pytest.raises(ValueError, match="strictly inside"):
            split_serve_window(db_session, original.id, 1.0, USER_ID)

    def test_split_at_equal_to_end_raises(self, db_session, video, player):
        original = _make_window(db_session, video, player, start=1.0, end=5.0)

        with pytest.raises(ValueError, match="strictly inside"):
            split_serve_window(db_session, original.id, 5.0, USER_ID)

    def test_first_half_too_short_raises(self, db_session, video, player):
        original = _make_window(db_session, video, player, start=0.0, end=5.0)

        with pytest.raises(ValueError, match="First half"):
            split_serve_window(db_session, original.id, 0.1, USER_ID)

    def test_second_half_too_short_raises(self, db_session, video, player):
        original = _make_window(db_session, video, player, start=0.0, end=5.0)

        with pytest.raises(ValueError, match="Second half"):
            split_serve_window(db_session, original.id, 4.9, USER_ID)

    def test_wrong_user_raises(self, db_session, video, player):
        original = _make_window(db_session, video, player, start=0.0, end=5.0)

        with pytest.raises(ValueError, match="Access denied"):
            split_serve_window(db_session, original.id, 2.5, "wrong-user-id")

    def test_nonexistent_window_raises(self, db_session):
        with pytest.raises(ValueError, match="not found"):
            split_serve_window(db_session, 99999, 2.5, USER_ID)


# ---------------------------------------------------------------------------
# update_serve_window — resize/shift behavior
# ---------------------------------------------------------------------------


class TestUpdateServeWindowResize:
    def test_sets_status_edited_on_start_change(self, db_session, video, player):
        from app.api.schemas.serve_window import ServeWindowUpdate

        window = _make_window(db_session, video, player, start=0.0, end=5.0)
        updates = ServeWindowUpdate(start_timestamp=1.0)

        result = serve_window_service.update_serve_window(
            db_session, window.id, updates, USER_ID
        )

        assert result.status == "edited"

    def test_preserves_original_start_on_first_edit(self, db_session, video, player):
        from app.api.schemas.serve_window import ServeWindowUpdate

        window = _make_window(db_session, video, player, start=0.0, end=5.0)
        updates = ServeWindowUpdate(start_timestamp=1.0)

        result = serve_window_service.update_serve_window(
            db_session, window.id, updates, USER_ID
        )

        assert result.original_start_timestamp == 0.0

    def test_does_not_overwrite_original_timestamps_on_second_edit(
        self, db_session, video, player
    ):
        from app.api.schemas.serve_window import ServeWindowUpdate

        window = _make_window(db_session, video, player, start=0.0, end=5.0)

        # First edit
        serve_window_service.update_serve_window(
            db_session, window.id, ServeWindowUpdate(start_timestamp=1.0), USER_ID
        )
        # Second edit — original should still be 0.0
        result = serve_window_service.update_serve_window(
            db_session, window.id, ServeWindowUpdate(start_timestamp=2.0), USER_ID
        )

        assert result.original_start_timestamp == 0.0

    def test_overlap_raises(self, db_session, video, player):
        from app.api.schemas.serve_window import ServeWindowUpdate

        _make_window(db_session, video, player, start=0.0, end=3.0)
        window_b = _make_window(db_session, video, player, start=4.0, end=8.0)

        # Try to extend window_b to overlap with window_a
        updates = ServeWindowUpdate(start_timestamp=2.0)
        with pytest.raises(ValueError, match="overlap"):
            serve_window_service.update_serve_window(
                db_session, window_b.id, updates, USER_ID
            )

    def test_too_short_raises(self, db_session, video, player):
        from app.api.schemas.serve_window import ServeWindowUpdate

        window = _make_window(db_session, video, player, start=0.0, end=5.0)
        updates = ServeWindowUpdate(start_timestamp=0.0, end_timestamp=0.1)

        with pytest.raises(ValueError, match=r"0\.5 seconds"):
            serve_window_service.update_serve_window(
                db_session, window.id, updates, USER_ID
            )


# ---------------------------------------------------------------------------
# Listing functions — is_active filtering
# ---------------------------------------------------------------------------


class TestListingFiltersInactive:
    def test_list_user_serve_windows_excludes_inactive(self, db_session, video, player):
        _make_window(db_session, video, player, start=0.0, end=3.0, is_active=True)
        _make_window(
            db_session,
            video,
            player,
            start=4.0,
            end=7.0,
            is_active=False,
            status="edited",
        )

        results = serve_window_service.list_user_serve_windows(db_session, USER_ID)

        assert len(results) == 1
        assert results[0].is_active is True

    def test_get_serve_windows_for_video_excludes_inactive(
        self, db_session, video, player
    ):
        _make_window(db_session, video, player, start=0.0, end=3.0, is_active=True)
        _make_window(
            db_session,
            video,
            player,
            start=4.0,
            end=7.0,
            is_active=False,
            status="edited",
        )

        results = serve_window_service.get_serve_windows_for_video(db_session, video.id)

        assert len(results) == 1
        assert results[0].is_active is True
