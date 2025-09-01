"""
Tests for ball contact detection functionality.
"""

from typing import Any, Dict, List

import pytest
from sqlalchemy.orm import Session

from app.models.video import Video
from app.services.ball_contact_service import (
    ALLOWED_BALL_CONTACT_FIELDS,
    create_ball_contact,
    update_ball_contact,
)
from app.services.cv_service import detect_ball_contact


def create_mock_detections() -> tuple[
    List[List[Dict[str, Any]]], List[Dict[str, List[float]]]
]:
    """Create mock ball and pose detections for testing."""

    # Mock ball detections - ball appears in frames 10, 20, 30
    ball_detections = [[] for _ in range(50)]  # 50 frames

    # Frame 10: ball detected near left wrist
    ball_detections[10] = [
        {
            "bbox": [
                145,
                175,
                155,
                185,
            ],  # Ball center at (150, 180) - close to left wrist
            "confidence": 0.9,
            "class_id": 32,
            "frame_index": 10,
        }
    ]

    # Frame 20: ball detected near right wrist
    ball_detections[20] = [
        {
            "bbox": [
                245,
                195,
                255,
                205,
            ],  # Ball center at (250, 200) - close to right wrist
            "confidence": 0.85,
            "class_id": 32,
            "frame_index": 20,
        }
    ]

    # Frame 30: ball detected near left wrist again
    ball_detections[30] = [
        {
            "bbox": [
                148,
                178,
                152,
                182,
            ],  # Ball center at (150, 180) - very close to left wrist
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
                "left_wrist": [150, 180],  # Close to ball in frame 10 and 30
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

    return ball_detections, pose_detections


class TestBallContactDetection:
    """Test cases for ball contact detection functionality."""

    def test_contact_detection_with_valid_data(self) -> None:
        """Test contact detection with valid ball and pose data."""
        ball_detections, pose_detections = create_mock_detections()
        fps = 30.0
        contact_threshold = 50.0

        contact_timestamps, contact_detections = detect_ball_contact(
            ball_detections=ball_detections,
            pose_detections=pose_detections,
            fps=fps,
            contact_threshold=contact_threshold,
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

        # Check contact details
        assert contact_detections[0]["frame_index"] == 10
        assert contact_detections[0]["contact_hand"] == "left"
        assert contact_detections[1]["frame_index"] == 20
        assert contact_detections[1]["contact_hand"] == "right"
        assert contact_detections[2]["frame_index"] == 30
        assert contact_detections[2]["contact_hand"] == "left"

    def test_contact_detection_with_no_ball_detections(self) -> None:
        """Test contact detection when no balls are detected."""
        ball_detections = [[] for _ in range(50)]  # No ball detections
        pose_detections = [
            {"left_wrist": [150, 180], "right_wrist": [250, 200]} for _ in range(50)
        ]
        fps = 30.0
        contact_threshold = 50.0

        contact_timestamps, contact_detections = detect_ball_contact(
            ball_detections=ball_detections,
            pose_detections=pose_detections,
            fps=fps,
            contact_threshold=contact_threshold,
        )

        assert len(contact_timestamps) == 0
        assert len(contact_detections) == 0

    def test_contact_detection_with_no_pose_detections(self) -> None:
        """Test contact detection when no poses are detected."""
        ball_detections = [[] for _ in range(50)]
        ball_detections[10] = [
            {
                "bbox": [145, 175, 155, 185],
                "confidence": 0.9,
                "class_id": 32,
                "frame_index": 10,
            }
        ]
        pose_detections = [None for _ in range(50)]  # No pose detections
        fps = 30.0
        contact_threshold = 50.0

        contact_timestamps, contact_detections = detect_ball_contact(
            ball_detections=ball_detections,
            pose_detections=pose_detections,
            fps=fps,
            contact_threshold=contact_threshold,
        )

        assert len(contact_timestamps) == 0
        assert len(contact_detections) == 0

    def test_contact_detection_distance_calculation(self) -> None:
        """Test that distance calculation is working correctly."""
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
            "left_wrist": [105, 105],  # Exact same position as ball
            "right_wrist": [200, 200],  # Far from ball
        }

        fps = 30.0
        contact_threshold = 50.0

        contact_timestamps, contact_detections = detect_ball_contact(
            ball_detections=ball_detections,
            pose_detections=pose_detections,
            fps=fps,
            contact_threshold=contact_threshold,
        )

        assert len(contact_timestamps) == 1
        assert contact_detections[0]["distance"] == pytest.approx(0.0, rel=1e-6)
        assert contact_detections[0]["contact_hand"] == "left"

    def test_contact_detection_hand_selection(self) -> None:
        """Test that the closest hand is selected for contact."""
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

        fps = 30.0
        contact_threshold = 50.0

        contact_timestamps, contact_detections = detect_ball_contact(
            ball_detections=ball_detections,
            pose_detections=pose_detections,
            fps=fps,
            contact_threshold=contact_threshold,
        )

        assert len(contact_timestamps) == 1
        assert contact_detections[0]["contact_hand"] == "right"
        assert contact_detections[0]["distance"] == pytest.approx(
            1.414, rel=1e-3
        )  # sqrt(1^2 + 1^2)


class TestBallContactServiceSecurity:
    """Test cases for ball contact service security features."""

    def test_allowed_fields_constant(self) -> None:
        """Test that ALLOWED_BALL_CONTACT_FIELDS contains all valid fields."""
        expected_fields = {
            "frame_number",
            "video_timestamp",
            "player",
            "contact_hand",
            "stroke_type",
            "stroke_subtype",
            "confidence",
            "ball_position",
            "player_position",
            "description",
            "detection_source",
            "ball_area",
            "ball_size_factor",
            "racket_data",
            "ball_bbox",
            "ball_racket_distance",
        }
        assert expected_fields == ALLOWED_BALL_CONTACT_FIELDS

    def test_update_ball_contact_with_valid_fields(self, db_session: Session) -> None:
        """Test that update_ball_contact accepts valid fields."""
        # Create a test video first
        video = Video(
            filename="test_video.mp4",
            file_path="/test/path",
            file_size=1024000,  # 1MB
            duration=60.0,
            fps=30.0,
            frame_count=1800,
        )
        db_session.add(video)
        db_session.commit()
        db_session.refresh(video)

        # Create a test ball contact
        contact = create_ball_contact(
            db=db_session,
            video_id=video.id,
            video_timestamp=1.5,
            contact_hand="right",
            stroke_type="ground_stroke",
            stroke_subtype="forehand",
            detection_source="manual",
        )

        # Update with valid fields
        updated_contact = update_ball_contact(
            db=db_session,
            ball_contact_id=contact.id,
            confidence=0.95,
            description="Updated description",
            stroke_type="serve",
        )

        assert updated_contact.confidence == 0.95
        assert updated_contact.description == "Updated description"
        assert updated_contact.stroke_type == "serve"

    def test_update_ball_contact_with_invalid_fields(self, db_session: Session) -> None:
        """Test that update_ball_contact rejects invalid fields."""
        # Create a test video first
        video = Video(
            filename="test_video_invalid_fields.mp4",
            file_path="/test/path",
            file_size=1024000,  # 1MB
            duration=60.0,
            fps=30.0,
            frame_count=1800,
        )
        db_session.add(video)
        db_session.commit()
        db_session.refresh(video)

        # Create a test ball contact
        contact = create_ball_contact(
            db=db_session,
            video_id=video.id,
            video_timestamp=1.5,
            contact_hand="right",
            stroke_type="ground_stroke",
            stroke_subtype="forehand",
            detection_source="manual",
        )

        # Try to update with invalid fields
        with pytest.raises(ValueError, match="Invalid fields for update"):
            update_ball_contact(
                db=db_session,
                ball_contact_id=contact.id,
                invalid_field="should_fail",
                another_invalid_field="should_also_fail",
            )

    def test_update_ball_contact_with_mixed_valid_invalid_fields(
        self, db_session: Session
    ) -> None:
        """Test that update_ball_contact rejects when any field is invalid."""
        # Create a test video first
        video = Video(
            filename="test_video_mixed_fields.mp4",
            file_path="/test/path",
            file_size=1024000,  # 1MB
            duration=60.0,
            fps=30.0,
            frame_count=1800,
        )
        db_session.add(video)
        db_session.commit()
        db_session.refresh(video)

        # Create a test ball contact
        contact = create_ball_contact(
            db=db_session,
            video_id=video.id,
            video_timestamp=1.5,
            contact_hand="right",
            stroke_type="ground_stroke",
            stroke_subtype="forehand",
            detection_source="manual",
        )

        # Try to update with mix of valid and invalid fields
        with pytest.raises(ValueError, match="Invalid fields for update"):
            update_ball_contact(
                db=db_session,
                ball_contact_id=contact.id,
                confidence=0.95,  # Valid field
                invalid_field="should_fail",  # Invalid field
            )

    def test_update_ball_contact_sql_injection_prevention(
        self, db_session: Session
    ) -> None:
        """Test that update_ball_contact prevents SQL injection attempts."""
        # Create a test video first
        video = Video(
            filename="test_video_sql_injection.mp4",
            file_path="/test/path",
            file_size=1024000,  # 1MB
            duration=60.0,
            fps=30.0,
            frame_count=1800,
        )
        db_session.add(video)
        db_session.commit()
        db_session.refresh(video)

        # Create a test ball contact
        contact = create_ball_contact(
            db=db_session,
            video_id=video.id,
            video_timestamp=1.5,
            contact_hand="right",
            stroke_type="ground_stroke",
            stroke_subtype="forehand",
            detection_source="manual",
        )

        # Try to inject malicious field names
        malicious_fields = [
            "id; DROP TABLE ball_contacts; --",
            "__class__",
            "__dict__",
            "_sa_instance_state",
            "query",
            "metadata",
        ]

        for malicious_field in malicious_fields:
            with pytest.raises(ValueError, match="Invalid fields for update"):
                update_ball_contact(
                    db=db_session,
                    ball_contact_id=contact.id,
                    **{malicious_field: "malicious_value"},
                )
