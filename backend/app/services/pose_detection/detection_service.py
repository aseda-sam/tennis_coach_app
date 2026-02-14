"""
Pose detection service using MediaPipe for independent pose analysis.
"""

import copy
import json
import logging
import time
from pathlib import Path
from typing import TYPE_CHECKING, Any, Dict, Iterator, List, Optional, Sequence, Tuple

if TYPE_CHECKING:
    from mediapipe.tasks.python.vision import PoseLandmarker

import cv2
import numpy as np
from sqlalchemy.orm import Session

from app.core.config import settings
from app.models.pose_detection import PoseDetection
from app.utils.video_utils import get_video_rotation

logger = logging.getLogger(__name__)


class PoseDetectionService:
    """Service for detecting human poses in videos using MediaPipe."""

    def __init__(self) -> None:
        """Initialize the pose detection service."""
        self.pose_detector = None
        self._scout_detector = None  # Lite model for scout mode
        self.mp_pose = None
        self.logger = logger
        self._initialize_mediapipe()

    def _initialize_mediapipe(self, use_lite: bool = False) -> None:
        """Initialize MediaPipe pose detection models.

        Args:
            use_lite: If True, use lite model for faster processing
        """
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
            model_path = self._get_or_download_model(use_lite=use_lite)

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
                f"✅ MediaPipe pose detection initialized successfully (v0.10.x, {'lite' if use_lite else 'heavy'} model)"
            )

        except ImportError as e:
            logger.error("Failed to import MediaPipe: %s", e)
            self.pose_detector = None
        except (RuntimeError, ValueError, OSError) as e:
            logger.error("Failed to initialize MediaPipe pose detection: %s", e)
            self.pose_detector = None

    def _get_or_download_model(self, use_lite: bool = False) -> str:
        """Get or download the MediaPipe pose landmarker model file.

        Args:
            use_lite: If True, use lite model; otherwise use heavy model

        Returns:
            Path to model file
        """
        import urllib.request
        from pathlib import Path

        model_dir = Path(settings.ML_MODELS_DIR)
        model_dir.mkdir(parents=True, exist_ok=True)

        if use_lite:
            model_url = "https://storage.googleapis.com/mediapipe-models/pose_landmarker/pose_landmarker_lite/float16/1/pose_landmarker_lite.task"
            model_path = model_dir / "pose_landmarker_lite.task"
        else:
            model_url = "https://storage.googleapis.com/mediapipe-models/pose_landmarker/pose_landmarker_heavy/float16/1/pose_landmarker_heavy.task"
            model_path = model_dir / "pose_landmarker.task"

        # Download if not exists
        if not model_path.exists():
            logger.info(
                f"Downloading MediaPipe pose landmarker {'lite' if use_lite else 'heavy'} model to {model_path}"
            )
            try:
                urllib.request.urlretrieve(model_url, model_path)  # noqa: S310 - Downloading from trusted Google storage
                logger.info("✅ Model downloaded successfully")
            except (urllib.error.URLError, OSError) as e:
                logger.error("Failed to download model: %s", e)
                if not use_lite:
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
        return self._detect_pose_in_frame_with_detector(frame, self.pose_detector)

    def _detect_pose_in_frame_with_detector(
        self, frame: np.ndarray, detector: "PoseLandmarker"
    ) -> Optional[Dict[str, List[float]]]:
        """
        Detect human pose in a single frame using specified detector.

        Args:
            frame: Input frame as numpy array
            detector: MediaPipe PoseLandmarker instance

        Returns:
            Dictionary of keypoint coordinates if pose detected, None otherwise
        """
        if not detector:
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
            detection_result = detector.detect_for_video(mp_image, timestamp_ms)

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
            logger.error("Error in pose detection: %s", e)
            return None

    def analyze_video_file(
        self,
        video_path: Path,
        confidence_threshold: Optional[float] = None,
        detection_threshold: Optional[float] = None,
        max_frames: Optional[int] = None,
        mode: str = "full",  # "scout" or "full"
    ) -> Dict[str, any]:
        """
        Analyze a video file for pose detection with streaming frame processing.

        Memory-efficient: processes one frame at a time, never holds all frames.

        Args:
            video_path: Path to video file
            confidence_threshold: Minimum confidence for pose detection
            detection_threshold: Minimum detection threshold
            max_frames: Maximum number of frames to process
            mode: "scout" (lite model, frame skip) or "full" (heavy model, all frames)

        Returns:
            Dictionary containing detailed pose detection results
        """
        start_time = time.time()
        is_scout_mode = mode == "scout"
        logger.info(
            f"Starting pose detection analysis for: {video_path} (mode: {mode})"
        )

        # Initialize appropriate detector if needed
        if is_scout_mode:
            if not self._scout_detector:
                # Create a separate scout detector instance with lite model
                scout_service = PoseDetectionService()
                scout_service._initialize_mediapipe(use_lite=True)
                self._scout_detector = scout_service.pose_detector
        else:
            if not self.pose_detector:
                self._initialize_mediapipe(use_lite=False)

        # Use appropriate detector
        detector = self._scout_detector if is_scout_mode else self.pose_detector

        if not detector:
            return {
                "error": "Pose detector not initialized",
                "pose_detections": [],
                "total_frames": 0,
                "frames_with_poses": 0,
                "total_pose_detections": 0,
                "detection_rate": 0.0,
                "processing_time_seconds": time.time() - start_time,
                "frame_processing_rate": 0.0,
                "confidence_scores": [],
            }

        # Accumulators for results (lightweight: keypoints only, not raw frames)
        pose_detections = []
        confidence_scores = []
        frames_with_poses = 0
        total_frames = 0

        # Get video FPS for timestamp calculation
        cap = cv2.VideoCapture(str(video_path))
        if not cap.isOpened():
            return {
                "error": "Could not open video file",
                "pose_detections": [],
                "total_frames": 0,
                "frames_with_poses": 0,
                "total_pose_detections": 0,
                "detection_rate": 0.0,
                "processing_time_seconds": time.time() - start_time,
                "frame_processing_rate": 0.0,
                "confidence_scores": [],
            }
        fps = cap.get(cv2.CAP_PROP_FPS)
        cap.release()

        # Scout mode: process every Nth frame (SCOUT_FRAME_SKIP; e.g. 4 → 15fps at 60fps input)
        frame_skip = settings.SCOUT_FRAME_SKIP if is_scout_mode else 1

        try:
            # Process frames one at a time via generator
            processed_frame_count = 0
            for frame_index, frame in self._iter_frames(video_path, max_frames):
                # Skip frames in scout mode
                if is_scout_mode and frame_index % frame_skip != 0:
                    # Still store None for skipped frames to maintain frame_index alignment
                    timestamp_ms = (frame_index * 1000.0 / fps) if fps > 0 else 0.0
                    pose_detections.append(
                        {
                            "frame_index": frame_index,
                            "timestamp_ms": timestamp_ms,
                            "keypoints": None,
                        }
                    )
                    confidence_scores.append(0.0)
                    total_frames += 1
                    continue

                total_frames += 1
                processed_frame_count += 1

                # Calculate timestamp in milliseconds
                timestamp_ms = (frame_index * 1000.0 / fps) if fps > 0 else 0.0

                # Detect pose in single frame (use appropriate detector)
                pose_keypoints = self._detect_pose_in_frame_with_detector(
                    frame, detector
                )

                if pose_keypoints is not None:
                    frames_with_poses += 1
                    confidence_scores.append(settings.POSE_OVERALL_CONFIDENCE)
                    # Store with timestamp_ms
                    pose_detections.append(
                        {
                            "frame_index": frame_index,
                            "timestamp_ms": timestamp_ms,
                            "keypoints": pose_keypoints,
                        }
                    )
                else:
                    confidence_scores.append(0.0)
                    # Store None for frames without pose, but include timestamp_ms for consistency
                    pose_detections.append(
                        {
                            "frame_index": frame_index,
                            "timestamp_ms": timestamp_ms,
                            "keypoints": None,
                        }
                    )

                # Log progress every 100 frames
                if frame_index % 100 == 0:
                    logger.debug(
                        f"Frame {frame_index}: pose_detected={pose_keypoints is not None}"
                    )

                # Frame is now out of scope and can be garbage collected

            if total_frames == 0:
                return {
                    "error": "No frames could be extracted from video",
                    "pose_detections": [],
                    "total_frames": 0,
                    "frames_with_poses": 0,
                    "total_pose_detections": 0,
                    "detection_rate": 0.0,
                    "processing_time_seconds": time.time() - start_time,
                    "frame_processing_rate": 0.0,
                    "confidence_scores": [],
                }

            # Calculate metrics
            processing_time = time.time() - start_time
            non_zero_confidences = [c for c in confidence_scores if c > 0]

            results = {
                "pose_detections": pose_detections,
                "total_frames": total_frames,
                "frames_with_poses": frames_with_poses,
                "total_pose_detections": frames_with_poses,
                "detection_rate": frames_with_poses / total_frames
                if total_frames
                else 0.0,
                "processing_time_seconds": processing_time,
                "frame_processing_rate": processed_frame_count / processing_time
                if processing_time > 0 and is_scout_mode
                else (total_frames / processing_time if processing_time > 0 else 0),
                "confidence_scores": confidence_scores,
                "average_confidence": (
                    sum(non_zero_confidences) / len(non_zero_confidences)
                    if non_zero_confidences
                    else None
                ),
                "min_confidence": min(non_zero_confidences)
                if non_zero_confidences
                else None,
                "max_confidence": max(non_zero_confidences)
                if non_zero_confidences
                else None,
                "confidence_threshold": confidence_threshold or 0.5,
                "detection_threshold": detection_threshold or 0.5,
                "video_path": str(video_path),
                "mode": mode,
            }

            logger.info(
                f"Pose detection complete: {frames_with_poses}/{total_frames} frames with poses "
                f"in {processing_time:.2f}s"
            )
            return results

        except (RuntimeError, ValueError, OSError) as e:
            logger.error("Error in pose detection: %s", e)
            return {
                "error": str(e),
                "pose_detections": [],
                "total_frames": total_frames,
                "frames_with_poses": frames_with_poses,
                "total_pose_detections": frames_with_poses,
                "detection_rate": 0.0,
                "processing_time_seconds": time.time() - start_time,
                "frame_processing_rate": 0.0,
                "confidence_scores": confidence_scores,
            }

    def analyze_serve_windows(
        self,
        video_path: Path,
        windows: List[Dict[str, float]],  # [{"start_ms": 1000, "end_ms": 4000}, ...]
        padding_ms: float = 500,
        confidence_threshold: Optional[float] = None,
        detection_threshold: Optional[float] = None,
    ) -> Dict[str, Any]:
        """
        Run full pose detection only within specified time windows.

        Args:
            video_path: Path to video file
            windows: List of window dicts with start_ms and end_ms
            padding_ms: Padding to add before/after each window (milliseconds)
            confidence_threshold: Minimum confidence for pose detection
            detection_threshold: Minimum detection threshold

        Returns:
            Dictionary containing pose detection results for specified windows
        """
        start_time = time.time()
        logger.info(
            f"Starting refine pass for {len(windows)} serve windows in: {video_path}"
        )

        if not self.pose_detector:
            self._initialize_mediapipe(use_lite=False)
            if not self.pose_detector:
                return {
                    "error": "Pose detector not initialized",
                    "pose_detections": [],
                    "total_frames": 0,
                    "frames_with_poses": 0,
                    "total_pose_detections": 0,
                    "detection_rate": 0.0,
                    "processing_time_seconds": time.time() - start_time,
                    "frame_processing_rate": 0.0,
                    "confidence_scores": [],
                }

        # Get video FPS for frame calculation
        cap = cv2.VideoCapture(str(video_path))
        if not cap.isOpened():
            return {
                "error": "Could not open video file",
                "pose_detections": [],
                "total_frames": 0,
                "frames_with_poses": 0,
                "total_pose_detections": 0,
                "detection_rate": 0.0,
                "processing_time_seconds": time.time() - start_time,
                "frame_processing_rate": 0.0,
                "confidence_scores": [],
            }
        fps = cap.get(cv2.CAP_PROP_FPS)
        total_video_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
        cap.release()

        # Accumulators
        pose_detections = []
        confidence_scores = []
        frames_with_poses = 0
        total_frames = 0

        # Create a mapping of frame_index -> pose_data for all frames
        # Initialize all frames as None
        all_frames_pose_data = [None] * total_video_frames
        all_frames_confidence = [0.0] * total_video_frames

        try:
            # Process each window
            for window_idx, window in enumerate(windows):
                start_ms = window.get("start_ms", 0.0)
                end_ms = window.get("end_ms", 0.0)

                # Add padding
                padded_start_ms = max(0, start_ms - padding_ms)
                padded_end_ms = min(
                    (total_video_frames / fps * 1000)
                    if fps > 0
                    else end_ms + padding_ms,
                    end_ms + padding_ms,
                )

                # Convert to frame indices
                start_frame = int(padded_start_ms * fps / 1000.0) if fps > 0 else 0
                end_frame = (
                    int(padded_end_ms * fps / 1000.0) if fps > 0 else total_video_frames
                )

                logger.info(
                    f"Processing window {window_idx + 1}/{len(windows)}: "
                    f"frames {start_frame}-{end_frame} ({padded_start_ms:.0f}ms - {padded_end_ms:.0f}ms)"
                )

                # Process frames in this window
                cap = cv2.VideoCapture(str(video_path))
                if not cap.isOpened():
                    logger.error("Could not open video for window %s", window_idx)
                    continue

                # Seek to start frame
                cap.set(cv2.CAP_PROP_POS_FRAMES, start_frame)

                frame_index = start_frame
                while frame_index <= end_frame and frame_index < total_video_frames:
                    ret, frame = cap.read()
                    if not ret:
                        break

                    total_frames += 1
                    timestamp_ms = (frame_index * 1000.0 / fps) if fps > 0 else 0.0

                    # Detect pose in frame
                    pose_keypoints = self._detect_pose_in_frame_with_detector(
                        frame, self.pose_detector
                    )

                    if pose_keypoints is not None:
                        frames_with_poses += 1
                        confidence_scores.append(settings.POSE_OVERALL_CONFIDENCE)
                        all_frames_pose_data[frame_index] = {
                            "frame_index": frame_index,
                            "timestamp_ms": timestamp_ms,
                            "keypoints": pose_keypoints,
                        }
                        all_frames_confidence[frame_index] = (
                            settings.POSE_OVERALL_CONFIDENCE
                        )
                    else:
                        confidence_scores.append(0.0)
                        all_frames_pose_data[frame_index] = {
                            "frame_index": frame_index,
                            "timestamp_ms": timestamp_ms,
                            "keypoints": None,
                        }
                        all_frames_confidence[frame_index] = 0.0

                    frame_index += 1

                cap.release()

            # Convert to list format (maintain frame_index alignment)
            pose_detections = all_frames_pose_data
            confidence_scores = all_frames_confidence

            # Calculate metrics
            processing_time = time.time() - start_time
            non_zero_confidences = [c for c in confidence_scores if c > 0]

            results = {
                "pose_detections": pose_detections,
                "total_frames": total_video_frames,  # Total video frames
                "frames_with_poses": frames_with_poses,
                "total_pose_detections": frames_with_poses,
                "detection_rate": frames_with_poses / total_frames
                if total_frames > 0
                else 0.0,
                "processing_time_seconds": processing_time,
                "frame_processing_rate": total_frames / processing_time
                if processing_time > 0
                else 0,
                "confidence_scores": confidence_scores,
                "average_confidence": (
                    sum(non_zero_confidences) / len(non_zero_confidences)
                    if non_zero_confidences
                    else None
                ),
                "min_confidence": min(non_zero_confidences)
                if non_zero_confidences
                else None,
                "max_confidence": max(non_zero_confidences)
                if non_zero_confidences
                else None,
                "confidence_threshold": confidence_threshold or 0.5,
                "detection_threshold": detection_threshold or 0.5,
                "video_path": str(video_path),
                "mode": "refine",
                "windows_processed": len(windows),
            }

            logger.info(
                f"Refine pass complete: {frames_with_poses}/{total_frames} frames with poses "
                f"in {processing_time:.2f}s for {len(windows)} windows"
            )
            return results

        except (RuntimeError, ValueError, OSError) as e:
            logger.error("Error in refine pass: %s", e)
            return {
                "error": str(e),
                "pose_detections": [],
                "total_frames": total_frames,
                "frames_with_poses": frames_with_poses,
                "total_pose_detections": frames_with_poses,
                "detection_rate": 0.0,
                "processing_time_seconds": time.time() - start_time,
                "frame_processing_rate": 0.0,
                "confidence_scores": confidence_scores,
            }

    @staticmethod
    def merge_pose_data(
        scout_data: List[Dict[str, Any]],
        refine_data: List[Optional[Dict[str, Any]]],
    ) -> List[Dict[str, Any]]:
        """
        Merge refine pose data into scout data.

        Refine data overwrites scout data for frames where refine has keypoints.
        This combines sparse scout data (entire video) with dense refine data
        (serve windows only).

        Args:
            scout_data: Pose data from scout pass (sparse, covers entire video)
            refine_data: Pose data from refine pass (dense, only serve windows)

        Returns:
            Merged pose data with refine data overwriting scout for serve windows
        """
        merged = copy.deepcopy(scout_data)

        for frame_idx, refine_frame in enumerate(refine_data):
            if frame_idx >= len(merged):
                break
            if refine_frame is None:
                continue
            refine_keypoints = refine_frame.get("keypoints")
            if refine_keypoints is not None:
                merged[frame_idx] = refine_frame

        return merged

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

        # Serialize time windows if present
        time_windows_json = None
        if detection_results.get("time_windows"):
            time_windows_json = json.dumps(detection_results["time_windows"])

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
            detection_mode=detection_results.get("mode", "full"),
            time_windows=time_windows_json,
        )

        db.add(pose_detection)
        db.commit()
        db.refresh(pose_detection)

        logger.info("Saved pose detection results for video %s", video_id)
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

            for frame_index, frame_data in enumerate(raw_pose_data):
                # Handle both old format (dict of keypoints or None) and new format (dict with frame_index/timestamp_ms/keypoints)
                if isinstance(frame_data, dict) and "keypoints" in frame_data:
                    # New format with timestamp_ms
                    timestamp_ms = frame_data.get("timestamp_ms", 0.0)
                    frame_pose_data = frame_data.get("keypoints")
                else:
                    # Old format (backward compatibility)
                    frame_pose_data = frame_data
                    timestamp_ms = 0.0  # Will be calculated from fps if available

                if frame_pose_data is None:
                    # No pose detected in this frame
                    formatted_data.append(
                        {
                            "frame_index": frame_index,
                            "timestamp_ms": timestamp_ms,
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
                        "timestamp_ms": timestamp_ms,
                        "keypoints": keypoints,
                        "overall_confidence": overall_confidence,
                    }
                )

            return formatted_data

        except (json.JSONDecodeError, KeyError, TypeError) as e:
            logger.error("Failed to deserialize pose data: %s", e)
            return None

    def _rotate_frame(self, frame: np.ndarray, rotation: int) -> np.ndarray:
        """
        Rotate frame to match display orientation.

        The rotation value from ffprobe indicates how much the raw frames need
        to be rotated to display correctly. A negative value means rotate
        clockwise by that amount (e.g., -90 means rotate 90° clockwise).

        Args:
            frame: Input frame
            rotation: Rotation in degrees from ffprobe (-90, 90, 180, -180, etc.)

        Returns:
            Rotated frame
        """
        # Determine rotation operation based on ffprobe rotation value
        # rotation=-90: raw video needs 90° clockwise rotation to display correctly
        # rotation=90: raw video needs 90° counterclockwise rotation to display correctly
        # rotation=180/-180: raw video needs 180° rotation
        if rotation == -90 or rotation == 270:
            return cv2.rotate(frame, cv2.ROTATE_90_CLOCKWISE)
        elif rotation == 90 or rotation == -270:
            return cv2.rotate(frame, cv2.ROTATE_90_COUNTERCLOCKWISE)
        elif rotation == 180 or rotation == -180:
            return cv2.rotate(frame, cv2.ROTATE_180)
        else:
            return frame

    def _iter_frames(
        self, video_path: Path, max_frames: Optional[int] = None
    ) -> Iterator[Tuple[int, np.ndarray]]:
        """
        Yield frames one at a time instead of loading all into memory.

        Frames are rotated according to video metadata to match browser display.

        Args:
            video_path: Path to video file
            max_frames: Maximum number of frames to extract

        Yields:
            Tuple of (frame_index, frame_array)
        """
        try:
            cap = cv2.VideoCapture(str(video_path))
            if not cap.isOpened():
                logger.error("Could not open video: %s", video_path)
                return

            # Disable OpenCV's auto-rotation to get raw frames
            # OpenCV 4.x auto-rotates based on metadata, but interprets rotation sign
            # differently than browsers. We disable it and manually rotate using
            # ffprobe's rotation value (which matches browser behavior).
            cap.set(cv2.CAP_PROP_ORIENTATION_AUTO, 0)

            # Get rotation once for the entire video
            rotation = get_video_rotation(video_path)
            if rotation != 0:
                logger.info(
                    "Applying rotation=%d° to frames from %s", rotation, video_path
                )

            frame_index = 0
            while True:
                ret, frame = cap.read()
                if not ret:
                    break

                # Rotate frame to match display orientation
                if rotation != 0:
                    frame = self._rotate_frame(frame, rotation)

                yield frame_index, frame
                frame_index += 1

                if max_frames and frame_index >= max_frames:
                    logger.info("Reached max_frames limit: %s", max_frames)
                    break

            logger.info("Yielded %s frames from %s", frame_index, video_path)

        except (OSError, RuntimeError, ValueError) as e:
            logger.error("Error extracting frames from %s: %s", video_path, e)
        finally:
            if "cap" in locals():
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
