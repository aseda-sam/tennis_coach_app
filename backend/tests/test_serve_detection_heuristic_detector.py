"""Unit tests for serve detection heuristic detector."""

from app.services.serve_detection.heuristic_detector import (
    MAX_SERVE_DURATION,
    detect_serve_windows,
)


def _base_feature() -> dict[str, float | bool]:
    return {
        "max_wrist_height": 0.8,
        "any_wrist_above_shoulder": False,
        "both_arms_raised": False,
        "max_wrist_velocity": 10.0,
        "knee_hip_ratio": 1.0,
        "has_pose": True,
    }


def test_detect_serve_windows_splits_long_cluster_instead_of_dropping() -> None:
    """Long raised-arm sequences should yield at least one candidate window."""
    fps = 30.0
    total_frames = 532  # ~17.7s clip like the regression case
    features = [_base_feature() for _ in range(total_frames)]

    # Long "arm raised" segment (~11.4s) that would previously be discarded.
    for i in range(100, 442):
        features[i]["any_wrist_above_shoulder"] = True
        features[i]["max_wrist_height"] = 1.25

    # Strong motion burst around contact/swing.
    for i in range(245, 281):
        features[i]["max_wrist_velocity"] = 260.0

    proposals = detect_serve_windows(features, fps)

    assert len(proposals) >= 1
    assert all(
        (p["end_timestamp"] - p["start_timestamp"]) <= MAX_SERVE_DURATION
        for p in proposals
    )
    # At least one proposal should cover the motion burst center.
    burst_center_ts = 263 / fps
    assert any(
        p["start_timestamp"] <= burst_center_ts <= p["end_timestamp"] for p in proposals
    )


def test_detect_serve_windows_keeps_short_cluster_behavior() -> None:
    """Normal short clusters should still produce one valid proposal."""
    fps = 30.0
    total_frames = 180
    features = [_base_feature() for _ in range(total_frames)]

    for i in range(45, 90):
        features[i]["any_wrist_above_shoulder"] = True
        features[i]["max_wrist_height"] = 1.1
        features[i]["max_wrist_velocity"] = 140.0

    proposals = detect_serve_windows(features, fps)

    assert len(proposals) == 1
    duration = proposals[0]["end_timestamp"] - proposals[0]["start_timestamp"]
    assert 0.5 <= duration <= MAX_SERVE_DURATION
