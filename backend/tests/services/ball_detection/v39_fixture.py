"""Frozen ByteTrack output for video 39 — regression fixture.

Video 39 (PXL_20260427_122519582_1.mp4, Royal Victoria, 2026-04-27) had
ball detection report 100% rate but no ball appeared in the stick figure
view. Diagnosis: two real tennis balls were lying on the court the whole
session and the strong fine-tuned model latched onto them; the moving
serve ball was detected as 3-5 frame bursts that lost the selection
battle.

Data derived from the live YOLO+ByteTrack run on 2026-05-08. Static ball
A sat at ~(32, 564) for all four serves; static ball B at ~(200, 1058)
appeared in serves 2-4. Moving toss-arc bursts appeared at the apex
(~y=200, mid-frame x) in serves 2-4 only; serve 1 had no qualifying
moving track.

The fixture builders below produce mock `tracked_frames` that match the
shape `_select_ball_track` consumes: list of (frame_idx, timestamp_ms,
det) tuples, where `det.tracker_id` and `det.xyxy` are numpy arrays.
"""

from __future__ import annotations

from typing import Callable
from unittest.mock import MagicMock

import numpy as np

FPS = 30.0
_BBOX_HALF = 8.0


def _bbox(cx: float, cy: float) -> list[float]:
    return [cx - _BBOX_HALF, cy - _BBOX_HALF, cx + _BBOX_HALF, cy + _BBOX_HALF]


def _det_for_frame(tracks_at_frame: list[tuple[int, float, float]]) -> MagicMock:
    """tracks_at_frame: list of (track_id, cx, cy)."""
    det = MagicMock()
    if not tracks_at_frame:
        det.tracker_id = None
        det.xyxy = np.empty((0, 4), dtype=np.float32)
        return det
    det.tracker_id = np.array([t[0] for t in tracks_at_frame], dtype=np.int32)
    det.xyxy = np.array([_bbox(t[1], t[2]) for t in tracks_at_frame], dtype=np.float32)
    return det


def _static_jitter(cx: float, cy: float) -> Callable[[int], tuple[float, float]]:
    """Sub-pixel jitter: ±0.1 px around the center, deterministic."""

    def pos_at(frame_idx: int) -> tuple[float, float]:
        delta = ((frame_idx % 3) - 1) * 0.1
        return (cx + delta, cy + delta)

    return pos_at


def _build_window(
    start_frame: int,
    end_frame: int,
    track_specs: list[dict],
) -> list[tuple]:
    """Build a list of (frame_idx, timestamp_ms, det) tuples for one window.

    Each track_spec dict has:
        id: int — track id
        frames: Iterable[int] — frames where this track is active
        pos: Callable[[int], tuple[float, float]] — centroid at frame idx
    """
    out: list[tuple] = []
    for f in range(start_frame, end_frame + 1):
        ts = f * 1000.0 / FPS
        active: list[tuple[int, float, float]] = []
        for spec in track_specs:
            if f in spec["frames"]:
                cx, cy = spec["pos"](f)
                active.append((spec["id"], cx, cy))
        out.append((f, ts, _det_for_frame(active)))
    return out


def _frames_set(start: int, end: int) -> set[int]:
    return set(range(start, end + 1))


def _sparse_frames(start: int, end: int, n: int) -> set[int]:
    """Pick `n` frames evenly spaced across [start, end]."""
    if n >= (end - start + 1):
        return _frames_set(start, end)
    step = (end - start) / max(n - 1, 1)
    return {round(start + i * step) for i in range(n)}


def _moving_arc(
    base_frame: int, points: list[tuple[float, float]]
) -> Callable[[int], tuple[float, float]]:
    """Position at frame f = points[f - base_frame]."""

    def pos_at(frame_idx: int) -> tuple[float, float]:
        return points[frame_idx - base_frame]

    return pos_at


# --- Frame ranges per serve window (matches DB serve_windows for video 39) ---

SERVE1_RANGE = (343, 431)  # 89 frames
SERVE2_RANGE = (547, 627)  # 81 frames
SERVE3_RANGE = (915, 999)  # 85 frames
SERVE4_RANGE = (1131, 1215)  # 85 frames

