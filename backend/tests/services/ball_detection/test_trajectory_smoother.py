"""Tests for TrajectorySmoother post-processing (spline interpolation)."""

from __future__ import annotations

import pytest

from app.services.ball_detection.trajectory_smoother import (
    MAX_GAP_FRAMES,
    MIN_ANCHORS,
    TrajectorySmoother,
    _cubic_spline_interpolate,
    smooth_trajectory,
)


def _make_det(
    frame_index: int,
    *,
    ball_x: float | None = None,
    ball_y: float | None = None,
    confidence: float | None = None,
    interpolated: bool = False,
) -> dict:
    return {
        "frame_index": frame_index,
        "timestamp_ms": frame_index * 33.3,
        "ball_x": ball_x,
        "ball_y": ball_y,
        "confidence": confidence,
        "interpolated": interpolated,
    }


def _moving_sequence(
    start: int, n: int, dx: float = 20.0, dy: float = 15.0
) -> list[dict]:
    """A sequence of n frames with a clearly moving ball."""
    return [
        _make_det(
            start + i, ball_x=100.0 + i * dx, ball_y=200.0 - i * dy, confidence=0.8
        )
        for i in range(n)
    ]


# ---------------------------------------------------------------------------
# Cubic spline interpolation
# ---------------------------------------------------------------------------


