"""
Pose detection service using MediaPipe for independent pose analysis.
"""

import json
import logging
import time
from pathlib import Path
from typing import Dict, List, Optional, Sequence, Tuple

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
            import mediapipe as mp

            self.mp_pose = mp.solutions.pose
            self.pose_detector = self.mp_pose.Pose(
                static_image_mode=False,
                model_complexity=1,  # 0, 1, or 2 (1 is good balance)
                smooth_landmarks=True,
                enable_segmentation=False,
                min_detection_confidence=settings.POSE_DETECTION_CONFIDENCE,
                min_tracking_confidence=settings.POSE_TRACKING_CONFIDENCE,
            )
            logger.info("✅ MediaPipe pose detection initialized successfully")

        except ImportError as e:
            logger.error(f"Failed to import MediaPipe: {e}")
            self.pose_detector = None
        except (RuntimeError, ValueError, OSError) as e:
            logger.error(f"Failed to initialize MediaPipe pose detection: {e}")
            self.pose_detector = None

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

            # Process frame
            results = self.pose_detector.process(rgb_frame)

            if results.pose_landmarks:
                landmarks = results.pose_landmarks.landmark
                return self._extract_keypoints(landmarks, frame.shape)

            return None

        except (RuntimeError, ValueError, OSError) as e:
            logger.error(f"Error in pose detection: {e}")
            return None

    def detect_poses_in_frames(
        self,
        frames: List[np.ndarray],
        confidence_threshold: Optional[float] = None,
        detection_threshold: Optional[float] = None,
    ) -> Dict[str, any]:
        """
        Detect poses in a batch of frames with detailed metrics.

        Args:
            frames: List of frame arrays
            confidence_threshold: Minimum confidence for pose detection
            detection_threshold: Minimum detection threshold

        Returns:
            Dictionary containing pose detection results and metrics
        """
        start_time = time.time()

        if not self.pose_detector:
            logger.warning("Pose detector not available")
            return {
                "pose_detections": [None] * len(frames),
                "frames_with_poses": 0,
                "total_pose_detections": 0,
                "detection_rate": 0.0,
                "processing_time_seconds": 0.0,
                "frame_processing_rate": 0.0,
                "confidence_scores": [],
                "error": "Pose detector not initialized",
            }

        pose_detections = []
        confidence_scores = []
        frame_timings = []
        frames_with_poses = 0

        try:
            for i, frame in enumerate(frames):
                frame_start = time.time()
                pose_keypoints = self.detect_pose_in_frame(frame)

                if pose_keypoints is not None:
                    frames_with_poses += 1
                    # Use configurable overall confidence score
                    confidence_scores.append(settings.POSE_OVERALL_CONFIDENCE)
                else:
                    confidence_scores.append(0.0)

                pose_detections.append(pose_keypoints)

                frame_time = time.time() - frame_start
                frame_timings.append(frame_time)

                # Log every 10th frame for performance monitoring
                if i % 10 == 0:
                    frame_shape = frame.shape
                    logger.debug(
                        f"Frame {i}: shape={frame_shape}, pose_detected={pose_keypoints is not None}, time={frame_time:.3f}s"
                    )

            total_poses = frames_with_poses
            processing_time = time.time() - start_time
            avg_frame_time = (
                sum(frame_timings) / len(frame_timings) if frame_timings else 0
            )
            frame_processing_rate = (
                len(frames) / processing_time if processing_time > 0 else 0
            )

            # Calculate pose quality metrics
            non_zero_confidences = [c for c in confidence_scores if c > 0]
            avg_confidence = (
                sum(non_zero_confidences) / len(non_zero_confidences)
                if non_zero_confidences
                else None
            )
            min_confidence = min(non_zero_confidences) if non_zero_confidences else None
            max_confidence = max(non_zero_confidences) if non_zero_confidences else None

            logger.info(
                f"Pose detection complete: {total_poses} poses detected out of {len(frames)} frames"
            )
            logger.info(
                f"⏱️ Average frame time: {avg_frame_time:.3f}s, Total time: {processing_time:.3f}s"
            )

            results = {
                "pose_detections": pose_detections,
                "frames_with_poses": frames_with_poses,
                "total_pose_detections": total_poses,
                "detection_rate": frames_with_poses / len(frames) if frames else 0.0,
                "processing_time_seconds": processing_time,
                "frame_processing_rate": frame_processing_rate,
                "confidence_scores": confidence_scores,
                "average_confidence": avg_confidence,
                "min_confidence": min_confidence,
                "max_confidence": max_confidence,
                "confidence_threshold": confidence_threshold or 0.5,
                "detection_threshold": detection_threshold or 0.5,
            }

        except (RuntimeError, ValueError, OSError) as e:
            logger.error(f"Error in batch pose detection: {e}")
            results = {
                "pose_detections": [None] * len(frames),
                "frames_with_poses": 0,
                "total_pose_detections": 0,
                "detection_rate": 0.0,
                "processing_time_seconds": time.time() - start_time,
                "frame_processing_rate": 0.0,
                "confidence_scores": [0.0] * len(frames),
                "error": str(e),
            }

        logger.info(f"Pose detection completed in {time.time() - start_time:.3f}s")
        return results

    def analyze_video_file(
        self,
        video_path: Path,
        confidence_threshold: Optional[float] = None,
        detection_threshold: Optional[float] = None,
        max_frames: Optional[int] = None,
    ) -> Dict[str, any]:
        """
        Analyze a video file for pose detection.

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

        # Extract frames
        frames = self._extract_frames(video_path, max_frames)
        if not frames:
            return {
                "error": "No frames could be extracted from video",
                "processing_time_seconds": time.time() - start_time,
            }

        # Perform pose detection
        detection_results = self.detect_poses_in_frames(
            frames, confidence_threshold, detection_threshold
        )

        # Add video metadata
        detection_results.update(
            {
                "total_frames": len(frames),
                "video_path": str(video_path),
                "processing_time_seconds": time.time() - start_time,
            }
        )

        logger.info(f"Pose detection analysis complete for {video_path}")
        return detection_results

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

    def _extract_frames(
        self, video_path: Path, max_frames: Optional[int] = None
    ) -> List[np.ndarray]:
        """
        Extract frames from video file.

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
                logger.error(f"Could not open video: {video_path}")
                return frames

            frame_count = 0
            while True:
                ret, frame = cap.read()
                if not ret:
                    break

                frames.append(frame)
                frame_count += 1

                if max_frames and frame_count >= max_frames:
                    logger.info(f"Reached max_frames limit: {max_frames}")
                    break

            cap.release()
            logger.info(f"Extracted {len(frames)} frames from {video_path}")

        except (OSError, RuntimeError, ValueError) as e:
            logger.error(f"Error extracting frames from {video_path}: {e}")

        return frames

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
