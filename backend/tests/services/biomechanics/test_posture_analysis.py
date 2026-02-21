"""
Tests for posture analysis utilities.

Serve MVP scope: elbow angle calculation only.
"""

from app.services.biomechanics.posture_analysis import calculate_elbow_angle


class TestPostureAnalysisService:
    """Test posture analysis service functionality."""

    def test_calculate_elbow_angle_valid_data(self) -> None:
        """Test elbow angle calculation with valid pose landmarks."""
        pose_landmarks = {
            "right_shoulder": [0.4, 0.3, 0.9],
            "right_elbow": [0.5, 0.4, 0.9],
            "right_wrist": [0.6, 0.5, 0.9],
        }

        angle = calculate_elbow_angle(pose_landmarks, "right", "serve")

        assert angle is not None
        assert 0.0 <= angle <= 180.0
        assert isinstance(angle, float)

    def test_calculate_elbow_angle_left_hand(self) -> None:
        """Test elbow angle calculation for left hand."""
        pose_landmarks = {
            "left_shoulder": [0.6, 0.3, 0.9],
            "left_elbow": [0.5, 0.4, 0.9],
            "left_wrist": [0.4, 0.5, 0.9],
        }

        angle = calculate_elbow_angle(pose_landmarks, "left", "serve")

        assert angle is not None
        assert 0.0 <= angle <= 180.0

    def test_calculate_elbow_angle_missing_keypoints(self) -> None:
        """Test elbow angle calculation with missing keypoints."""
        pose_landmarks = {
            "right_shoulder": [0.4, 0.3, 0.9],
            "right_elbow": [0.5, 0.4, 0.9],
        }

        angle = calculate_elbow_angle(pose_landmarks, "right", "serve")
        assert angle is None

    def test_calculate_elbow_angle_invalid_hand(self) -> None:
        """Test elbow angle calculation with invalid hand specification."""
        pose_landmarks = {
            "right_shoulder": [0.4, 0.3, 0.9],
            "right_elbow": [0.5, 0.4, 0.9],
            "right_wrist": [0.6, 0.5, 0.9],
        }

        angle = calculate_elbow_angle(pose_landmarks, "invalid", "serve")
        assert angle is None

    def test_calculate_elbow_angle_unsupported_stroke(self) -> None:
        """Test elbow angle calculation with unsupported stroke type."""
        pose_landmarks = {
            "right_shoulder": [0.4, 0.3, 0.9],
            "right_elbow": [0.5, 0.4, 0.9],
            "right_wrist": [0.6, 0.5, 0.9],
        }

        angle = calculate_elbow_angle(pose_landmarks, "right", "backhand")
        assert angle is None

    def test_calculate_elbow_angle_straight_arm(self) -> None:
        """Test elbow angle calculation for a straight arm (~180 degrees)."""
        pose_landmarks = {
            "right_shoulder": [0.3, 0.4, 0.9],
            "right_elbow": [0.5, 0.4, 0.9],
            "right_wrist": [0.7, 0.4, 0.9],
        }

        angle = calculate_elbow_angle(pose_landmarks, "right", "serve")

        assert angle is not None
        assert 170.0 <= angle <= 180.0

    def test_calculate_elbow_angle_bent_arm(self) -> None:
        """Test elbow angle calculation for a significantly bent arm."""
        pose_landmarks = {
            "right_shoulder": [0.4, 0.3, 0.9],
            "right_elbow": [0.4, 0.4, 0.9],
            "right_wrist": [0.5, 0.4, 0.9],
        }

        angle = calculate_elbow_angle(pose_landmarks, "right", "serve")

        assert angle is not None
        assert 80.0 <= angle <= 100.0
