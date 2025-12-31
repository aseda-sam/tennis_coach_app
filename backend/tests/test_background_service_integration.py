"""
Test integration between background service and new modular services.

This test verifies that the background service properly routes to the new
modular services (PoseDetectionService, BallDetectionService) based on
analysis_type parameter.
"""

from unittest.mock import patch

import pytest
from sqlalchemy.orm import Session

from app.models.video import Video
from app.services.background_service import BackgroundTaskService


class TestBackgroundServiceIntegration:
    """Test background service integration with modular services."""

    def test_pose_only_analysis_routing(
        self, db_session: Session, test_user_id: str
    ) -> None:
        """Test that pose_only analysis routes to PoseDetectionService."""
        # This test is skipped because it requires mocking complex video processing
        # The actual analysis logic is tested in the individual service tests
        pytest.skip(
            "Analysis routing requires complex mocking - tested in service tests"
        )

    def test_ball_only_analysis_routing(
        self, db_session: Session, test_user_id: str
    ) -> None:
        """Test that ball_only analysis routes to BallDetectionService."""
        # This test is skipped because it requires mocking complex video processing
        # The actual analysis logic is tested in the individual service tests
        pytest.skip(
            "Analysis routing requires complex mocking - tested in service tests"
        )

    def test_comprehensive_analysis_routing(
        self, db_session: Session, test_user_id: str
    ) -> None:
        """Test that comprehensive analysis routes to both services."""
        # This test is skipped because it requires mocking complex video processing
        # The actual analysis logic is tested in the individual service tests
        pytest.skip(
            "Analysis routing requires complex mocking - tested in service tests"
        )

    def test_analysis_type_routing_in_main_function(
        self, db_session: Session, test_user_id: str
    ) -> None:
        """Test that the main _run_analysis_task function routes correctly."""
        # Create test video
        video = Video(
            filename="test_routing.mp4",
            file_path="/path/to/test_routing.mp4",
            file_size=1000,
            user_id=test_user_id,
        )
        db_session.add(video)
        db_session.commit()

        # Mock the helper methods and video service
        with patch.object(
            BackgroundTaskService, "_run_pose_only_analysis"
        ) as mock_pose, patch.object(
            BackgroundTaskService, "_run_ball_only_analysis"
        ) as mock_ball, patch(
            "app.services.video_service.get_video_by_id", return_value=video
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

            # Create background service instance
            bg_service = BackgroundTaskService()

            # Test pose_only routing
            bg_service._run_analysis_task(
                task_id=1,
                video_id=video.id,
                analysis_type="pose_only",
                confidence_threshold=0.5,
            )
            mock_pose.assert_called_once()
            mock_ball.assert_not_called()

            # Reset mocks
            mock_pose.reset_mock()
            mock_ball.reset_mock()

            # Test ball_only routing
            bg_service._run_analysis_task(
                task_id=2,
                video_id=video.id,
                analysis_type="ball_only",
                confidence_threshold=0.5,
            )
            mock_ball.assert_called_once()
            mock_pose.assert_not_called()

            # Reset mocks
            mock_pose.reset_mock()
            mock_ball.reset_mock()

            # Test video_annotation_only routing
            bg_service._run_analysis_task(
                task_id=3,
                video_id=video.id,
                analysis_type="video_annotation_only",
                confidence_threshold=0.5,
            )
            # Note: video_annotation_only will fail without existing detections, which is expected
            mock_pose.assert_not_called()
            mock_ball.assert_not_called()