class TestCubicSplineInterpolation:
    def test_short_gap_is_filled(self) -> None:
        """A gap ≤ MAX_GAP_FRAMES with enough anchors should be interpolated."""
        pytest.importorskip("scipy")
        # 6 anchors before gap, gap of 4, 6 anchors after
        before = _moving_sequence(0, MIN_ANCHORS + 2, dx=10.0, dy=5.0)
        gap = [
            _make_det(i, ball_x=None, ball_y=None)
            for i in range(MIN_ANCHORS + 2, MIN_ANCHORS + 6)
        ]
        after = _moving_sequence(MIN_ANCHORS + 6, MIN_ANCHORS + 2, dx=10.0, dy=5.0)
        dets = before + gap + after

        result = _cubic_spline_interpolate(
            dets, max_gap_frames=MAX_GAP_FRAMES, min_anchors=MIN_ANCHORS
        )

        gap_results = result[MIN_ANCHORS + 2 : MIN_ANCHORS + 6]
        for r in gap_results:
            assert r["ball_x"] is not None, "Gap should be interpolated"
            assert r["interpolated"] is True

    def test_long_gap_left_as_none(self) -> None:
        """A gap > MAX_GAP_FRAMES should NOT be interpolated."""
        pytest.importorskip("scipy")
        before = _moving_sequence(0, MIN_ANCHORS + 2, dx=10.0, dy=5.0)
        gap_len = MAX_GAP_FRAMES + 2
        gap = [
            _make_det(i, ball_x=None, ball_y=None)
            for i in range(MIN_ANCHORS + 2, MIN_ANCHORS + 2 + gap_len)
        ]
        after = _moving_sequence(
            MIN_ANCHORS + 2 + gap_len, MIN_ANCHORS + 2, dx=10.0, dy=5.0
        )
        dets = before + gap + after

        result = _cubic_spline_interpolate(
            dets, max_gap_frames=MAX_GAP_FRAMES, min_anchors=MIN_ANCHORS
        )

        gap_start = MIN_ANCHORS + 2
        gap_results = result[gap_start : gap_start + gap_len]
        for r in gap_results:
            assert r["ball_x"] is None, "Long gap should not be interpolated"
            assert r["interpolated"] is False

    def test_gap_with_insufficient_anchors_not_filled(self) -> None:
        """If there are fewer than MIN_ANCHORS on either side, do not interpolate."""
        pytest.importorskip("scipy")
        # Only 2 anchors before (< MIN_ANCHORS)
        before = _moving_sequence(0, 2, dx=10.0, dy=5.0)
        gap = [_make_det(i, ball_x=None, ball_y=None) for i in range(2, 6)]
        after = _moving_sequence(6, MIN_ANCHORS + 2, dx=10.0, dy=5.0)
        dets = before + gap + after

        result = _cubic_spline_interpolate(
            dets, max_gap_frames=MAX_GAP_FRAMES, min_anchors=MIN_ANCHORS
        )

        gap_results = result[2:6]
        for r in gap_results:
            assert r["ball_x"] is None

    def test_interpolated_values_are_plausible(self) -> None:
        """Interpolated positions should lie roughly on the expected arc."""
        pytest.importorskip("scipy")
        # Straight-line trajectory: x = 100 + 10*i, y = 200 - 5*i
        n = MIN_ANCHORS + 2
        before = [
            _make_det(i, ball_x=100.0 + i * 10, ball_y=200.0 - i * 5, confidence=0.9)
            for i in range(n)
        ]
        gap_start_i = n
        gap_end_i = gap_start_i + 4
        gap = [
            _make_det(i, ball_x=None, ball_y=None)
            for i in range(gap_start_i, gap_end_i)
        ]
        after = [
            _make_det(i, ball_x=100.0 + i * 10, ball_y=200.0 - i * 5, confidence=0.9)
            for i in range(gap_end_i, gap_end_i + n)
        ]
        dets = before + gap + after

        result = _cubic_spline_interpolate(
            dets, max_gap_frames=MAX_GAP_FRAMES, min_anchors=MIN_ANCHORS
        )

        for k, gap_i in enumerate(range(gap_start_i, gap_end_i)):
            r = result[gap_i]
            expected_x = 100.0 + gap_i * 10
            expected_y = 200.0 - gap_i * 5
            assert abs(r["ball_x"] - expected_x) < 5.0, f"x off at gap frame {k}"
            assert abs(r["ball_y"] - expected_y) < 5.0, f"y off at gap frame {k}"

    def test_interpolated_flag_set_correctly(self) -> None:
        """Non-gap frames should have interpolated=False; gap frames interpolated=True."""
        pytest.importorskip("scipy")
        before = _moving_sequence(0, MIN_ANCHORS + 2, dx=10.0, dy=5.0)
        gap = [
            _make_det(i, ball_x=None, ball_y=None)
            for i in range(MIN_ANCHORS + 2, MIN_ANCHORS + 4)
        ]
        after = _moving_sequence(MIN_ANCHORS + 4, MIN_ANCHORS + 2, dx=10.0, dy=5.0)
        dets = before + gap + after

        result = _cubic_spline_interpolate(
            dets, max_gap_frames=MAX_GAP_FRAMES, min_anchors=MIN_ANCHORS
        )

        for r in result[: MIN_ANCHORS + 2]:
            assert r["interpolated"] is False
        for r in result[MIN_ANCHORS + 2 : MIN_ANCHORS + 4]:
            assert r["interpolated"] is True
        for r in result[MIN_ANCHORS + 4 :]:
            assert r["interpolated"] is False


# ---------------------------------------------------------------------------
# TrajectorySmoother end-to-end
# ---------------------------------------------------------------------------


class TestTrajectorySmoother:
    def test_smoother_runs_interpolation(self) -> None:
        """smoke test: smoother produces a list with interpolated keys."""
        pytest.importorskip("scipy")
        smoother = TrajectorySmoother()
        dets = _moving_sequence(0, 10, dx=20.0)
        result = smoother.smooth(dets)
        assert len(result) == 10
        for r in result:
            assert "interpolated" in r

    def test_module_level_convenience_wrapper(self) -> None:
        """smooth_trajectory() is equivalent to TrajectorySmoother().smooth()."""
        pytest.importorskip("scipy")
        dets = _moving_sequence(0, 6, dx=20.0)
        r1 = smooth_trajectory(dets)
        r2 = TrajectorySmoother().smooth(dets)
        assert [d["ball_x"] for d in r1] == [d["ball_x"] for d in r2]
