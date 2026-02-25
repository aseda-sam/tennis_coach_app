"""Unit tests for ServeWindowCreate and ServeWindowUpdate schemas.

Tests cross-field timestamp validator and Literal type enforcement.
Pure Pydantic tests — no DB or HTTP client needed.
"""

import pytest
from pydantic import ValidationError

from app.api.schemas.serve_window import (
    ServeWindowCreate,
    ServeWindowSplitRequest,
    ServeWindowUpdate,
)

# ---------------------------------------------------------------------------
# ServeWindowCreate — timestamp validator
# ---------------------------------------------------------------------------


class TestServeWindowCreateTimestamps:
    def _valid(self, **overrides) -> dict:
        base = {
            "video_id": 1,
            "start_timestamp": 0.0,
            "end_timestamp": 2.0,
        }
        base.update(overrides)
        return base

    def test_valid_timestamps_accepted(self) -> None:
        sw = ServeWindowCreate(**self._valid())
        assert sw.start_timestamp == 0.0
        assert sw.end_timestamp == 2.0

    def test_end_before_start_raises(self) -> None:
        with pytest.raises(
            ValidationError, match="start_timestamp must be less than end_timestamp"
        ):
            ServeWindowCreate(**self._valid(start_timestamp=2.0, end_timestamp=1.0))

    def test_equal_timestamps_raises(self) -> None:
        with pytest.raises(ValidationError):
            ServeWindowCreate(**self._valid(start_timestamp=1.5, end_timestamp=1.5))

    def test_contact_inside_window_accepted(self) -> None:
        sw = ServeWindowCreate(**self._valid(contact_timestamp=1.0))
        assert sw.contact_timestamp == 1.0

    def test_contact_at_start_boundary_accepted(self) -> None:
        sw = ServeWindowCreate(
            **self._valid(start_timestamp=0.0, end_timestamp=2.0, contact_timestamp=0.0)
        )
        assert sw.contact_timestamp == 0.0

    def test_contact_at_end_boundary_accepted(self) -> None:
        sw = ServeWindowCreate(
            **self._valid(start_timestamp=0.0, end_timestamp=2.0, contact_timestamp=2.0)
        )
        assert sw.contact_timestamp == 2.0

    def test_contact_before_start_raises(self) -> None:
        # start=1.0, contact=0.5 — contact is valid (≥0) but before start
        with pytest.raises(ValidationError, match="contact_timestamp must be between"):
            ServeWindowCreate(
                **self._valid(
                    start_timestamp=1.0, end_timestamp=3.0, contact_timestamp=0.5
                )
            )

    def test_contact_after_end_raises(self) -> None:
        with pytest.raises(ValidationError, match="contact_timestamp must be between"):
            ServeWindowCreate(**self._valid(contact_timestamp=3.0))

    def test_no_contact_timestamp_is_fine(self) -> None:
        sw = ServeWindowCreate(**self._valid())
        assert sw.contact_timestamp is None


# ---------------------------------------------------------------------------
# ServeWindowCreate — Literal type enforcement
# ---------------------------------------------------------------------------


class TestServeWindowCreateLiterals:
    def _base(self) -> dict:
        return {"video_id": 1, "start_timestamp": 0.0, "end_timestamp": 2.0}

    def test_court_side_deuce_accepted(self) -> None:
        sw = ServeWindowCreate(**self._base(), court_side="deuce")
        assert sw.court_side == "deuce"

    def test_court_side_ad_accepted(self) -> None:
        sw = ServeWindowCreate(**self._base(), court_side="ad")
        assert sw.court_side == "ad"

    def test_court_side_invalid_raises(self) -> None:
        with pytest.raises(ValidationError):
            ServeWindowCreate(**self._base(), court_side="left")

    def test_serve_subtype_flat_accepted(self) -> None:
        sw = ServeWindowCreate(**self._base(), serve_subtype="flat")
        assert sw.serve_subtype == "flat"

    def test_serve_subtype_invalid_raises(self) -> None:
        with pytest.raises(ValidationError):
            ServeWindowCreate(**self._base(), serve_subtype="topspin")

    def test_in_out_in_accepted(self) -> None:
        sw = ServeWindowCreate(**self._base(), in_out="in")
        assert sw.in_out == "in"

    def test_in_out_out_long_accepted(self) -> None:
        sw = ServeWindowCreate(**self._base(), in_out="out_long")
        assert sw.in_out == "out_long"

    def test_in_out_invalid_raises(self) -> None:
        with pytest.raises(ValidationError):
            ServeWindowCreate(**self._base(), in_out="out")

    def test_all_none_is_valid(self) -> None:
        sw = ServeWindowCreate(**self._base())
        assert sw.court_side is None
        assert sw.serve_subtype is None
        assert sw.in_out is None


# ---------------------------------------------------------------------------
# ServeWindowUpdate — timestamp validator (partial update)
# ---------------------------------------------------------------------------


class TestServeWindowUpdateTimestamps:
    def test_no_timestamps_is_valid(self) -> None:
        sw = ServeWindowUpdate(court_side="deuce")
        assert sw.start_timestamp is None
        assert sw.end_timestamp is None

    def test_both_timestamps_valid(self) -> None:
        sw = ServeWindowUpdate(start_timestamp=1.0, end_timestamp=3.0)
        assert sw.start_timestamp == 1.0

    def test_both_timestamps_inverted_raises(self) -> None:
        with pytest.raises(
            ValidationError, match="start_timestamp must be less than end_timestamp"
        ):
            ServeWindowUpdate(start_timestamp=3.0, end_timestamp=1.0)

    def test_only_start_no_validation(self) -> None:
        # Partial update: only start provided — no cross-field check possible
        sw = ServeWindowUpdate(start_timestamp=5.0)
        assert sw.start_timestamp == 5.0

    def test_contact_outside_window_raises(self) -> None:
        with pytest.raises(ValidationError, match="contact_timestamp must be between"):
            ServeWindowUpdate(
                start_timestamp=0.0, end_timestamp=2.0, contact_timestamp=5.0
            )

    def test_contact_inside_window_accepted(self) -> None:
        sw = ServeWindowUpdate(
            start_timestamp=0.0, end_timestamp=2.0, contact_timestamp=1.0
        )
        assert sw.contact_timestamp == 1.0

    def test_contact_without_start_end_no_cross_check(self) -> None:
        # Only contact provided — can't cross-check, should not raise
        sw = ServeWindowUpdate(contact_timestamp=1.0)
        assert sw.contact_timestamp == 1.0


# ---------------------------------------------------------------------------
# ServeWindowSplitRequest
# ---------------------------------------------------------------------------


class TestServeWindowSplitRequest:
    def test_valid_split_at_accepted(self) -> None:
        req = ServeWindowSplitRequest(split_at=1.5)
        assert req.split_at == 1.5

    def test_split_at_zero_rejected(self) -> None:
        # gt=0 constraint
        with pytest.raises(ValidationError):
            ServeWindowSplitRequest(split_at=0.0)

    def test_split_at_negative_rejected(self) -> None:
        with pytest.raises(ValidationError):
            ServeWindowSplitRequest(split_at=-1.0)

    def test_split_at_small_positive_accepted(self) -> None:
        req = ServeWindowSplitRequest(split_at=0.001)
        assert req.split_at == 0.001

    def test_missing_split_at_raises(self) -> None:
        with pytest.raises(ValidationError):
            ServeWindowSplitRequest()  # type: ignore[call-arg]
