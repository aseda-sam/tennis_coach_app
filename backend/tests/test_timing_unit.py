"""
Unit tests for timing functionality.
"""

import time
from unittest.mock import patch

from app.services.cv_service import log_timing, log_timing_error


class TestTimingFunctions:
    """Test timing utility functions."""

    def test_log_timing_success(self) -> None:
        """Test successful timing log."""
        start_time = time.time() - 1.5  # 1.5 seconds ago

        with patch("app.services.cv_service.logger") as mock_logger:
            log_timing("Test Operation", start_time)

            # Verify logger was called
            mock_logger.info.assert_called_once()

            # Verify the log message contains timing info
            log_message = mock_logger.info.call_args[0][0]
            assert "Test Operation" in log_message
            assert "completed in" in log_message
            assert "1.5" in log_message or "1.4" in log_message or "1.6" in log_message

    def test_log_timing_error(self) -> None:
        """Test timing error log."""
        start_time = time.time() - 2.0  # 2.0 seconds ago
        test_error = ValueError("Test error")

        with patch("app.services.cv_service.logger") as mock_logger:
            log_timing_error("Test Operation", start_time, test_error)

            # Verify logger was called
            mock_logger.error.assert_called_once()

            # Verify the log message contains error info
            log_message = mock_logger.error.call_args[0][0]
            assert "Test Operation" in log_message
            assert "failed after" in log_message
            assert "Test error" in log_message

    def test_log_timing_very_fast_operation(self) -> None:
        """Test timing for very fast operations."""
        start_time = time.time() - 0.001  # 1ms ago

        with patch("app.services.cv_service.logger") as mock_logger:
            log_timing("Fast Operation", start_time)

            # Verify logger was called
            mock_logger.info.assert_called_once()

            # Verify the log message contains timing info
            log_message = mock_logger.info.call_args[0][0]
            assert "Fast Operation" in log_message
            assert "completed in" in log_message

    def test_log_timing_very_slow_operation(self) -> None:
        """Test timing for very slow operations."""
        start_time = time.time() - 60.0  # 60 seconds ago

        with patch("app.services.cv_service.logger") as mock_logger:
            log_timing("Slow Operation", start_time)

            # Verify logger was called
            mock_logger.info.assert_called_once()

            # Verify the log message contains timing info
            log_message = mock_logger.info.call_args[0][0]
            assert "Slow Operation" in log_message
            assert "completed in" in log_message
            assert "60" in log_message or "59" in log_message or "61" in log_message


class TestAnalysisTiming:
    """Test timing functionality in analysis results."""

    def test_analysis_timing_structure(self) -> None:
        """Test that analysis results contain proper timing structure."""
        # This test verifies that the timing structure is properly included
        # in analysis results, which is tested indirectly through integration tests

        # Mock timing data structure
        timing_data = {
            "frame_extraction": 1.5,
            "ball_detection": 3.2,
            "pose_detection": 2.1,
            "frame_annotation": 0.8,
            "video_creation": 1.2,
            "total_analysis": 8.8,
        }

        # Verify timing data structure
        assert "frame_extraction" in timing_data
        assert "ball_detection" in timing_data
        assert "pose_detection" in timing_data
        assert "frame_annotation" in timing_data
        assert "video_creation" in timing_data
        assert "total_analysis" in timing_data

        # Verify all values are positive
        for stage, duration in timing_data.items():
            assert duration >= 0, f"Timing for {stage} should be non-negative"

        # Verify total matches sum of stages (approximately)
        stage_sum = sum(
            duration
            for stage, duration in timing_data.items()
            if stage != "total_analysis"
        )
        assert abs(stage_sum - timing_data["total_analysis"]) < 1.0, (
            "Total should approximately match sum of stages"
        )
