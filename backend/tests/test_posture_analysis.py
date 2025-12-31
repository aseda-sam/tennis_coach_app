"""
Tests for posture analysis service and API endpoints.

These tests cover elbow angle calculation, pose data retrieval,
and posture analysis for ball contacts with comprehensive test data.
"""

import json

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.models.ball_contact import BallContact
from app.models.pose_detection import PoseDetection
from app.models.video import Video
from app.services.posture_analysis import (
    analyze_and_store_contact_posture,
    analyze_contact_posture,
    calculate_elbow_angle,
    get_pose_at_contact,
)


class TestPostureAnalysisService:
    """Test posture analysis service functionality."""

    def test_calculate_elbow_angle_valid_data(self) -> None:
        """Test elbow angle calculation with valid pose landmarks."""
        # Sample pose landmarks for a right-handed forehand
        pose_landmarks = {
            "right_shoulder": [0.4, 0.3, 0.9],  # [x, y, confidence]
            "right_elbow": [0.5, 0.4, 0.9],
            "right_wrist": [0.6, 0.5, 0.9],
        }

        angle = calculate_elbow_angle(pose_landmarks, "right", "forehand")

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

        angle = calculate_elbow_angle(pose_landmarks, "left", "forehand")

        assert angle is not None
        assert 0.0 <= angle <= 180.0

    def test_calculate_elbow_angle_missing_keypoints(self) -> None:
        """Test elbow angle calculation with missing keypoints."""
        # Missing wrist keypoint
        pose_landmarks = {
            "right_shoulder": [0.4, 0.3, 0.9],
            "right_elbow": [0.5, 0.4, 0.9],
        }

        angle = calculate_elbow_angle(pose_landmarks, "right", "forehand")
        assert angle is None

    def test_calculate_elbow_angle_invalid_hand(self) -> None:
        """Test elbow angle calculation with invalid hand specification."""
        pose_landmarks = {
            "right_shoulder": [0.4, 0.3, 0.9],
            "right_elbow": [0.5, 0.4, 0.9],
            "right_wrist": [0.6, 0.5, 0.9],
        }

        angle = calculate_elbow_angle(pose_landmarks, "invalid", "forehand")
        assert angle is None

    def test_calculate_elbow_angle_unsupported_stroke(self) -> None:
        """Test elbow angle calculation with unsupported stroke type."""
        pose_landmarks = {
            "right_shoulder": [0.4, 0.3, 0.9],
            "right_elbow": [0.5, 0.4, 0.9],
            "right_wrist": [0.6, 0.5, 0.9],
        }

        # Backhand is not supported yet (too complex for MVP)
        angle = calculate_elbow_angle(pose_landmarks, "right", "backhand")
        assert angle is None

    def test_calculate_elbow_angle_straight_arm(self) -> None:
        """Test elbow angle calculation for a straight arm (~180 degrees)."""
        # Aligned points for straight arm
        pose_landmarks = {
            "right_shoulder": [0.3, 0.4, 0.9],
            "right_elbow": [0.5, 0.4, 0.9],  # Same y-coordinate
            "right_wrist": [0.7, 0.4, 0.9],
        }

        angle = calculate_elbow_angle(pose_landmarks, "right", "forehand")

        assert angle is not None
        # Should be close to 180 degrees for a straight arm
        assert 170.0 <= angle <= 180.0

    def test_calculate_elbow_angle_bent_arm(self) -> None:
        """Test elbow angle calculation for a significantly bent arm."""
        # L-shaped arm configuration (~90 degrees)
        pose_landmarks = {
            "right_shoulder": [0.4, 0.3, 0.9],
            "right_elbow": [0.4, 0.4, 0.9],  # Directly below shoulder
            "right_wrist": [0.5, 0.4, 0.9],  # To the right of elbow
        }

        angle = calculate_elbow_angle(pose_landmarks, "right", "forehand")

        assert angle is not None
        # Should be close to 90 degrees for L-shaped arm
        assert 80.0 <= angle <= 100.0

    def test_get_pose_at_contact_exact_frame(self, db_session: Session, test_user_id: str) -> None:
        """Test pose retrieval when exact frame exists."""
        # Create test video
        video = Video(
            filename="test_pose.mp4",
            file_path="/test/path.mp4",
            file_size=1000,
            content_type="video/mp4",
            fps=30.0,
            user_id=test_user_id,
        )
        db_session.add(video)
        db_session.flush()

        # Create sample pose data for 3 frames
        pose_data = [
            None,  # Frame 0 - no pose
            {  # Frame 1 - pose data
                "right_shoulder": [0.4, 0.3, 0.9],
                "right_elbow": [0.5, 0.4, 0.9],
                "right_wrist": [0.6, 0.5, 0.9],
            },
            None,  # Frame 2 - no pose
        ]

        # Create pose detection
        pose_detection = PoseDetection(
            video_id=video.id,
            status="completed",
            total_frames=3,
            frames_with_poses=1,
            detection_rate=0.33,
            pose_data=json.dumps(pose_data),
            processing_time_seconds=1.5,
        )
        db_session.add(pose_detection)

        # Create ball contact at 1/30 second (should map to frame 1)
        ball_contact = BallContact(
            video_id=video.id,
            video_timestamp=1.0 / 30.0,  # 0.033 seconds
            contact_hand="right",
            stroke_type="forehand",
        )
        db_session.add(ball_contact)
        db_session.commit()

        # Test pose retrieval
        pose_landmarks = get_pose_at_contact(ball_contact, pose_detection, video)

        assert pose_landmarks is not None
        assert "right_shoulder" in pose_landmarks
        assert "right_elbow" in pose_landmarks
        assert "right_wrist" in pose_landmarks

    def test_get_pose_at_contact_nearby_frame(self, db_session: Session, test_user_id: str) -> None:
        """Test pose retrieval when exact frame is missing but nearby frame exists."""
        # Create test video
        video = Video(
            filename="test_pose_nearby.mp4",
            file_path="/test/path.mp4",
            file_size=1000,
            content_type="video/mp4",
            fps=30.0,
            user_id=test_user_id,
        )
        db_session.add(video)
        db_session.flush()

        # Create pose data where target frame is missing but nearby frame exists
        pose_data = [
            None,  # Frame 0 - no pose
            None,  # Frame 1 - no pose (target frame)
            {  # Frame 2 - pose data (nearby frame)
                "right_shoulder": [0.4, 0.3, 0.9],
                "right_elbow": [0.5, 0.4, 0.9],
                "right_wrist": [0.6, 0.5, 0.9],
            },
        ]

        # Create pose detection
        pose_detection = PoseDetection(
            video_id=video.id,
            status="completed",
            total_frames=3,
            frames_with_poses=1,
            detection_rate=0.33,
            pose_data=json.dumps(pose_data),
            processing_time_seconds=2.0,
        )
        db_session.add(pose_detection)

        # Create ball contact at frame 1 (no pose), should find frame 2
        ball_contact = BallContact(
            video_id=video.id,
            video_timestamp=1.0 / 30.0,
            contact_hand="right",
            stroke_type="forehand",
        )
        db_session.add(ball_contact)
        db_session.commit()

        # Test pose retrieval - should find nearby frame
        pose_landmarks = get_pose_at_contact(ball_contact, pose_detection, video)

        assert pose_landmarks is not None
        assert "right_shoulder" in pose_landmarks

    def test_get_pose_at_contact_no_data(self, db_session: Session, test_user_id: str) -> None:
        """Test pose retrieval when no pose data is available."""
        # Create test video
        video = Video(
            filename="test_no_pose.mp4",
            file_path="/test/path.mp4",
            file_size=1000,
            content_type="video/mp4",
            fps=30.0,
            user_id=test_user_id,
        )
        db_session.add(video)
        db_session.flush()

        # Create pose detection with no data
        pose_detection = PoseDetection(
            video_id=video.id,
            status="completed",
            total_frames=10,
            frames_with_poses=0,
            detection_rate=0.0,
            pose_data=json.dumps([None] * 10),
            processing_time_seconds=3.0,
        )
        db_session.add(pose_detection)

        # Create ball contact
        ball_contact = BallContact(
            video_id=video.id,
            video_timestamp=0.5,
            contact_hand="right",
            stroke_type="forehand",
        )
        db_session.add(ball_contact)
        db_session.commit()

        # Test pose retrieval - should return None
        pose_landmarks = get_pose_at_contact(ball_contact, pose_detection, video)
        assert pose_landmarks is None

    def test_analyze_contact_posture_success(self, db_session: Session, test_user_id: str) -> None:
        """Test successful contact posture analysis."""
        # Create test video
        video = Video(
            filename="test_analysis.mp4",
            file_path="/test/path.mp4",
            file_size=1000,
            content_type="video/mp4",
            fps=30.0,
            user_id=test_user_id,
        )
        db_session.add(video)
        db_session.flush()

        # Create pose data with valid keypoints
        pose_data = [
            {
                "right_shoulder": [0.4, 0.3, 0.9],
                "right_elbow": [0.5, 0.4, 0.9],
                "right_wrist": [0.6, 0.5, 0.9],
            }
        ]

        # Create pose detection
        pose_detection = PoseDetection(
            video_id=video.id,
            status="completed",
            total_frames=1,
            frames_with_poses=1,
            detection_rate=1.0,
            pose_data=json.dumps(pose_data),
            processing_time_seconds=1.0,
        )
        db_session.add(pose_detection)

        # Create ball contact
        ball_contact = BallContact(
            video_id=video.id,
            video_timestamp=0.0,
            contact_hand="right",
            stroke_type="forehand",
        )
        db_session.add(ball_contact)
        db_session.commit()

        # Test analysis
        elbow_angle = analyze_contact_posture(db_session, ball_contact.id)

        assert elbow_angle is not None
        assert 0.0 <= elbow_angle <= 180.0

    def test_analyze_contact_posture_missing_contact(self, db_session: Session, test_user_id: str) -> None:
        """Test posture analysis with missing ball contact."""
        elbow_angle = analyze_contact_posture(db_session, 999)  # Non-existent ID
        assert elbow_angle is None

    def test_analyze_and_store_contact_posture_success(
        self, db_session: Session, test_user_id: str
    ) -> None:
        """Test analyze and store functionality with successful analysis."""
        # Create test data similar to previous test
        video = Video(
            filename="test_store.mp4",
            file_path="/test/path.mp4",
            file_size=1000,
            content_type="video/mp4",
            fps=30.0,
            user_id=test_user_id,
        )
        db_session.add(video)
        db_session.flush()

        pose_data = [
            {
                "right_shoulder": [0.4, 0.3, 0.9],
                "right_elbow": [0.5, 0.4, 0.9],
                "right_wrist": [0.6, 0.5, 0.9],
            }
        ]

        pose_detection = PoseDetection(
            video_id=video.id,
            status="completed",
            total_frames=1,
            frames_with_poses=1,
            detection_rate=1.0,
            pose_data=json.dumps(pose_data),
            processing_time_seconds=1.0,
        )
        db_session.add(pose_detection)

        ball_contact = BallContact(
            video_id=video.id,
            video_timestamp=0.0,
            contact_hand="right",
            stroke_type="forehand",
        )
        db_session.add(ball_contact)
        db_session.commit()

        # Test analyze and store
        result = analyze_and_store_contact_posture(db_session, ball_contact.id)

        assert result["analysis_status"] == "success"
        assert result["elbow_angle"] is not None
        assert 0.0 <= result["elbow_angle"] <= 180.0
        assert "message" in result

        # Verify data was stored in database
        db_session.refresh(ball_contact)
        assert ball_contact.elbow_angle is not None
        assert ball_contact.elbow_angle == result["elbow_angle"]

    def test_analyze_and_store_contact_posture_already_analyzed(
        self, db_session: Session, test_user_id: str
    ) -> None:
        """Test analyze and store when contact is already analyzed."""
        # Create ball contact with existing elbow angle
        video = Video(
            filename="test_existing.mp4",
            file_path="/test/path.mp4",
            file_size=1000,
            content_type="video/mp4",
            fps=30.0,
            user_id=test_user_id,
        )
        db_session.add(video)
        db_session.flush()

        ball_contact = BallContact(
            video_id=video.id,
            video_timestamp=0.0,
            contact_hand="right",
            stroke_type="forehand",
            elbow_angle=120.5,  # Already analyzed
        )
        db_session.add(ball_contact)
        db_session.commit()

        # Test analyze and store without force_reanalysis
        result = analyze_and_store_contact_posture(
            db_session, ball_contact.id, force_reanalysis=False
        )

        assert result["analysis_status"] == "success"
        assert result["elbow_angle"] == 120.5
        assert "already completed" in result["message"]

    def test_analyze_and_store_contact_posture_force_reanalysis(
        self, db_session: Session, test_user_id: str
    ) -> None:
        """Test forced reanalysis of already analyzed contact."""
        # Create test data
        video = Video(
            filename="test_force.mp4",
            file_path="/test/path.mp4",
            file_size=1000,
            content_type="video/mp4",
            fps=30.0,
            user_id=test_user_id,
        )
        db_session.add(video)
        db_session.flush()

        pose_data = [
            {
                "right_shoulder": [0.4, 0.3, 0.9],
                "right_elbow": [0.5, 0.4, 0.9],
                "right_wrist": [0.6, 0.5, 0.9],
            }
        ]

        pose_detection = PoseDetection(
            video_id=video.id,
            status="completed",
            total_frames=1,
            frames_with_poses=1,
            detection_rate=1.0,
            pose_data=json.dumps(pose_data),
            processing_time_seconds=1.0,
        )
        db_session.add(pose_detection)

        ball_contact = BallContact(
            video_id=video.id,
            video_timestamp=0.0,
            contact_hand="right",
            stroke_type="forehand",
            elbow_angle=999.0,  # Existing but wrong value
        )
        db_session.add(ball_contact)
        db_session.commit()

        # Test forced reanalysis
        result = analyze_and_store_contact_posture(
            db_session, ball_contact.id, force_reanalysis=True
        )

        assert result["analysis_status"] == "success"
        assert result["elbow_angle"] != 999.0  # Should be recalculated
        assert 0.0 <= result["elbow_angle"] <= 180.0

    def test_analyze_and_store_contact_posture_unsupported_stroke(
        self, db_session: Session, test_user_id: str
    ) -> None:
        """Test analyze and store with unsupported stroke type."""
        video = Video(
            filename="test_unsupported.mp4",
            file_path="/test/path.mp4",
            file_size=1000,
            content_type="video/mp4",
            fps=30.0,
            user_id=test_user_id,
        )
        db_session.add(video)
        db_session.flush()

        ball_contact = BallContact(
            video_id=video.id,
            video_timestamp=0.0,
            contact_hand="right",
            stroke_type="backhand",  # Not supported yet
        )
        db_session.add(ball_contact)
        db_session.commit()

        # Test analysis with unsupported stroke
        result = analyze_and_store_contact_posture(db_session, ball_contact.id)

        assert result["analysis_status"] == "invalid_stroke"
        assert result["elbow_angle"] is None
        assert "not supported" in result["message"]


