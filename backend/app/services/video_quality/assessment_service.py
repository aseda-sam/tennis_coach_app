"""
Video quality assessment service.

This service provides comprehensive video quality assessment functionality,
optimized for different use cases (quick upload assessment vs detailed analysis).
"""

import logging
import time
from pathlib import Path
from typing import Any, Dict, List

import cv2
import numpy as np

from app.core.config import settings

logger = logging.getLogger(__name__)


class VideoQualityService:
    """Service for assessing video quality metrics."""

    def __init__(self) -> None:
        """Initialize the video quality service."""
        self.logger = logger

    def quick_assess(
        self, video_path: Path, max_sample_frames: int = 10
    ) -> Dict[str, Any]:
        """
        Perform quick quality assessment on video using limited sample frames.

        Optimized for speed during upload process - uses fewer frames than full analysis.

        Args:
            video_path: Path to video file
            max_sample_frames: Maximum number of frames to sample for assessment

        Returns:
            Dictionary containing quality metrics and recommended thresholds
        """
        start_time = time.time()

        try:
            # Extract sample frames for quick assessment
            frames = self._extract_sample_frames(video_path, max_sample_frames)

            if not frames:
                self.logger.warning(f"No frames extracted from {video_path}")
                return self._get_default_quality_metrics()

            # Perform quality assessment
            quality_metrics = self._assess_frames_quality(frames)

            assessment_time = time.time() - start_time
            self.logger.info(
                f"Quick quality assessment completed in {assessment_time:.2f}s"
            )

            return quality_metrics

        except (OSError, RuntimeError, ValueError) as e:
            self.logger.error(f"Error in quick quality assessment: {e}")
            return self._get_default_quality_metrics()

    def detailed_assess(self, frames: List[np.ndarray]) -> Dict[str, Any]:
        """
        Perform detailed quality assessment on provided frames.

        Used for comprehensive analysis where frames are already extracted.

        Args:
            frames: List of video frames to analyze

        Returns:
            Dictionary containing detailed quality metrics
        """
        if not frames:
            self.logger.warning("No frames provided for detailed assessment")
            return self._get_default_quality_metrics()

        start_time = time.time()

        try:
            # Sample frames if we have too many (for performance)
            max_frames_for_analysis = 50
            if len(frames) > max_frames_for_analysis:
                # Sample frames evenly across the video
                step = len(frames) // max_frames_for_analysis
                sample_frames = frames[::step][:max_frames_for_analysis]
                self.logger.info(
                    f"Sampled {len(sample_frames)} frames from {len(frames)} total"
                )
            else:
                sample_frames = frames

            quality_metrics = self._assess_frames_quality(sample_frames)

            assessment_time = time.time() - start_time
            self.logger.info(
                f"Detailed quality assessment completed in {assessment_time:.2f}s"
            )

            return quality_metrics

        except (OSError, RuntimeError, ValueError) as e:
            self.logger.error(f"Error in detailed quality assessment: {e}")
            return self._get_default_quality_metrics()

    def _extract_sample_frames(
        self, video_path: Path, max_frames: int
    ) -> List[np.ndarray]:
        """
        Extract sample frames from video for quality assessment.

        Args:
            video_path: Path to video file
            max_frames: Maximum number of frames to extract

        Returns:
            List of frame arrays
        """
        frames = []

        try:
            cap = cv2.VideoCapture(str(video_path))
            if not cap.isOpened():
                self.logger.error(f"Could not open video: {video_path}")
                return frames

            total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
            if total_frames == 0:
                self.logger.error(f"Video has no frames: {video_path}")
                cap.release()
                return frames

            # Calculate frame interval to get good distribution
            interval = max(1, total_frames // max_frames)

            frame_count = 0
            extracted_count = 0

            while extracted_count < max_frames and frame_count < total_frames:
                ret, frame = cap.read()
                if not ret:
                    break

                # Extract frame at interval
                if frame_count % interval == 0:
                    frames.append(frame)
                    extracted_count += 1

                frame_count += interval

                # Skip frames to maintain interval
                if interval > 1:
                    for _ in range(interval - 1):
                        cap.read()

            cap.release()
            self.logger.info(
                f"Extracted {len(frames)} sample frames from {total_frames} total frames"
            )

        except (OSError, RuntimeError, ValueError) as e:
            self.logger.error(f"Error extracting sample frames: {e}")

        return frames

    def _assess_frames_quality(self, frames: List[np.ndarray]) -> Dict[str, Any]:
        """
        Assess quality of video frames.

        Args:
            frames: List of video frames to analyze

        Returns:
            Dictionary containing quality metrics and recommended thresholds
        """
        if not frames:
            return self._get_default_quality_metrics()

        # Calculate blur score using Laplacian variance
        blur_scores = []
        for frame in frames:
            gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
            blur_score = cv2.Laplacian(gray, cv2.CV_64F).var()
            blur_scores.append(blur_score)

        avg_blur_score = np.mean(blur_scores)
        # Normalize blur score (higher variance = less blur)
        blur_quality = min(
            1.0, avg_blur_score / 500.0
        )  # Threshold based on typical tennis video blur

        # Calculate lighting score using brightness and contrast
        lighting_scores = []
        for frame in frames:
            # Convert to LAB color space for better lighting analysis
            lab = cv2.cvtColor(frame, cv2.COLOR_BGR2LAB)
            l_channel = lab[:, :, 0]

            # Calculate brightness (mean of L channel)
            brightness = np.mean(l_channel)
            # Calculate contrast (standard deviation of L channel)
            contrast = np.std(l_channel)

            # Normalize brightness (good range: 50-200)
            brightness_score = 1.0 - abs(brightness - 125) / 125
            brightness_score = max(0.0, min(1.0, brightness_score))

            # Normalize contrast (good range: >20)
            contrast_score = min(1.0, contrast / 50.0)

            # Combined lighting score
            lighting_score = (brightness_score + contrast_score) / 2
            lighting_scores.append(lighting_score)

        lighting_quality = np.mean(lighting_scores)

        # Calculate resolution score
        first_frame = frames[0]
        height, width = first_frame.shape[:2]

        # Normalize resolution score (4K = 1.0, 720p = 0.5, 480p = 0.25)
        resolution_score = min(1.0, (width * height) / (1920 * 1080))

        # Calculate overall quality score
        quality_score = (
            blur_quality * 0.4 + lighting_quality * 0.4 + resolution_score * 0.2
        )

        # Determine quality level
        if quality_score >= 0.8:
            quality_level = "excellent"
            recommended_threshold = settings.BALL_CONFIDENCE_THRESHOLD
        elif quality_score >= 0.6:
            quality_level = "good"
            recommended_threshold = settings.BALL_CONFIDENCE_THRESHOLD * 0.9
        elif quality_score >= 0.4:
            quality_level = "fair"
            recommended_threshold = settings.BALL_CONFIDENCE_THRESHOLD * 0.8
        else:
            quality_level = "poor"
            recommended_threshold = settings.BALL_CONFIDENCE_THRESHOLD * 0.7

        self.logger.info(
            f"Video quality assessment: {quality_level} (score: {quality_score:.2f})"
        )
        self.logger.info(
            f"  Blur: {blur_quality:.2f}, Lighting: {lighting_quality:.2f}, Resolution: {resolution_score:.2f}"
        )
        self.logger.info(
            f"  Recommended confidence threshold: {recommended_threshold:.2f}"
        )

        return {
            "quality_score": float(quality_score),
            "blur_score": float(blur_quality),
            "lighting_score": float(lighting_quality),
            "resolution_score": float(resolution_score),
            "recommended_confidence_threshold": float(recommended_threshold),
            "quality_level": quality_level,
            "frame_count_analyzed": len(frames),
        }

    def _get_default_quality_metrics(self) -> Dict[str, Any]:
        """
        Return default quality metrics when assessment fails.

        Returns:
            Dictionary with default quality metrics
        """
        return {
            "quality_score": 0.0,
            "blur_score": 0.0,
            "lighting_score": 0.0,
            "resolution_score": 0.0,
            "recommended_confidence_threshold": settings.BALL_CONFIDENCE_THRESHOLD,
            "quality_level": "unknown",
            "frame_count_analyzed": 0,
        }
