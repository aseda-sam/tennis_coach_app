"""
Tests for improved ball contact detection using racket positions.
"""

from typing import Any, Dict, List

import pytest

from app.services.cv_service import detect_ball_contact_with_rackets


def create_mock_detections_with_rackets() -> tuple[
    List[List[Dict[str, Any]]], List[Dict[str, List[float]]], List[Dict[str, Any]]
]:
    """Create mock ball, pose, and racket detections for testing."""

    # Mock ball detections - ball appears in frames 10, 20, 30
    ball_detections = [[] for _ in range(50)]  # 50 frames

    # Frame 10: ball detected near racket head
    ball_detections[10] = [
        {
            "bbox": [150, 180, 160, 190],  # Ball center at (155, 185)
            "confidence": 0.9,
            "class_id": 32,
            "frame_index": 10,
        }
    ]

    # Frame 20: ball detected near wrist (no racket)
    ball_detections[20] = [
        {
            "bbox": [250, 200, 260, 210],  # Ball center at (255, 205)
            "confidence": 0.85,
            "class_id": 32,
            "frame_index": 20,
        }
    ]

    # Frame 30: ball detected near racket head again
    ball_detections[30] = [
        {
            "bbox": [148, 178, 152, 182],  # Ball center at (150, 180)
            "confidence": 0.92,
            "class_id": 32,
            "frame_index": 30,
        }
    ]

    # Mock pose detections - player present in all frames
    pose_detections = []
    for _i in range(50):
        pose_detections.append(
            {
                "left_wrist": [140, 170],  # Far from ball
                "right_wrist": [250, 200],  # Close to ball in frame 20
                "left_shoulder": [140, 160],
                "right_shoulder": [160, 160],
                "left_elbow": [145, 170],
                "right_elbow": [155, 170],
                "left_hip": [140, 220],
                "right_hip": [160, 220],
                "left_knee": [140, 260],
                "right_knee": [160, 260],
                "left_ankle": [140, 300],
                "right_ankle": [160, 300],
            }
        )

    # Mock racket positions - racket head available in frames 10 and 30
    racket_positions = [None for _ in range(50)]

    # Frame 10: racket head close to ball
    racket_positions[10] = {
        "center": [155, 185],  # Very close to ball center
        "confidence": 0.8,
        "closest_wrist": "right",
        "distance_to_wrist": 50.0,
        "score": 0.85,
    }

    # Frame 20: no racket position (should fall back to wrist-based)
    racket_positions[20] = None

    # Frame 30: racket head close to ball
    racket_positions[30] = {
        "center": [150, 180],  # Very close to ball center
        "confidence": 0.9,
        "closest_wrist": "right",
        "distance_to_wrist": 45.0,
        "score": 0.92,
    }

    return ball_detections, pose_detections, racket_positions


