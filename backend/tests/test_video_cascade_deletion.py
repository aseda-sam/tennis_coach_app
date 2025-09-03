"""
Test video cascade deletion to ensure all related records are properly deleted.
"""

from sqlalchemy.orm import Session

from app.models.ball_detection import BallDetection
from app.models.pose_detection import PoseDetection
from app.models.video import Video
from app.services.video_service import delete_video_with_analyses


class TestVideoCascadeDeletion:
    """Test that video deletion properly cascades to all related records."""

    def test_video_deletion_cascades_to_pose_detection(
        self, db_session: Session
    ) -> None:
        """Test that deleting a video also deletes associated pose detection records."""
        # Create a test video
        video = Video(
            filename="test_cascade_video.mp4",
            file_path="/path/to/test_cascade_video.mp4",
            file_size=1000,
        )
        db_session.add(video)
        db_session.commit()
        db_session.refresh(video)

        # Create a pose detection record for this video
        pose_detection = PoseDetection(
            video_id=video.id,
            total_frames=100,
            frames_with_poses=50,
            total_pose_detections=50,
            detection_rate=0.5,
            confidence_threshold=0.5,
            detection_threshold=0.5,
            processing_time_seconds=10.0,
            status="completed",
        )
        db_session.add(pose_detection)
        db_session.commit()
        db_session.refresh(pose_detection)

        # Verify the pose detection was created
        assert pose_detection.id is not None
        assert pose_detection.video_id == video.id

        # Delete the video
        success, filename, deleted_video_id = delete_video_with_analyses(
            db_session, video.id
        )

        # Verify deletion was successful
        assert success is True
        assert deleted_video_id == video.id
        assert filename == "test_cascade_video.mp4"

        # Verify the video is deleted
        deleted_video = db_session.query(Video).filter(Video.id == video.id).first()
        assert deleted_video is None

        # Verify the pose detection is also deleted (cascade should handle this)
        deleted_pose_detection = (
            db_session.query(PoseDetection)
            .filter(PoseDetection.id == pose_detection.id)
            .first()
        )
        assert deleted_pose_detection is None

    def test_video_deletion_cascades_to_ball_detection(
        self, db_session: Session
    ) -> None:
        """Test that deleting a video also deletes associated ball detection records."""
        # Create a test video
        video = Video(
            filename="test_cascade_ball_video.mp4",
            file_path="/path/to/test_cascade_ball_video.mp4",
            file_size=2000,
        )
        db_session.add(video)
        db_session.commit()
        db_session.refresh(video)

        # Create a ball detection record for this video
        ball_detection = BallDetection(
            video_id=video.id,
            total_frames=200,
            frames_with_balls=100,
            total_ball_detections=100,
            average_detections_per_frame=0.5,
            detection_rate=0.5,
            model_used="yolov8n",
            confidence_threshold=0.5,
            processing_time_seconds=15.0,
            status="completed",
        )
        db_session.add(ball_detection)
        db_session.commit()
        db_session.refresh(ball_detection)

        # Verify the ball detection was created
        assert ball_detection.id is not None
        assert ball_detection.video_id == video.id

        # Delete the video
        success, filename, deleted_video_id = delete_video_with_analyses(
            db_session, video.id
        )

        # Verify deletion was successful
        assert success is True
        assert deleted_video_id == video.id
        assert filename == "test_cascade_ball_video.mp4"

        # Verify the video is deleted
        deleted_video = db_session.query(Video).filter(Video.id == video.id).first()
        assert deleted_video is None

        # Verify the ball detection is also deleted (cascade should handle this)
        deleted_ball_detection = (
            db_session.query(BallDetection)
            .filter(BallDetection.id == ball_detection.id)
            .first()
        )
        assert deleted_ball_detection is None

    def test_video_deletion_with_multiple_related_records(
        self, db_session: Session
    ) -> None:
        """Test that deleting a video deletes all related records (pose, ball, etc.)."""
        # Create a test video
        video = Video(
            filename="test_cascade_comprehensive.mp4",
            file_path="/path/to/test_cascade_comprehensive.mp4",
            file_size=3000,
        )
        db_session.add(video)
        db_session.commit()
        db_session.refresh(video)

        # Create multiple related records
        pose_detection = PoseDetection(
            video_id=video.id,
            total_frames=150,
            frames_with_poses=75,
            total_pose_detections=75,
            detection_rate=0.5,
            confidence_threshold=0.5,
            detection_threshold=0.5,
            processing_time_seconds=12.0,
            status="completed",
        )

        ball_detection = BallDetection(
            video_id=video.id,
            total_frames=150,
            frames_with_balls=60,
            total_ball_detections=60,
            average_detections_per_frame=0.4,
            detection_rate=0.4,
            model_used="yolov8s",
            confidence_threshold=0.6,
            processing_time_seconds=18.0,
            status="completed",
        )

        db_session.add(pose_detection)
        db_session.add(ball_detection)
        db_session.commit()
        db_session.refresh(pose_detection)
        db_session.refresh(ball_detection)

        # Verify records were created
        assert pose_detection.id is not None
        assert ball_detection.id is not None

        # Delete the video
        success, filename, deleted_video_id = delete_video_with_analyses(
            db_session, video.id
        )

        # Verify deletion was successful
        assert success is True
        assert deleted_video_id == video.id

        # Verify all records are deleted
        deleted_video = db_session.query(Video).filter(Video.id == video.id).first()
        assert deleted_video is None

        deleted_pose_detection = (
            db_session.query(PoseDetection)
            .filter(PoseDetection.id == pose_detection.id)
            .first()
        )
        assert deleted_pose_detection is None

        deleted_ball_detection = (
            db_session.query(BallDetection)
            .filter(BallDetection.id == ball_detection.id)
            .first()
        )
        assert deleted_ball_detection is None
