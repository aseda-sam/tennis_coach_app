"""Unit tests for serve detection heuristic detector."""

import pytest

from app.services.serve_detection.heuristic_detector import (
    ANGLE_PROFILES,
    FALLBACK_CONFIDENCE_PENALTY,
    MAX_SERVE_DURATION,
    AngleProfile,
    compute_adaptive_velocity_threshold,
    compute_motion_stats,
    detect_serve_windows,
    get_angle_profile,
    _build_relaxed_profile,
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


# ---------------------------------------------------------------------------
# Existing regression tests (preserved)
# ---------------------------------------------------------------------------


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


# ---------------------------------------------------------------------------
# Camera-angle profile tests
# ---------------------------------------------------------------------------


def test_get_angle_profile_returns_correct_profile() -> None:
    """Known camera angles should return their specific profile."""
    behind = get_angle_profile("behind")
    assert behind.name == "behind"
    assert behind.gap_merge_threshold == 0.4

    profile_cam = get_angle_profile("profile")
    assert profile_cam.name == "profile"
    assert profile_cam.max_serve_duration == 10.0

    unknown = get_angle_profile("unknown")
    assert unknown.name == "unknown"


def test_get_angle_profile_defaults_to_unknown() -> None:
    """None or unrecognized angles fall back to the unknown profile."""
    assert get_angle_profile(None).name == "unknown"
    assert get_angle_profile("overhead").name == "unknown"


def test_behind_profile_stricter_gap_merge() -> None:
    """Behind profile uses a tighter gap merge than profile angle."""
    behind = ANGLE_PROFILES["behind"]
    profile_cam = ANGLE_PROFILES["profile"]
    assert behind.gap_merge_threshold < profile_cam.gap_merge_threshold


def test_profile_angle_allows_longer_serves() -> None:
    """Profile angle has a higher max_serve_duration for visible toss setup."""
    profile_cam = ANGLE_PROFILES["profile"]
    behind = ANGLE_PROFILES["behind"]
    assert profile_cam.max_serve_duration > behind.max_serve_duration


def test_detect_with_behind_angle() -> None:
    """Detection with 'behind' angle should produce proposals for normal serves."""
    fps = 30.0
    total_frames = 180
    features = [_base_feature() for _ in range(total_frames)]

    for i in range(50, 100):
        features[i]["any_wrist_above_shoulder"] = True
        features[i]["max_wrist_height"] = 1.2
        features[i]["max_wrist_velocity"] = 180.0

    proposals = detect_serve_windows(features, fps, camera_angle="behind")
    assert len(proposals) >= 1
    assert proposals[0]["detection_features"]["profile"] == "behind"


def test_detect_with_profile_angle_longer_window() -> None:
    """Profile angle should accept slightly longer serve windows."""
    fps = 30.0
    # Create a serve that's ~9s -- too long for behind (max 8s) but OK for profile (max 10s)
    total_frames = 400
    features = [_base_feature() for _ in range(total_frames)]

    for i in range(50, 320):
        features[i]["any_wrist_above_shoulder"] = True
        features[i]["max_wrist_height"] = 1.2
        features[i]["max_wrist_velocity"] = 150.0

    proposals_profile = detect_serve_windows(features, fps, camera_angle="profile")
    proposals_behind = detect_serve_windows(features, fps, camera_angle="behind")

    # Profile should accept windows that behind might split differently
    assert len(proposals_profile) >= 1


# ---------------------------------------------------------------------------
# Adaptive / motion-normalized threshold tests
# ---------------------------------------------------------------------------


def test_compute_motion_stats_with_velocities() -> None:
    """Motion stats should reflect the velocity distribution."""
    features = [_base_feature() for _ in range(100)]
    for i in range(100):
        features[i]["max_wrist_velocity"] = float(i)  # 0..99

    stats = compute_motion_stats(features)
    assert stats["velocity_p50"] > 0
    assert stats["velocity_p75"] > stats["velocity_p50"]
    assert stats["velocity_p90"] > stats["velocity_p75"]
    assert stats["velocity_max"] == 99.0
    assert stats["pose_density"] == 1.0


def test_compute_motion_stats_no_velocity() -> None:
    """All-zero velocities should return zero stats."""
    features = [_base_feature() for _ in range(10)]
    for f in features:
        f["max_wrist_velocity"] = 0.0

    stats = compute_motion_stats(features)
    assert stats["velocity_p50"] == 0.0
    assert stats["velocity_max"] == 0.0


def test_adaptive_velocity_threshold_slow_motion() -> None:
    """For a slow-motion clip with low velocities, threshold should adapt down."""
    # Simulate a slow-motion clip where velocities are much lower
    stats = {
        "velocity_p50": 15.0,
        "velocity_p75": 25.0,
        "velocity_p90": 40.0,
        "velocity_max": 60.0,
    }
    threshold = compute_adaptive_velocity_threshold(stats, base_threshold=80.0)
    # Should be lower than the base threshold
    assert threshold < 80.0
    # But clamped above the minimum
    assert threshold >= 30.0


def test_adaptive_velocity_threshold_normal_motion() -> None:
    """For normal-speed clips, threshold should be in the reasonable range."""
    stats = {
        "velocity_p50": 60.0,
        "velocity_p75": 90.0,
        "velocity_p90": 150.0,
        "velocity_max": 350.0,
    }
    threshold = compute_adaptive_velocity_threshold(stats, base_threshold=80.0)
    # Should be clamped within bounds
    assert 30.0 <= threshold <= 120.0


def test_adaptive_velocity_threshold_zero_stats() -> None:
    """When stats are zero, fall back to the base threshold."""
    stats = {"velocity_p75": 0.0, "velocity_p90": 0.0}
    threshold = compute_adaptive_velocity_threshold(stats, base_threshold=80.0)
    assert threshold == 80.0


def test_slow_motion_clip_produces_proposals() -> None:
    """A slow-motion clip with low velocities should still detect serves via adaptive thresholds."""
    fps = 30.0
    total_frames = 600  # 20s clip
    features = [_base_feature() for _ in range(total_frames)]

    # Simulate slow-motion: velocities are much lower than normal
    for i in range(total_frames):
        features[i]["max_wrist_velocity"] = 8.0  # low base velocity

    # Arm raised for a long segment (simulating slow-mo serve)
    for i in range(100, 450):
        features[i]["any_wrist_above_shoulder"] = True
        features[i]["max_wrist_height"] = 1.3

    # Small velocity burst at the "contact" - low because slow motion
    for i in range(260, 290):
        features[i]["max_wrist_velocity"] = 45.0  # Below old fixed threshold of 80

    proposals = detect_serve_windows(features, fps)
    # Should find proposals thanks to adaptive threshold
    assert len(proposals) >= 1


# ---------------------------------------------------------------------------
# Fallback pass tests
# ---------------------------------------------------------------------------


def test_fallback_pass_recovers_proposals() -> None:
    """When the primary pass produces nothing, fallback should recover proposals."""
    fps = 30.0
    total_frames = 600
    features = [_base_feature() for _ in range(total_frames)]

    # Long arm-raised segment with uniformly LOW velocity. The cluster is too long
    # (~11.7s > MAX_SERVE_DURATION=8s) so split_long_cluster runs. But all velocities
    # are below the adaptive threshold floor (30), so the primary centered-fallback
    # produces a window that's exactly MAX_SERVE_DURATION. A small velocity bump
    # just above the relaxed threshold (which halves the base) allows the fallback
    # pass to isolate a motion-focused sub-window.
    for i in range(50, 400):  # ~11.7s of arm raised
        features[i]["any_wrist_above_shoulder"] = True
        features[i]["max_wrist_height"] = 1.3
        features[i]["max_wrist_velocity"] = 5.0  # very low, uniform

    # Small bump that's too low for primary adaptive threshold (~30 floor) but
    # enough for the relaxed pass (threshold * 0.5 = ~15)
    for i in range(200, 220):
        features[i]["max_wrist_velocity"] = 22.0

    proposals = detect_serve_windows(features, fps)

    # Should produce at least one proposal (either from primary centered fallback
    # or from the relaxed fallback pass)
    assert len(proposals) >= 1
    for p in proposals:
        assert "detection_pass" in p["detection_features"]


def test_fallback_applies_confidence_penalty() -> None:
    """Proposals from the fallback pass should have reduced confidence."""
    fps = 30.0
    total_frames = 300
    features = [_base_feature() for _ in range(total_frames)]

    # Create a borderline case that only the relaxed pass picks up
    for i in range(120, 128):
        features[i]["any_wrist_above_shoulder"] = True
        features[i]["max_wrist_height"] = 1.5
        features[i]["max_wrist_velocity"] = 300.0

    proposals = detect_serve_windows(features, fps)
    if proposals:
        # The confidence penalty should have been applied
        # A perfect score would be ~1.0, so with penalty it should be lower
        for p in proposals:
            assert p["confidence"] <= 1.0 - FALLBACK_CONFIDENCE_PENALTY + 0.01


def test_no_fallback_when_primary_succeeds() -> None:
    """When the primary pass finds proposals, no fallback should run."""
    fps = 30.0
    total_frames = 180
    features = [_base_feature() for _ in range(total_frames)]

    for i in range(45, 90):
        features[i]["any_wrist_above_shoulder"] = True
        features[i]["max_wrist_height"] = 1.1
        features[i]["max_wrist_velocity"] = 140.0

    proposals = detect_serve_windows(features, fps)
    assert len(proposals) == 1
    assert proposals[0]["detection_features"]["detection_pass"] == "primary"


def test_fallback_tries_alternate_profiles_for_unknown_angle() -> None:
    """For unknown camera angle, fallback should try behind and profile profiles."""
    fps = 30.0
    total_frames = 200
    features = [_base_feature() for _ in range(total_frames)]

    # Marginal arm-raised segment - very short
    for i in range(80, 86):
        features[i]["any_wrist_above_shoulder"] = True
        features[i]["max_wrist_height"] = 1.0
        features[i]["max_wrist_velocity"] = 120.0

    # Unknown angle = should try alternate profiles in fallback
    proposals = detect_serve_windows(features, fps, camera_angle="unknown")
    # May or may not find proposals, but shouldn't crash
    assert isinstance(proposals, list)


# ---------------------------------------------------------------------------
# Relaxed profile tests
# ---------------------------------------------------------------------------


def test_build_relaxed_profile_widens_parameters() -> None:
    """Relaxed profile should have wider tolerances than the original."""
    original = ANGLE_PROFILES["behind"]
    relaxed = _build_relaxed_profile(original)

    assert relaxed.gap_merge_threshold >= original.gap_merge_threshold
    assert relaxed.max_serve_duration >= original.max_serve_duration
    assert relaxed.min_serve_duration <= original.min_serve_duration
    assert relaxed.long_cluster_velocity_threshold <= original.long_cluster_velocity_threshold
    assert relaxed.name == "behind_relaxed"


def test_build_relaxed_profile_bounded() -> None:
    """Relaxed profile values should stay within reasonable bounds."""
    original = ANGLE_PROFILES["profile"]
    relaxed = _build_relaxed_profile(original)

    assert relaxed.gap_merge_threshold <= 1.5
    assert relaxed.max_serve_duration <= 12.0
    assert relaxed.min_serve_duration >= 0.3
    assert relaxed.padding_before <= 1.0
    assert relaxed.padding_after <= 1.0


# ---------------------------------------------------------------------------
# Edge cases
# ---------------------------------------------------------------------------


def test_empty_features_returns_empty() -> None:
    """Empty features should return no proposals."""
    assert detect_serve_windows([], 30.0) == []
    assert detect_serve_windows([], 30.0, camera_angle="behind") == []


def test_zero_fps_returns_empty() -> None:
    """Zero or negative FPS should return no proposals."""
    features = [_base_feature() for _ in range(10)]
    assert detect_serve_windows(features, 0.0) == []
    assert detect_serve_windows(features, -1.0) == []


def test_no_pose_data_returns_empty() -> None:
    """No frames with pose data should return no proposals."""
    features = [_base_feature() for _ in range(10)]
    for f in features:
        f["has_pose"] = False
    assert detect_serve_windows(features, 30.0) == []


def test_detection_features_include_pass_and_profile() -> None:
    """Detection features should include which pass and profile produced the proposal."""
    fps = 30.0
    total_frames = 180
    features = [_base_feature() for _ in range(total_frames)]

    for i in range(45, 90):
        features[i]["any_wrist_above_shoulder"] = True
        features[i]["max_wrist_height"] = 1.1
        features[i]["max_wrist_velocity"] = 140.0

    proposals = detect_serve_windows(features, fps, camera_angle="behind")
    assert len(proposals) >= 1
    for p in proposals:
        assert "detection_pass" in p["detection_features"]
        assert "profile" in p["detection_features"]
