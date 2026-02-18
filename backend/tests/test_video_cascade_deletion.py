"""
Test video cascade deletion to ensure all related records are properly deleted.
"""

from sqlalchemy.orm import Session

from app.models.player import Player
from app.models.pose_detection import PoseDetection
from app.models.serve_biomechanics_report import ServeBiomechanicsReport
from app.models.serve_window import ServeWindow
from app.models.video import Video
from app.services import video_service


class TestVideoCascadeDeletion:
    """Test that video deletion properly cascades to all related records."""

    def test_video_deletion_cascades_to_pose_detection(
        self, db_session: Session, test_user_id: str
    ) -> None:
        """Test that deleting a video also deletes associated pose detection records."""
        # Create a test video
        video = Video(
            filename="test_cascade_video.mp4",
            file_path="/path/to/test_cascade_video.mp4",
            file_size=1000,
            user_id=test_user_id,
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
        success, filename, deleted_video_id = video_service.delete_video_with_analyses(
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

    def test_video_deletion_with_multiple_related_records(
        self, db_session: Session, test_user_id: str
    ) -> None:
        """Test that deleting a video deletes all related records (pose, etc.)."""
        # Create a test video
        video = Video(
            filename="test_cascade_comprehensive.mp4",
            file_path="/path/to/test_cascade_comprehensive.mp4",
            file_size=3000,
            user_id=test_user_id,
        )
        db_session.add(video)
        db_session.commit()
        db_session.refresh(video)

        # Create pose detection record
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

        db_session.add(pose_detection)
        db_session.commit()
        db_session.refresh(pose_detection)

        # Verify record was created
        assert pose_detection.id is not None

        # Delete the video
        success, _, deleted_video_id = video_service.delete_video_with_analyses(
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

    def test_video_deletion_cascades_to_biomechanics_reports(
        self, db_session: Session, test_user_id: str
    ) -> None:
        """Deleting a video should also delete serve biomechanics reports."""
        player = Player(
            name="Cascade Player",
            dominant_hand="right",
            user_id=test_user_id,
        )
        db_session.add(player)
        db_session.commit()
        db_session.refresh(player)

        video = Video(
            filename="test_biomechanics_cascade.mp4",
            file_path="/path/to/test_biomechanics_cascade.mp4",
            file_size=2000,
            user_id=test_user_id,
        )
        db_session.add(video)
        db_session.commit()
        db_session.refresh(video)

        serve_window = ServeWindow(
            video_id=video.id,
            user_id=test_user_id,
            player_id=player.id,
            start_timestamp=1.0,
            end_timestamp=2.0,
            contact_timestamp=1.5,
            status="accepted",
            source="manual",
        )
        db_session.add(serve_window)
        db_session.commit()
        db_session.refresh(serve_window)

        report = ServeBiomechanicsReport(
            serve_window_id=serve_window.id,
            user_id=test_user_id,
            player_id=player.id,
            phase_segmentation_json='{"phases":[]}',
            metrics_json="{}",
            analysis_version="phase-metrics-v1",
        )
        db_session.add(report)
        db_session.commit()
        db_session.refresh(report)
        report_id = report.id

        success, _, deleted_video_id = video_service.delete_video_with_analyses(
            db_session, video.id
        )

        assert success is True
        assert deleted_video_id == video.id
        assert db_session.query(Video).filter(Video.id == video.id).first() is None
        assert (
            db_session.query(ServeWindow)
            .filter(ServeWindow.id == serve_window.id)
            .first()
            is None
        )
        assert (
            db_session.query(ServeBiomechanicsReport)
            .filter(ServeBiomechanicsReport.id == report_id)
            .first()
            is None
        )
