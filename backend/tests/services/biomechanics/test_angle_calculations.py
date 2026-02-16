"""Tests for biomechanics angle calculation functions.

TDD: These tests define the contract for each calculation function.
All functions take pose_landmarks dicts with keypoints as [x, y] or [x, y, confidence].
"""

from app.services.biomechanics.angle_calculations import (
    calculate_contact_point_height,
    calculate_hip_shoulder_separation,
    calculate_racket_drop_depth,
    calculate_shoulder_abduction,
    calculate_trunk_rotation,
)

# --- Fixtures: sample pose data ---


def _make_pose(overrides: dict | None = None) -> dict:
    """Create a default standing pose with optional overrides.

    Default pose: person standing upright, arms at sides.
    Screen coordinates: Y increases downward.
    """
    base = {
        "left_shoulder": [0.4, 0.3],
        "right_shoulder": [0.6, 0.3],
        "left_elbow": [0.35, 0.45],
        "right_elbow": [0.65, 0.45],
        "left_wrist": [0.3, 0.6],
        "right_wrist": [0.7, 0.6],
        "left_hip": [0.45, 0.55],
        "right_hip": [0.55, 0.55],
        "left_knee": [0.45, 0.7],
        "right_knee": [0.55, 0.7],
        "left_ankle": [0.45, 0.85],
        "right_ankle": [0.55, 0.85],
    }
    if overrides:
        base.update(overrides)
    return base


# --- Tests: calculate_trunk_rotation ---


class TestCalculateTrunkRotation:
    def test_aligned_shoulders_and_hips_returns_zero(self):
        """When shoulder line and hip line are parallel, rotation should be ~0."""
        pose = _make_pose()
        result = calculate_trunk_rotation(pose)
        assert result is not None
        assert abs(result) < 5.0  # Allow small floating point tolerance

    def test_rotated_shoulders_returns_positive_angle(self):
        """Shoulders rotated relative to hips should return non-zero angle."""
        pose = _make_pose(
            {
                # Rotate shoulders: left forward (smaller x), right back (larger x)
                "left_shoulder": [0.35, 0.28],
                "right_shoulder": [0.65, 0.32],
            }
        )
        result = calculate_trunk_rotation(pose)
        assert result is not None
        assert result > 0.0

    def test_missing_keypoints_returns_none(self):
        pose = {"left_shoulder": [0.4, 0.3]}  # Missing most keypoints
        result = calculate_trunk_rotation(pose)
        assert result is None

    def test_returns_float(self):
        pose = _make_pose()
        result = calculate_trunk_rotation(pose)
        assert isinstance(result, float)

    def test_with_confidence_values(self):
        """Should work with [x, y, confidence] format."""
        pose = _make_pose(
            {
                "left_shoulder": [0.4, 0.3, 0.95],
                "right_shoulder": [0.6, 0.3, 0.92],
                "left_hip": [0.45, 0.55, 0.88],
                "right_hip": [0.55, 0.55, 0.90],
            }
        )
        result = calculate_trunk_rotation(pose)
        assert result is not None


# --- Tests: calculate_shoulder_abduction ---


class TestCalculateShoulderAbduction:
    def test_arm_at_side_returns_small_angle(self):
        """Arm hanging at side should have small abduction angle."""
        pose = _make_pose()
        result = calculate_shoulder_abduction(pose, "right")
        assert result is not None
        # Arm at side: hip-shoulder-elbow angle should be relatively small
        assert result < 90.0

    def test_arm_raised_overhead_returns_large_angle(self):
        """Arm raised overhead (trophy position) should have large abduction."""
        pose = _make_pose(
            {
                # Right arm raised overhead
                "right_elbow": [0.65, 0.15],
                "right_wrist": [0.65, 0.05],
            }
        )
        result = calculate_shoulder_abduction(pose, "right")
        assert result is not None
        assert result > 90.0

    def test_left_side(self):
        """Should work for left side too."""
        pose = _make_pose(
            {
                "left_elbow": [0.35, 0.15],
                "left_wrist": [0.35, 0.05],
            }
        )
        result = calculate_shoulder_abduction(pose, "left")
        assert result is not None
        assert result > 90.0

    def test_invalid_side_returns_none(self):
        pose = _make_pose()
        result = calculate_shoulder_abduction(pose, "center")
        assert result is None

    def test_missing_keypoints_returns_none(self):
        pose = {"right_shoulder": [0.6, 0.3]}
        result = calculate_shoulder_abduction(pose, "right")
        assert result is None


# --- Tests: calculate_hip_shoulder_separation ---