class TestPostureAnalysisAPI:
    """Test posture analysis API endpoints."""

    def test_analyze_ball_contact_posture_success(
        self, client: TestClient, db_session: Session, test_user_id: str
    ) -> None:
        """Test successful ball contact posture analysis via API."""
        # Create test data
        video = Video(
            filename="test_api.mp4",
            file_path="/test/path.mp4",
            file_size=1000,
            content_type="video/mp4",
            fps=30.0,
            user_id=test_user_id,
        )
        db_session.add(video)
        db_session.flush()

        pose_data = [
            {
                "right_shoulder": [0.4, 0.3, 0.9],
                "right_elbow": [0.5, 0.4, 0.9],
                "right_wrist": [0.6, 0.5, 0.9],
            }
        ]

        pose_detection = PoseDetection(
            video_id=video.id,
            status="completed",
            total_frames=1,
            frames_with_poses=1,
            detection_rate=1.0,
            pose_data=json.dumps(pose_data),
            processing_time_seconds=1.0,
        )
        db_session.add(pose_detection)

        ball_contact = BallContact(
            video_id=video.id,
            video_timestamp=0.0,
            contact_hand="right",
            stroke_type="forehand",
        )
        db_session.add(ball_contact)
        db_session.commit()

        # Test API endpoint
        response = client.post(
            f"/v0/ball-contacts/{ball_contact.id}/analyze-posture",
            json={"force_reanalysis": False},
        )

        assert response.status_code == 200
        data = response.json()

        assert data["ball_contact_id"] == ball_contact.id
        assert data["analysis_status"] == "success"
        assert data["elbow_angle"] is not None
        assert 0.0 <= data["elbow_angle"] <= 180.0

    def test_analyze_ball_contact_posture_not_found(self, client: TestClient) -> None:
        """Test posture analysis API with non-existent ball contact."""
        response = client.post(
            "/v0/ball-contacts/999/analyze-posture", json={"force_reanalysis": False}
        )

        assert response.status_code == 200
        data = response.json()
        assert data["analysis_status"] == "failed"
        assert "not found" in data["message"].lower()

    def test_get_ball_contact_posture_analysis(
        self, client: TestClient, db_session: Session, test_user_id: str
    ) -> None:
        """Test retrieving existing posture analysis via API."""
        # Create ball contact with existing analysis
        video = Video(
            filename="test_get.mp4",
            file_path="/test/path.mp4",
            file_size=1000,
            content_type="video/mp4",
            fps=30.0,
            user_id=test_user_id,
        )
        db_session.add(video)
        db_session.flush()

        ball_contact = BallContact(
            video_id=video.id,
            video_timestamp=0.0,
            contact_hand="right",
            stroke_type="forehand",
            elbow_angle=135.5,
        )
        db_session.add(ball_contact)
        db_session.commit()

        # Test API endpoint
        response = client.get(f"/v0/ball-contacts/{ball_contact.id}/posture-analysis")

        assert response.status_code == 200
        data = response.json()

        assert data["ball_contact_id"] == ball_contact.id
        assert data["analysis_status"] == "success"
        assert data["elbow_angle"] == 135.5


