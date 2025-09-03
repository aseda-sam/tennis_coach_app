"""
Test integration between background service and new modular services.

This test verifies that the background service properly routes to the new
modular services (PoseDetectionService, BallDetectionService) based on
analysis_type parameter.
"""

from unittest.mock import Mock, patch

from sqlalchemy.orm import Session

from app.models.video import Video
from app.services.background_service import BackgroundTaskService


class TestBackgroundServiceIntegration:
    """Test background service integration with modular services."""

    def test_pose_only_analysis_routing(self, db_session: Session) -> None:
        """Test that pose_only analysis routes to PoseDetectionService."""
        # Create test video
        video = Video(
            filename="test_pose_only.mp4",
            file_path="/path/to/test_pose_only.mp4",
            file_size=1000,
        )
        db_session.add(video)
        db_session.commit()

        # Mock the modular services
        with patch(
            "app.services.background_service.PoseDetectionService"
        ) as mock_pose_service, patch(
            "app.services.background_service.create_analysis_record"
        ), patch("app.services.background_service.update_analysis_status"), patch(
            "app.services.background_service.update_task_progress"
        ), patch("pathlib.Path.exists", return_value=True):
            # Setup mock return values
            mock_pose_instance = Mock()
            mock_pose_service.return_value = mock_pose_instance
            mock_pose_instance.analyze_video_file.return_value = {
                "total_frames": 50,
                "frames_with_poses": 30,
                "total_pose_detections": 30,
                "detection_rate": 0.6,
                "processing_time_seconds": 10.0,
            }
            mock_pose_instance.save_detection_results.return_value = Mock(id=1)

            # Create background service instance
            bg_service = BackgroundTaskService()

            # Run pose-only analysis
            result = bg_service._run_pose_only_analysis(
                db=db_session,
                video_id=video.id,
                video_path="/path/to/test_pose_only.mp4",
                confidence_threshold=0.5,
                task_id=1,
            )

            # Verify PoseDetectionService was called
            mock_pose_service.assert_called_once()
            mock_pose_instance.analyze_video_file.assert_called_once()
            mock_pose_instance.save_detection_results.assert_called_once()

            # Verify result structure
            assert "pose_detection_id" in result
            assert result["analysis_type"] == "pose_only"

    def test_ball_only_analysis_routing(self, db_session: Session) -> None:
        """Test that ball_only analysis routes to BallDetectionService."""
        # Create test video
        video = Video(
            filename="test_ball_only.mp4",
            file_path="/path/to/test_ball_only.mp4",
            file_size=1000,
        )
        db_session.add(video)
        db_session.commit()

        # Mock the modular services
        with patch(
            "app.services.background_service.BallDetectionService"
        ) as mock_ball_service, patch(
            "app.services.background_service.create_analysis_record"
        ), patch("app.services.background_service.update_analysis_status"), patch(
            "app.services.background_service.update_task_progress"
        ), patch("pathlib.Path.exists", return_value=True):
            # Setup mock return values
            mock_ball_instance = Mock()
            mock_ball_service.return_value = mock_ball_instance
            mock_ball_instance.analyze_video_file.return_value = {
                "total_frames": 50,
                "frames_with_balls": 25,
                "total_ball_detections": 25,
                "detection_rate": 0.5,
                "processing_time_seconds": 8.0,
            }
            mock_ball_instance.save_detection_results.return_value = Mock(id=1)

            # Create background service instance
            bg_service = BackgroundTaskService()

            # Run ball-only analysis
            result = bg_service._run_ball_only_analysis(
                db=db_session,
                video_id=video.id,
                video_path="/path/to/test_ball_only.mp4",
                confidence_threshold=0.5,
                task_id=1,
            )

            # Verify BallDetectionService was called
            mock_ball_service.assert_called_once()
            mock_ball_instance.analyze_video_file.assert_called_once()
            mock_ball_instance.save_detection_results.assert_called_once()

            # Verify result structure
            assert "ball_detection_id" in result
            assert result["analysis_type"] == "ball_only"

    def test_comprehensive_analysis_routing(self, db_session: Session) -> None:
        """Test that comprehensive analysis routes to both services."""
        # Create test video
        video = Video(
            filename="test_comprehensive.mp4",
            file_path="/path/to/test_comprehensive.mp4",
            file_size=1000,
        )
        db_session.add(video)
        db_session.commit()

        # Mock the modular services
        with patch(
            "app.services.background_service.PoseDetectionService"
        ) as mock_pose_service, patch(
            "app.services.background_service.BallDetectionService"
        ) as mock_ball_service, patch(
            "app.services.background_service.create_analysis_record"
        ), patch("app.services.background_service.update_analysis_status"), patch(
            "app.services.background_service.update_task_progress"
        ), patch("pathlib.Path.exists", return_value=True):
            # Setup mock return values
            mock_pose_instance = Mock()
            mock_ball_instance = Mock()
            mock_pose_service.return_value = mock_pose_instance
            mock_ball_service.return_value = mock_ball_instance

            mock_pose_instance.analyze_video_file.return_value = {
                "total_frames": 50,
                "frames_with_poses": 30,
                "total_pose_detections": 30,
                "detection_rate": 0.6,
                "processing_time_seconds": 10.0,
            }
            mock_ball_instance.analyze_video_file.return_value = {
                "total_frames": 50,
                "frames_with_balls": 25,
                "total_ball_detections": 25,
                "detection_rate": 0.5,
                "processing_time_seconds": 8.0,
            }

            mock_pose_instance.save_detection_results.return_value = Mock(id=1)
            mock_ball_instance.save_detection_results.return_value = Mock(id=2)

            # Create background service instance
            bg_service = BackgroundTaskService()

            # Run comprehensive analysis
            result = bg_service._run_comprehensive_analysis(
                db=db_session,
                video_id=video.id,
                video_path="/path/to/test_comprehensive.mp4",
                confidence_threshold=0.5,
                include_pose_detection=True,
                task_id=1,
            )

            # Verify both services were called
            mock_pose_service.assert_called_once()
            mock_ball_service.assert_called_once()
            mock_pose_instance.analyze_video_file.assert_called_once()
            mock_ball_instance.analyze_video_file.assert_called_once()

            # Verify result structure
            assert "pose_detection_id" in result
            assert "ball_detection_id" in result
            assert result["analysis_type"] == "comprehensive"

    def test_analysis_type_routing_in_main_function(self, db_session: Session) -> None:
        """Test that the main _run_analysis_task function routes correctly."""
        # Create test video
        video = Video(
            filename="test_routing.mp4",
            file_path="/path/to/test_routing.mp4",
            file_size=1000,
        )
        db_session.add(video)
        db_session.commit()

        # Mock the helper methods and video service
        with patch.object(
            BackgroundTaskService, "_run_pose_only_analysis"
        ) as mock_pose, patch.object(
            BackgroundTaskService, "_run_ball_only_analysis"
        ) as mock_ball, patch.object(
            BackgroundTaskService, "_run_comprehensive_analysis"
        ) as mock_comp, patch(
            "app.services.background_service.get_video_by_id", return_value=video
        ), patch("pathlib.Path.exists", return_value=True):
            # Setup mock return values
            mock_pose.return_value = {
                "pose_detection_id": 1,
                "analysis_type": "pose_only",
            }
            mock_ball.return_value = {
                "ball_detection_id": 1,
                "analysis_type": "ball_only",
            }
            mock_comp.return_value = {
                "pose_detection_id": 1,
                "ball_detection_id": 2,
                "analysis_type": "comprehensive",
            }

            # Create background service instance
            bg_service = BackgroundTaskService()

            # Test pose_only routing
            bg_service._run_analysis_task(
                task_id=1,
                video_id=video.id,
                analysis_type="pose_only",
                confidence_threshold=0.5,
                include_pose_detection=True,
            )
            mock_pose.assert_called_once()
            mock_ball.assert_not_called()
            mock_comp.assert_not_called()

            # Reset mocks
            mock_pose.reset_mock()
            mock_ball.reset_mock()
            mock_comp.reset_mock()

            # Test ball_only routing
            bg_service._run_analysis_task(
                task_id=2,
                video_id=video.id,
                analysis_type="ball_only",
                confidence_threshold=0.5,
                include_pose_detection=False,
            )
            mock_ball.assert_called_once()
            mock_pose.assert_not_called()
            mock_comp.assert_not_called()

            # Reset mocks
            mock_pose.reset_mock()
            mock_ball.reset_mock()
            mock_comp.reset_mock()

            # Test comprehensive routing
            bg_service._run_analysis_task(
                task_id=3,
                video_id=video.id,
                analysis_type="comprehensive",
                confidence_threshold=0.5,
                include_pose_detection=True,
            )
            mock_comp.assert_called_once()
            mock_pose.assert_not_called()
            mock_ball.assert_not_called()