class TestImprovedBallContactDetection:
    """Test cases for improved ball contact detection functionality."""

    def test_racket_based_contact_detection(self) -> None:
        """Test contact detection using racket head positions."""
        ball_detections, pose_detections, racket_positions = (
            create_mock_detections_with_rackets()
        )
        fps = 30.0
        contact_threshold = 50.0
        racket_contact_threshold = 30.0

        contact_timestamps, contact_detections = detect_ball_contact_with_rackets(
            ball_detections=ball_detections,
            pose_detections=pose_detections,
            racket_positions=racket_positions,
            fps=fps,
            contact_threshold=contact_threshold,
            racket_contact_threshold=racket_contact_threshold,
        )

        # Should detect 3 contacts
        assert len(contact_timestamps) == 3
        assert len(contact_detections) == 3

        # Check timestamps are in ascending order
        assert contact_timestamps == sorted(contact_timestamps)

        # Check specific contact details
        assert contact_timestamps[0] == pytest.approx(10.0 / fps, rel=1e-6)  # Frame 10
        assert contact_timestamps[1] == pytest.approx(20.0 / fps, rel=1e-6)  # Frame 20
        assert contact_timestamps[2] == pytest.approx(30.0 / fps, rel=1e-6)  # Frame 30

        # Check contact types
        assert (
            contact_detections[0]["contact_type"] == "racket"
        )  # Frame 10: racket-based
        assert (
            contact_detections[1]["contact_type"] == "wrist"
        )  # Frame 20: wrist-based (no racket)
        assert (
            contact_detections[2]["contact_type"] == "racket"
        )  # Frame 30: racket-based

        # Check racket data is present for racket-based contacts
        assert contact_detections[0]["racket_data"] is not None
        assert contact_detections[0]["racket_data"]["racket_center"] == [155, 185]
        assert contact_detections[1]["racket_data"] is None  # Wrist-based contact
        assert contact_detections[2]["racket_data"] is not None
        assert contact_detections[2]["racket_data"]["racket_center"] == [150, 180]

    def test_fallback_to_wrist_based_detection(self) -> None:
        """Test fallback to wrist-based detection when no racket position available."""
        ball_detections = [[] for _ in range(10)]
        ball_detections[5] = [
            {
                "bbox": [100, 100, 110, 110],  # Ball center at (105, 105)
                "confidence": 0.9,
                "class_id": 32,
                "frame_index": 5,
            }
        ]

        pose_detections = [None for _ in range(10)]
        pose_detections[5] = {
            "left_wrist": [200, 200],  # Far from ball
            "right_wrist": [106, 106],  # Close to ball
        }

        racket_positions = [None for _ in range(10)]  # No racket positions

        fps = 30.0
        contact_threshold = 50.0
        racket_contact_threshold = 30.0

        contact_timestamps, contact_detections = detect_ball_contact_with_rackets(
            ball_detections=ball_detections,
            pose_detections=pose_detections,
            racket_positions=racket_positions,
            fps=fps,
            contact_threshold=contact_threshold,
            racket_contact_threshold=racket_contact_threshold,
        )

        assert len(contact_timestamps) == 1
        assert contact_detections[0]["contact_type"] == "wrist"
        assert contact_detections[0]["contact_hand"] == "right"
        assert contact_detections[0]["racket_data"] is None
        assert contact_detections[0]["distance"] == pytest.approx(
            1.414, rel=1e-3
        )  # sqrt(1^2 + 1^2)

    def test_racket_contact_threshold(self) -> None:
        """Test that racket contact threshold is respected."""
        ball_detections = [[] for _ in range(10)]
        ball_detections[5] = [
            {
                "bbox": [100, 100, 110, 110],  # Ball center at (105, 105)
                "confidence": 0.9,
                "class_id": 32,
                "frame_index": 5,
            }
        ]

        pose_detections = [None for _ in range(10)]
        pose_detections[5] = {
            "left_wrist": [200, 200],  # Far from ball
            "right_wrist": [200, 200],  # Far from ball
        }

        racket_positions = [None for _ in range(10)]
        racket_positions[5] = {
            "center": [140, 140],  # 35 pixels from ball (above 30 threshold)
            "confidence": 0.8,
            "closest_wrist": "right",
            "distance_to_wrist": 50.0,
            "score": 0.85,
        }

        fps = 30.0
        contact_threshold = 50.0
        racket_contact_threshold = 30.0  # Ball is 35 pixels away, should not detect

        contact_timestamps, contact_detections = detect_ball_contact_with_rackets(
            ball_detections=ball_detections,
            pose_detections=pose_detections,
            racket_positions=racket_positions,
            fps=fps,
            contact_threshold=contact_threshold,
            racket_contact_threshold=racket_contact_threshold,
        )

        # Should not detect contact because ball is too far from racket
        assert len(contact_timestamps) == 0
        assert len(contact_detections) == 0

    def test_contact_detection_statistics(self) -> None:
        """Test that contact detection provides correct statistics."""
        ball_detections, pose_detections, racket_positions = (
            create_mock_detections_with_rackets()
        )
        fps = 30.0

        contact_timestamps, contact_detections = detect_ball_contact_with_rackets(
            ball_detections=ball_detections,
            pose_detections=pose_detections,
            racket_positions=racket_positions,
            fps=fps,
            contact_threshold=50.0,
            racket_contact_threshold=30.0,
        )

        # Count contact types
        racket_contacts = sum(
            1 for d in contact_detections if d["contact_type"] == "racket"
        )
        wrist_contacts = sum(
            1 for d in contact_detections if d["contact_type"] == "wrist"
        )

        assert racket_contacts == 2  # Frames 10 and 30
        assert wrist_contacts == 1  # Frame 20
        assert len(contact_detections) == racket_contacts + wrist_contacts