@pytest.mark.integration
class TestPostureAnalysisIntegration:
    """Integration tests for posture analysis with real-like data."""

    def test_full_posture_analysis_workflow(
        self, client: TestClient, db_session: Session, test_user_id: str
    ) -> None:
        """Test complete posture analysis workflow with video upload and ball contact creation."""
        # This test simulates the real workflow:
        # 1. Upload video -> 2. Create pose detection -> 3. Create ball contacts -> 4. Analyze posture

        # Create test video record (simulating upload)
        video = Video(
            filename="integration_test.mp4",
            file_path="/test/integration.mp4",
            file_size=5000000,
            content_type="video/mp4",
            fps=30.0,
            duration=10.0,
            width=1920,
            height=1080,
            frame_count=300,
            user_id=test_user_id,
        )
        db_session.add(video)
        db_session.flush()

        # Create pose detection (simulating completed pose analysis)
        sample_pose_frames = []
        for i in range(300):  # 10 seconds at 30fps
            if i % 5 == 0:  # Every 5th frame has pose data
                sample_pose_frames.append(
                    {
                        "right_shoulder": [0.4 + i * 0.001, 0.3, 0.9],
                        "right_elbow": [0.5 + i * 0.001, 0.4, 0.9],
                        "right_wrist": [0.6 + i * 0.001, 0.5, 0.9],
                        "left_shoulder": [0.6 - i * 0.001, 0.3, 0.9],
                        "left_elbow": [0.5 - i * 0.001, 0.4, 0.9],
                        "left_wrist": [0.4 - i * 0.001, 0.5, 0.9],
                    }
                )
            else:
                sample_pose_frames.append(None)

        pose_detection = PoseDetection(
            video_id=video.id,
            status="completed",
            total_frames=300,
            frames_with_poses=60,  # Every 5th frame
            detection_rate=0.2,
            pose_data=json.dumps(sample_pose_frames),
            processing_time_seconds=15.0,
        )
        db_session.add(pose_detection)

        # Create multiple ball contacts
        ball_contacts = [
            BallContact(
                video_id=video.id,
                video_timestamp=2.5,
                contact_hand="right",
                stroke_type="forehand",
            ),
            BallContact(
                video_id=video.id,
                video_timestamp=5.0,
                contact_hand="left",
                stroke_type="forehand",
            ),
            BallContact(
                video_id=video.id,
                video_timestamp=7.5,
                contact_hand="right",
                stroke_type="forehand",
            ),
        ]
        db_session.add_all(ball_contacts)
        db_session.commit()

        # Test batch posture analysis via API
        response = client.post(
            f"/v0/ball-contacts/video/{video.id}/analyze-posture",
            json={"force_reanalysis": False},
        )

        assert response.status_code == 200
        results = response.json()

        # Should have analysis for all contacts
        assert len(results) == 3

        # Check each result
        for i, result in enumerate(results):
            assert result["ball_contact_id"] == ball_contacts[i].id
            assert result["analysis_status"] == "success"
            assert result["elbow_angle"] is not None
            assert 0.0 <= result["elbow_angle"] <= 180.0

        # Verify data was stored in database
        for contact in ball_contacts:
            db_session.refresh(contact)
            assert contact.elbow_angle is not None