# --- Static ball A (left edge, 32, 564) — present in every serve ---
STATIC_A_X = 32.0
STATIC_A_Y = 564.5

# --- Static ball B (bottom, 200, 1058) — sparse in serve 2, persistent in 3 & 4 ---
STATIC_B_X = 200.5
STATIC_B_Y = 1058.0


def build_serve1() -> list[tuple]:
    """Serve 1: only static ball A + three 1-frame fragments (no moving track)."""
    return _build_window(
        *SERVE1_RANGE,
        track_specs=[
            {
                "id": 1,
                "frames": _frames_set(*SERVE1_RANGE),
                "pos": _static_jitter(STATIC_A_X, STATIC_A_Y),
            },
            # 1-frame fragments — moving ball detections that didn't form tracks
            {"id": 29, "frames": {385}, "pos": lambda f: (269.0, 189.0)},
            {"id": 33, "frames": {390}, "pos": lambda f: (382.0, 106.0)},
            {"id": 50, "frames": {419}, "pos": lambda f: (43.0, 248.0)},
        ],
    )


def build_serve2() -> list[tuple]:
    """Serve 2: static A + sparse static B + 5-frame moving toss arc (track 20)."""
    return _build_window(
        *SERVE2_RANGE,
        track_specs=[
            {
                "id": 1,
                "frames": _frames_set(*SERVE2_RANGE),
                "pos": _static_jitter(STATIC_A_X, STATIC_A_Y),
            },
            {
                "id": 9,
                "frames": _sparse_frames(573, 624, 28),
                "pos": _static_jitter(STATIC_B_X, STATIC_B_Y),
            },
            {
                "id": 20,
                "frames": _frames_set(585, 589),
                "pos": _moving_arc(
                    585,
                    [
                        (240.0, 232.0),
                        (241.0, 234.0),
                        (242.0, 236.0),
                        (243.0, 237.0),
                        (240.0, 235.0),
                    ],
                ),
            },
        ],
    )


def build_serve3() -> list[tuple]:
    """Serve 3: static A + persistent static B + 5-frame moving toss arc (track 34)."""
    return _build_window(
        *SERVE3_RANGE,
        track_specs=[
            {
                "id": 1,
                "frames": _frames_set(*SERVE3_RANGE),
                "pos": _static_jitter(STATIC_A_X, STATIC_A_Y),
            },
            {
                "id": 11,
                "frames": _frames_set(929, 930),
                "pos": _moving_arc(929, [(238.0, 518.0), (240.0, 520.0)]),
            },
            {
                "id": 20,
                "frames": _frames_set(941, 999),
                "pos": _static_jitter(STATIC_B_X, STATIC_B_Y),
            },
            {
                "id": 25,
                "frames": _frames_set(946, 955),
                "pos": _static_jitter(494.0, 249.0),  # noisy non-ball cluster
            },
            {
                "id": 34,
                "frames": _frames_set(955, 959),
                "pos": _moving_arc(
                    955,
                    [
                        (264.0, 195.0),
                        (265.0, 198.0),
                        (266.0, 200.0),
                        (267.0, 202.0),
                        (266.0, 204.0),
                    ],
                ),
            },
        ],
    )


def build_serve4() -> list[tuple]:
    """Serve 4: static A + persistent static B + 3-frame moving toss arc (track 28)."""
    return _build_window(
        *SERVE4_RANGE,
        track_specs=[
            {
                "id": 1,
                "frames": _frames_set(*SERVE4_RANGE),
                "pos": _static_jitter(STATIC_A_X, STATIC_A_Y),
            },
            {
                "id": 2,
                "frames": _frames_set(1131, 1214),
                "pos": _static_jitter(STATIC_B_X, STATIC_B_Y),
            },
            {"id": 5, "frames": {1143}, "pos": lambda f: (237.0, 524.0)},
            {
                "id": 28,
                "frames": _frames_set(1170, 1172),
                "pos": _moving_arc(
                    1170, [(228.0, 217.0), (229.0, 220.0), (228.0, 222.0)]
                ),
            },
        ],
    )


def build_all_windows() -> list[list[tuple]]:
    """All four serve windows for v39, in order."""
    return [build_serve1(), build_serve2(), build_serve3(), build_serve4()]