class TestCalculateHipShoulderSeparation:
    def test_aligned_returns_near_zero(self):
        """When shoulder and hip lines have same orientation, separation ~0."""
        pose = _make_pose()
        result = calculate_hip_shoulder_separation(pose)
        assert result is not None
        assert abs(result) < 5.0

    def test_rotated_returns_nonzero(self):
        """When shoulders are rotated relative to hips, separation > 0."""
        pose = _make_pose(
            {
                # Shoulders rotated ~30 degrees
                "left_shoulder": [0.35, 0.25],
                "right_shoulder": [0.65, 0.35],
            }
        )
        result = calculate_hip_shoulder_separation(pose)
        assert result is not None
        assert result > 5.0

    def test_returns_absolute_value(self):
        """Separation should always be non-negative (absolute angle difference)."""
        pose = _make_pose(
            {
                "left_shoulder": [0.35, 0.35],
                "right_shoulder": [0.65, 0.25],
            }
        )
        result = calculate_hip_shoulder_separation(pose)
        assert result is not None
        assert result >= 0.0

    def test_missing_keypoints_returns_none(self):
        pose = {"left_shoulder": [0.4, 0.3]}
        result = calculate_hip_shoulder_separation(pose)
        assert result is None


# --- Tests: calculate_contact_point_height ---


class TestCalculateContactPointHeight:
    def test_wrist_above_shoulder_returns_positive(self):
        """Wrist above shoulder (contact point) should return positive height."""
        pose = _make_pose(
            {
                "right_wrist": [0.65, 0.1],  # Well above shoulder at 0.3
            }
        )
        result = calculate_contact_point_height(pose, "right")
        assert result is not None
        assert result > 0.0

    def test_wrist_below_shoulder_returns_negative(self):
        """Wrist below shoulder should return negative height."""
        pose = _make_pose()  # Default: wrist at 0.6, shoulder at 0.3
        result = calculate_contact_point_height(pose, "right")
        assert result is not None
        assert result < 0.0

    def test_normalized_by_torso(self):
        """Result should be normalized by torso length (shoulder-hip distance)."""
        pose = _make_pose(
            {
                "right_wrist": [0.65, 0.1],
            }
        )
        result = calculate_contact_point_height(pose, "right")
        assert result is not None
        # Torso length is ~0.25 (shoulder at 0.3, hip at 0.55)
        # Wrist above shoulder by 0.2, so normalized ~ 0.8
        assert 0.5 < result < 1.5

    def test_left_side(self):
        pose = _make_pose({"left_wrist": [0.35, 0.1]})
        result = calculate_contact_point_height(pose, "left")
        assert result is not None
        assert result > 0.0

    def test_missing_keypoints_returns_none(self):
        pose = {"right_wrist": [0.7, 0.6]}
        result = calculate_contact_point_height(pose, "right")
        assert result is None

    def test_invalid_side_returns_none(self):
        pose = _make_pose()
        result = calculate_contact_point_height(pose, "center")
        assert result is None


# --- Tests: calculate_racket_drop_depth ---


class TestCalculateRacketDropDepth:
    def test_wrist_below_shoulder_returns_positive(self):
        """Wrist dropping below shoulder (racket drop) should return positive depth."""
        pose = _make_pose(
            {
                # Wrist behind and below shoulder (racket drop position)
                "right_wrist": [0.7, 0.5],
            }
        )
        result = calculate_racket_drop_depth(pose, "right")
        assert result is not None
        assert result > 0.0

    def test_wrist_above_shoulder_returns_negative(self):
        """Wrist above shoulder should return negative (no drop)."""
        pose = _make_pose(
            {
                "right_wrist": [0.65, 0.1],
            }
        )
        result = calculate_racket_drop_depth(pose, "right")
        assert result is not None
        assert result < 0.0

    def test_normalized_by_torso(self):
        """Result should be normalized by torso length."""
        pose = _make_pose(
            {
                "right_wrist": [0.7, 0.5],  # 0.2 below shoulder at 0.3
            }
        )
        result = calculate_racket_drop_depth(pose, "right")
        assert result is not None
        # Torso length ~0.25, drop ~0.2, normalized ~0.8
        assert 0.5 < result < 1.5

    def test_missing_keypoints_returns_none(self):
        pose = {"right_wrist": [0.7, 0.5]}
        result = calculate_racket_drop_depth(pose, "right")
        assert result is None

    def test_invalid_side_returns_none(self):
        pose = _make_pose()
        result = calculate_racket_drop_depth(pose, "center")
        assert result is None


# --- Tests: Edge cases ---


class TestEdgeCases:
    def test_all_functions_handle_zero_torso_length(self):
        """When shoulder and hip overlap, shouldn't crash."""
        pose = _make_pose(
            {
                "left_shoulder": [0.5, 0.5],
                "right_shoulder": [0.5, 0.5],
                "left_hip": [0.5, 0.5],
                "right_hip": [0.5, 0.5],
            }
        )
        # These use torso for normalization — should not crash
        height = calculate_contact_point_height(pose, "right")
        depth = calculate_racket_drop_depth(pose, "right")
        # May return None or a value, but should not raise
        assert height is None or isinstance(height, float)
        assert depth is None or isinstance(depth, float)

    def test_all_functions_handle_coincident_points(self):
        """When points overlap exactly, angle calc shouldn't crash."""
        pose = _make_pose(
            {
                "right_shoulder": [0.5, 0.3],
                "right_elbow": [0.5, 0.3],  # Same as shoulder
                "right_wrist": [0.5, 0.3],
            }
        )
        result = calculate_shoulder_abduction(pose, "right")
        # Should handle gracefully (return None or 0)
        assert result is None or isinstance(result, float)
