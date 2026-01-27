"""
Pose detection service using MediaPipe for independent pose analysis.
"""

import json
import logging
import time
from pathlib import Path
from typing import Dict, Iterator, List, Optional, Sequence, Tuple

import cv2
import numpy as np
from sqlalchemy.orm import Session

from app.core.config import settings
from app.models.pose_detection import PoseDetection

logger = logging.getLogger(__name__)


class PoseDetectionService:
    """Service for detecting human poses in videos using MediaPipe."""

    def __init__(self) -> None:
        """Initialize the pose detection service."""
        self.pose_detector = None
        self.mp_pose = None
        self.logger = logger
        self._initialize_mediapipe()

    def _initialize_mediapipe(self) -> None:
        """Initialize MediaPipe pose detection models."""
        try:
            # MediaPipe 0.10.x uses tasks API instead of solutions
            # The model file needs to be downloaded or specified
            from mediapipe.tasks.python import BaseOptions
            from mediapipe.tasks.python.vision import (
                PoseLandmarker,
                PoseLandmarkerOptions,
                RunningMode,
            )

            # Download model file if not exists
            # MediaPipe 0.10.x requires explicit model file
            model_path = self._get_or_download_model()

            # Configure options for video processing
            base_options = BaseOptions(model_asset_path=model_path)
            options = PoseLandmarkerOptions(
                base_options=base_options,
                running_mode=RunningMode.VIDEO,  # For video processing
                min_pose_detection_confidence=settings.POSE_DETECTION_CONFIDENCE,
                min_pose_presence_confidence=settings.POSE_TRACKING_CONFIDENCE,
                min_tracking_confidence=settings.POSE_TRACKING_CONFIDENCE,
                num_poses=1,  # Detect single pose
                output_segmentation_masks=False,
            )

            self.pose_detector = PoseLandmarker.create_from_options(options)
            self.mp_pose = None  # Not used in 0.10.x API
            logger.info(
                "✅ MediaPipe pose detection initialized successfully (v0.10.x)"
            )

        except ImportError as e:
            logger.error(f"Failed to import MediaPipe: {e}")
            self.pose_detector = None
        except (RuntimeError, ValueError, OSError) as e:
            logger.error(f"Failed to initialize MediaPipe pose detection: {e}")
            self.pose_detector = None

    def _get_or_download_model(self) -> str:
        """Get or download the MediaPipe pose landmarker model file."""
        import urllib.request
        from pathlib import Path

        # Model URL from MediaPipe GitHub releases
        model_url = "https://storage.googleapis.com/mediapipe-models/pose_landmarker/pose_landmarker_heavy/float16/1/pose_landmarker_heavy.task"
        model_dir = Path(settings.ML_MODELS_DIR)
        model_dir.mkdir(parents=True, exist_ok=True)
        model_path = model_dir / "pose_landmarker.task"

        # Download if not exists
        if not model_path.exists():
            logger.info(f"Downloading MediaPipe pose landmarker model to {model_path}")
            try:
                urllib.request.urlretrieve(model_url, model_path)  # noqa: S310 - Downloading from trusted Google storage
                logger.info("✅ Model downloaded successfully")
            except (urllib.error.URLError, OSError) as e:
                logger.error(f"Failed to download model: {e}")
                # Try lighter model as fallback
                model_url = "https://storage.googleapis.com/mediapipe-models/pose_landmarker/pose_landmarker_lite/float16/1/pose_landmarker_lite.task"
                model_path = model_dir / "pose_landmarker_lite.task"
                if not model_path.exists():
                    urllib.request.urlretrieve(model_url, model_path)  # noqa: S310 - Downloading from trusted Google storage
                    logger.info("✅ Lite model downloaded as fallback")

        return str(model_path)

    def detect_pose_in_frame(
        self, frame: np.ndarray
    ) -> Optional[Dict[str, List[float]]]:
        """
        Detect human pose in a single frame using MediaPipe.

        Args:
            frame: Input frame as numpy array

        Returns:
            Dictionary of keypoint coordinates if pose detected, None otherwise
        """
        if not self.pose_detector:
            logger.warning("Pose detector not available")
            return None

        try:
            # Convert BGR to RGB (MediaPipe expects RGB)
            rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)

            # MediaPipe 0.10.x uses Image class and detect() method
            from mediapipe import Image, ImageFormat

            # Create MediaPipe Image from numpy array
            mp_image = Image(image_format=ImageFormat.SRGB, data=rgb_frame)

            # Process frame (detect() for video mode)
            # Note: For video mode, we need to provide timestamp_ms
            # Using current time in milliseconds
            import time

            timestamp_ms = int(time.time() * 1000)
            detection_result = self.pose_detector.detect_for_video(
                mp_image, timestamp_ms
            )

            # Access pose landmarks from result
            if (
                detection_result.pose_landmarks
                and len(detection_result.pose_landmarks) > 0
            ):
                # Get first pose (we configured num_poses=1)
                landmarks = detection_result.pose_landmarks[0]
                return self._extract_keypoints(landmarks, frame.shape)

            return None

        except (RuntimeError, ValueError, OSError) as e:
            logger.error(f"Error in pose detection: {e}")
            return None


    def analyze_video_file(
        self,
        video_path: Path,
        confidence_threshold: Optional[float] = None,
        detection_threshold: Optional[float] = None,
        max_frames: Optional[int] = None,
    ) -> Dict[str, any]:
        """
        Analyze a video file for pose detection with streaming frame processing.

        Memory-efficient: processes one frame at a time, never holds all frames.

        Args:
            video_path: Path to video file
            confidence_threshold: Minimum confidence for pose detection
            detection_threshold: Minimum detection threshold
            max_frames: Maximum number of frames to process

        Returns:
            Dictionary containing detailed pose detection results
        """
        start_time = time.time()
        logger.info(f"Starting pose detection analysis for: {video_path}")

        if not self.pose_detector:
            return {
                "error": "Pose detector not initialized",
                "processing_time_seconds": time.time() - start_time,
            }

        # Accumulators for results (lightweight: keypoints only, not raw frames)
        pose_detections = []
        confidence_scores = []
        frames_with_poses = 0
        total_frames = 0

        try:
            # Process frames one at a time via generator
            for frame_index, frame in self._iter_frames(video_path, max_frames):
                total_frames += 1

                # Detect pose in single frame
                pose_keypoints = self.detect_pose_in_frame(frame)

                if pose_keypoints is not None:
                    frames_with_poses += 1
                    confidence_scores.append(settings.POSE_OVERALL_CONFIDENCE)
                else:
                    confidence_scores.append(0.0)

                pose_detections.append(pose_keypoints)

                # Log progress every 100 frames
                if frame_index % 100 == 0:
                    logger.debug(
                        f"Frame {frame_index}: pose_detected={pose_keypoints is not None}"
                    )

                # Frame is now out of scope and can be garbage collected

            if total_frames == 0:
                return {
                    "error": "No frames could be extracted from video",
                    "processing_time_seconds": time.time() - start_time,
                }

            # Calculate metrics
            processing_time = time.time() - start_time
            non_zero_confidences = [c for c in confidence_scores if c > 0]

            results = {
                "pose_detections": pose_detections,
                "total_frames": total_frames,
                "frames_with_poses": frames_with_poses,
                "total_pose_detections": frames_with_poses,
                "detection_rate": frames_with_poses / total_frames if total_frames else 0.0,
                "processing_time_seconds": processing_time,
                "frame_processing_rate": total_frames / processing_time if processing_time > 0 else 0,
                "confidence_scores": confidence_scores,
                "average_confidence": (
                    sum(non_zero_confidences) / len(non_zero_confidences)
                    if non_zero_confidences else None
                ),
                "min_confidence": min(non_zero_confidences) if non_zero_confidences else None,
                "max_confidence": max(non_zero_confidences) if non_zero_confidences else None,
                "confidence_threshold": confidence_threshold or 0.5,
                "detection_threshold": detection_threshold or 0.5,
                "video_path": str(video_path),
            }

            logger.info(
                f"Pose detection complete: {frames_with_poses}/{total_frames} frames with poses "
                f"in {processing_time:.2f}s"
            )
            return results

        except (RuntimeError, ValueError, OSError) as e:
            logger.error(f"Error in pose detection: {e}")
            return {
                "error": str(e),
                "processing_time_seconds": time.time() - start_time,
            }

    def save_detection_results(
        self, db: Session, video_id: int, detection_results: Dict[str, any]
    ) -> PoseDetection:
        """
        Save pose detection results to database.

        Args:
            db: Database session
            video_id: ID of the video
            detection_results: Results from pose detection analysis

        Returns:
            Created PoseDetection record
        """
        # Serialize complex data structures
        pose_data = None
        confidence_scores_json = None
        visibility_scores_json = None

        if detection_results.get("pose_detections"):
            pose_data = json.dumps(detection_results["pose_detections"])

        if detection_results.get("confidence_scores"):
            confidence_scores_json = json.dumps(detection_results["confidence_scores"])

        # Create pose detection record
        pose_detection = PoseDetection(
            video_id=video_id,
            total_frames=detection_results.get("total_frames", 0),
            frames_with_poses=detection_results.get("frames_with_poses", 0),
            total_pose_detections=detection_results.get("total_pose_detections", 0),
            detection_rate=detection_results.get("detection_rate", 0.0),
            average_pose_confidence=detection_results.get("average_confidence"),
            min_pose_confidence=detection_results.get("min_confidence"),
            max_pose_confidence=detection_results.get("max_confidence"),
            confidence_threshold=detection_results.get("confidence_threshold", 0.5),
            detection_threshold=detection_results.get("detection_threshold", 0.5),
            pose_data=pose_data,
            confidence_scores=confidence_scores_json,
            visibility_scores=visibility_scores_json,
            processing_time_seconds=detection_results.get(
                "processing_time_seconds", 0.0
            ),
            frame_processing_rate=detection_results.get("frame_processing_rate"),
            status="completed" if not detection_results.get("error") else "failed",
            error_message=detection_results.get("error"),
        )

        db.add(pose_detection)
        db.commit()
        db.refresh(pose_detection)

        logger.info(f"Saved pose detection results for video {video_id}")
        return pose_detection

    def get_detection_by_video_id(
        self, db: Session, video_id: int
    ) -> Optional[PoseDetection]:
        """
        Retrieve pose detection results for a video.

        Args:
            db: Database session
            video_id: ID of the video

        Returns:
            PoseDetection record if exists, None otherwise
        """
        return (
            db.query(PoseDetection)
            .filter(PoseDetection.video_id == video_id)
            .order_by(PoseDetection.created_at.desc())
            .first()
        )

    def get_formatted_pose_data(
        self, pose_detection: PoseDetection
    ) -> Optional[List[Dict]]:
        """
        Deserialize and format pose data for API response.

        Args:
            pose_detection: PoseDetection database record

        Returns:
            List of formatted frame data, or None if no pose data exists
        """
        if not pose_detection.pose_data:
            return None

        try:
            # Deserialize the JSON data
            raw_pose_data = json.loads(pose_detection.pose_data)
            confidence_scores = (
                json.loads(pose_detection.confidence_scores)
                if pose_detection.confidence_scores
                else []
            )

            formatted_data = []

            for frame_index, frame_pose_data in enumerate(raw_pose_data):
                if frame_pose_data is None:
                    # No pose detected in this frame
                    formatted_data.append(
                        {
                            "frame_index": frame_index,
                            "keypoints": [],
                            "overall_confidence": 0.0,
                        }
                    )
                    continue

                # Convert MediaPipe keypoint format to our API format
                keypoints = []
                for keypoint_name, coordinates in frame_pose_data.items():
                    if isinstance(coordinates, list) and len(coordinates) >= 2:
                        keypoints.append(
                            {
                                "name": keypoint_name,
                                "x": coordinates[0],
                                "y": coordinates[1],
                                "confidence": coordinates[2]
                                if len(coordinates) > 2
                                else None,
                            }
                        )

                # Get overall confidence for this frame
                overall_confidence = (
                    confidence_scores[frame_index]
                    if frame_index < len(confidence_scores)
                    else None
                )

                formatted_data.append(
                    {
                        "frame_index": frame_index,
                        "keypoints": keypoints,
                        "overall_confidence": overall_confidence,
                    }
                )

            return formatted_data

        except (json.JSONDecodeError, KeyError, TypeError) as e:
            logger.error(f"Failed to deserialize pose data: {e}")
            return None

    def _iter_frames(
        self, video_path: Path, max_frames: Optional[int] = None
    ) -> Iterator[Tuple[int, np.ndarray]]:
        """
        Yield frames one at a time instead of loading all into memory.

        Args:
            video_path: Path to video file
            max_frames: Maximum number of frames to extract

        Yields:
            Tuple of (frame_index, frame_array)
        """
        try:
            cap = cv2.VideoCapture(str(video_path))
            if not cap.isOpened():
                logger.error(f"Could not open video: {video_path}")
                return

            frame_index = 0
            while True:
                ret, frame = cap.read()
                if not ret:
                    break

                yield frame_index, frame
                frame_index += 1

                if max_frames and frame_index >= max_frames:
                    logger.info(f"Reached max_frames limit: {max_frames}")
                    break

            logger.info(f"Yielded {frame_index} frames from {video_path}")

        except (OSError, RuntimeError, ValueError) as e:
            logger.error(f"Error extracting frames from {video_path}: {e}")
        finally:
            if 'cap' in locals():
                cap.release()

    def _extract_keypoints(
        self, landmarks: Sequence, frame_shape: Tuple[int, int, int]
    ) -> Dict[str, List[float]]:
        """
        Extract relevant keypoints for tennis analysis.

        Args:
            landmarks: MediaPipe pose landmarks
            frame_shape: Shape of the frame (height, width, channels)

        Returns:
            Dictionary of keypoint coordinates
        """
        height, width = frame_shape[:2]

        # Extract keypoints relevant for tennis analysis (back view focus)
        # Note: Nose removed as it's not visible from behind
        # Focus on upper body and legs for tennis stroke analysis
        # MediaPipe 0.10.x uses same landmark indices but different structure
        keypoints = {
            # Upper body - essential for stroke analysis
            "left_shoulder": [landmarks[11].x * width, landmarks[11].y * height],
            "right_shoulder": [landmarks[12].x * width, landmarks[12].y * height],
            "left_elbow": [landmarks[13].x * width, landmarks[13].y * height],
            "right_elbow": [landmarks[14].x * width, landmarks[14].y * height],
            "left_wrist": [landmarks[15].x * width, landmarks[15].y * height],
            "right_wrist": [landmarks[16].x * width, landmarks[16].y * height],
            # Core/hip area - important for stance and balance
            "left_hip": [landmarks[23].x * width, landmarks[23].y * height],
            "right_hip": [landmarks[24].x * width, landmarks[24].y * height],
            # Lower body - crucial for footwork and court positioning
            "left_knee": [landmarks[25].x * width, landmarks[25].y * height],
            "right_knee": [landmarks[26].x * width, landmarks[26].y * height],
            "left_ankle": [landmarks[27].x * width, landmarks[27].y * height],
            "right_ankle": [landmarks[28].x * width, landmarks[28].y * height],
        }

        return keypoints
