"""Shared test fixtures for biomechanics (phase segmentation, metrics) tests.

Provides _make_pose and _make_serve_sequence used by test_phase_segmentation,
test_metrics, and test_serve_biomechanics_service.
"""

from typing import Any


def _make_pose(
    left_wrist_y: float = 0.6,
    right_wrist_y: float = 0.6,
    left_wrist_x: float = 0.3,
    right_wrist_x: float = 0.7,
    knee_y: float = 0.7,
    left_shoulder_x: float = 0.4,
    right_shoulder_x: float = 0.6,
) -> dict[str, list[float]]:
    """Create a pose dict with controllable wrist/knee positions."""
    return {
        "left_shoulder": [left_shoulder_x, 0.3],
        "right_shoulder": [right_shoulder_x, 0.3],
        "left_elbow": [0.35, 0.45],
        "right_elbow": [0.65, 0.45],
        "left_wrist": [left_wrist_x, left_wrist_y],
        "right_wrist": [right_wrist_x, right_wrist_y],
        "left_hip": [0.45, 0.55],
        "right_hip": [0.55, 0.55],
        "left_knee": [0.45, knee_y],
        "right_knee": [0.55, knee_y],
        "left_ankle": [0.45, 0.85],
        "right_ankle": [0.55, 0.85],
    }


def _make_serve_sequence(
    num_frames: int = 60,
    fps: float = 30.0,
) -> list[dict[str, Any] | None]:
    """Create a realistic-ish serve pose sequence (default 2s at 30fps).

    Phases at approximate frames (right-handed serve):
    0-5:   Start — arms at sides
    6-12:  Wind-up — left wrist (toss arm) rises above shoulder
    13-20: Cocking — both wrists above shoulders (trophy)
    21-28: Loading — knees bend deeply
    29-38: Acceleration — right wrist velocity spikes
    39-42: Contact — right wrist at highest point
    43-48: Deceleration — right wrist velocity drops
    49-59: Follow-through — right wrist drops below shoulder
    """
    frames: list[dict[str, Any] | None] = []
    for i in range(num_frames):
        if i <= 5:
            frames.append(_make_pose(left_wrist_y=0.6, right_wrist_y=0.6))
        elif i <= 12:
            progress = (i - 6) / 6
            left_y = 0.6 - progress * 0.4
            frames.append(_make_pose(left_wrist_y=left_y, right_wrist_y=0.5))
        elif i <= 20:
            frames.append(_make_pose(left_wrist_y=0.15, right_wrist_y=0.1))
        elif i <= 28:
            progress = (i - 21) / 7
            knee_y = 0.7 + progress * 0.15
            frames.append(
                _make_pose(left_wrist_y=0.2, right_wrist_y=0.2, knee_y=knee_y)
            )
        elif i <= 38:
            progress = (i - 29) / 9
            right_y = 0.4 - progress * 0.35
            right_x = 0.7 + progress * 0.05
            frames.append(
                _make_pose(
                    left_wrist_y=0.3,
                    right_wrist_y=right_y,
                    right_wrist_x=right_x,
                )
            )
        elif i <= 42:
            frames.append(
                _make_pose(left_wrist_y=0.4, right_wrist_y=0.05, right_wrist_x=0.75)
            )
        elif i <= 48:
            progress = (i - 43) / 5
            right_y = 0.05 + progress * 0.3
            frames.append(_make_pose(left_wrist_y=0.5, right_wrist_y=right_y))
        else:
            frames.append(_make_pose(left_wrist_y=0.6, right_wrist_y=0.55))
    return frames
