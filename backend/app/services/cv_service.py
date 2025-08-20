"""
Computer Vision Service for tennis video analysis.
Handles video processing, ball detection, and player tracking.
"""

import logging
import time
from pathlib import Path
from typing import Any, Dict, List, Optional, Sequence, Tuple

import cv2
import numpy as np

from app.core.config import settings

logger = logging.getLogger(__name__)


def log_timing(operation_name: str, start_time: float) -> None:
    """
    Log timing information for an operation.

    Args:
        operation_name: Name of the operation being timed
        start_time: Start time from time.time()
    """
    elapsed_time = time.time() - start_time
    logger.info(f"⏱️ {operation_name} completed in {elapsed_time:.3f}s")


def log_timing_error(operation_name: str, start_time: float, error: Exception) -> None:
    """
    Log timing information for a failed operation.

    Args:
        operation_name: Name of the operation being timed
        start_time: Start time from time.time()
        error: The exception that occurred
    """
    elapsed_time = time.time() - start_time
    logger.error(f"❌ {operation_name} failed after {elapsed_time:.3f}s: {error}")


class CVService:
    """Computer Vision service for video analysis."""

    def __init__(self) -> None:
        self.ball_detector = None
        self.pose_detector = None
        self.yolo_models = {}  # Cache for different YOLO models
        self._initialize_models()

    def _initialize_models(self) -> None:
        """Initialize YOLO and MediaPipe models."""
        start_time = time.time()

        # Initialize YOLO models for ball detection
        self.yolo_models = {}  # Ensure it's always initialized as empty dict

        try:
            from ultralytics import YOLO

            # Try to initialize models one by one to handle partial failures
            # YOLO will automatically download models if they don't exist locally
            models_to_try = [
                (model_name, model_path)
                for model_name, model_path in settings.YOLO_MODELS.items()
            ]

            for model_name, model_path in models_to_try:
                try:
                    logger.info(f"Loading YOLO model: {model_name} ({model_path})")
                    self.yolo_models[model_name] = YOLO(model_path)
                    logger.info(f"Successfully loaded YOLO model: {model_name}")
                except (OSError, RuntimeError, ImportError) as e:
                    logger.warning(f"Failed to load YOLO model {model_name}: {e}")
                    continue

            if self.yolo_models:
                # Set default model to the configured default or first available one
                default_model = (
                    settings.YOLO_DEFAULT_MODEL
                    if settings.YOLO_DEFAULT_MODEL in self.yolo_models
                    else next(iter(self.yolo_models.keys()))
                )
                self.ball_detector = self.yolo_models[default_model]
                logger.info("YOLO models initialized successfully")
                logger.info(f"Available models: {list(self.yolo_models.keys())}")
                logger.info(f"Default model: {default_model}")
            else:
                logger.warning(
                    "No YOLO models could be loaded, ball detection disabled"
                )
                self.ball_detector = None

        except ImportError:
            logger.warning("Ultralytics not available, ball detection disabled")
            self.ball_detector = None
        except (OSError, RuntimeError, ValueError) as e:
            logger.error(f"Unexpected error during YOLO initialization: {e}")
            self.ball_detector = None

        try:
            # Initialize MediaPipe for pose estimation
            import mediapipe as mp

            self.mp_pose = mp.solutions.pose
            self.pose_detector = self.mp_pose.Pose(
                static_image_mode=False,
                model_complexity=1,  # 0, 1, or 2 (1 is good balance)
                smooth_landmarks=True,
                enable_segmentation=False,
                smooth_segmentation=True,
                min_detection_confidence=0.3,  # Lowered from 0.5
                min_tracking_confidence=0.3,  # Lowered from 0.5
            )
            logger.info("MediaPipe Pose model initialized successfully")
        except ImportError:
            logger.warning("MediaPipe not available, pose detection disabled")
            self.pose_detector = None
        except (OSError, RuntimeError) as e:
            logger.error(f"Failed to initialize MediaPipe Pose: {e}")
            self.pose_detector = None

        elapsed_time = time.time() - start_time
        logger.info(f"⏱️ Model initialization completed in {elapsed_time:.3f}s")

    def _select_yolo_model(self, video_quality_level: Optional[str] = None) -> str:
        """
        Select appropriate YOLO model based on video quality.

        Args:
            video_quality_level: Quality level from video assessment

        Returns:
            Model name to use ('nano' or 'small')
        """
        # Check what models are actually available
        available_models = list(self.yolo_models.keys()) if self.yolo_models else []

        if not available_models:
            logger.warning("No YOLO models available")
            return "nano"  # Return default even if not available (will be handled by caller)

        if not video_quality_level or video_quality_level == "unknown":
            # Return the first available model (prefer nano if available)
            if "nano" in available_models:
                return "nano"
            return available_models[0]

        # Model selection logic based on quality
        quality_model_mapping = {
            "excellent": "small",  # Use better model for excellent quality
            "good": "small",  # Use better model for good quality
            "fair": "nano",  # Use faster model for fair quality
            "poor": "nano",  # Use faster model for poor quality
        }

        preferred_model = quality_model_mapping.get(video_quality_level, "nano")

        # Check if preferred model is available, otherwise use fallback
        if preferred_model in available_models:
            return preferred_model
        else:
            logger.warning(
                f"Preferred model '{preferred_model}' not available, using fallback"
            )
            # Return the first available model (prefer nano if available)
            if "nano" in available_models:
                return "nano"
            return available_models[0]

    def extract_frames(
        self, video_path: Path, max_frames: Optional[int] = None
    ) -> List[np.ndarray]:
        """
        Extract frames from video file.

        Args:
            video_path: Path to video file
            max_frames: Maximum number of frames to extract (None = extract all frames)

        Returns:
            List of frame arrays
        """
        start_time = time.time()
        frames = []
        try:
            cap = cv2.VideoCapture(str(video_path))
            if not cap.isOpened():
                logger.error(f"Could not open video: {video_path}")
                return frames

            frame_count = 0
            total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
            fps = cap.get(cv2.CAP_PROP_FPS)

            # Use FRAME_SKIP_RATIO from config for proper frame skipping
            from app.core.config import env_limits

            frame_skip_ratio = env_limits["frame_skip_ratio"]

            # Calculate frame interval based on max_frames and frame_skip_ratio
            if max_frames is None:
                # If no max_frames specified, use frame_skip_ratio directly
                interval = frame_skip_ratio
            else:
                # If max_frames specified, calculate interval to get max_frames
                # but respect the minimum frame_skip_ratio
                calculated_interval = (
                    total_frames // max_frames if total_frames > max_frames else 1
                )
                interval = max(calculated_interval, frame_skip_ratio)

            # Log frame skipping status
            if frame_skip_ratio > 1:
                logger.info(
                    f"Frame skipping enabled: processing every {frame_skip_ratio} frames"
                )
            else:
                logger.info("Frame skipping disabled: processing all frames")

            logger.info(f"Extracting frames from {video_path}")
            logger.info(
                f"Total frames: {total_frames}, FPS: {fps}, Frame skip ratio: {frame_skip_ratio}, Interval: {interval}"
            )

            # Process frames with proper skipping
            while frame_count < total_frames:
                ret, frame = cap.read()
                if not ret:
                    break

                # Only keep frames at interval
                if frame_count % interval == 0:
                    frames.append(frame)

                    # Stop if we've reached max_frames
                    if max_frames is not None and len(frames) >= max_frames:
                        break

                frame_count += interval

                # Skip frames to maintain interval
                if interval > 1:
                    for _ in range(interval - 1):
                        cap.read()

            cap.release()
            logger.info(f"Extracted {len(frames)} frames using interval {interval}")

        except (OSError, RuntimeError, ValueError) as e:
            logger.error(f"Error extracting frames: {e}")

        log_timing("Frame Extraction", start_time)
        return frames

    def detect_balls(
        self, frames: List[np.ndarray], confidence_threshold: Optional[float] = None
    ) -> List[List[Dict[str, Any]]]:
        """
        Detect tennis balls in frames using YOLO.

        Args:
            frames: List of frame arrays

        Returns:
            List of detections per frame
        """
        start_time = time.time()
        if not self.ball_detector:
            logger.warning("Ball detector not available")
            return [[] for _ in frames]

        detections = []
        frame_timings = []

        try:
            for i, frame in enumerate(frames):
                frame_start = time.time()

                # Run YOLO detection
                results = self.ball_detector(frame, verbose=False)

                frame_detections = []
                for result in results:
                    boxes = result.boxes
                    if boxes is not None:
                        for box in boxes:
                            # Get bounding box coordinates
                            x1, y1, x2, y2 = box.xyxy[0].cpu().numpy()
                            confidence = box.conf[0].cpu().numpy()
                            class_id = int(box.cls[0].cpu().numpy())

                            # Filter for sports balls (class 32 in COCO dataset)
                            # Use adaptive confidence threshold or fallback to config default
                            threshold = (
                                confidence_threshold
                                or settings.BALL_CONFIDENCE_THRESHOLD
                            )
                            if class_id == 32 and confidence > threshold:
                                frame_detections.append(
                                    {
                                        "bbox": [int(x1), int(y1), int(x2), int(y2)],
                                        "confidence": float(confidence),
                                        "class_id": class_id,
                                        "frame_index": i,
                                    }
                                )

                detections.append(frame_detections)
                frame_time = time.time() - frame_start
                frame_timings.append(frame_time)

                # Log every 10th frame for performance monitoring
                if i % 10 == 0:
                    logger.debug(
                        f"Frame {i}: {len(frame_detections)} detections in {frame_time:.3f}s"
                    )

            total_detections = sum(len(d) for d in detections)
            avg_frame_time = (
                sum(frame_timings) / len(frame_timings) if frame_timings else 0
            )
            total_time = sum(frame_timings)

            logger.info(f"Ball detection complete: {total_detections} total detections")
            logger.info(
                f"⏱️ Average frame time: {avg_frame_time:.3f}s, Total time: {total_time:.3f}s"
            )

        except (RuntimeError, ValueError, OSError) as e:
            logger.error(f"Error in ball detection: {e}")
            detections = [[] for _ in frames]

        log_timing("Ball Detection", start_time)
        return detections

    def detect_pose(self, frame: np.ndarray) -> Optional[Dict[str, List[float]]]:
        """
        Detect human pose in a frame using MediaPipe.

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

    def detect_poses_batch(
        self, frames: List[np.ndarray]
    ) -> List[Optional[Dict[str, List[float]]]]:
        """
        Detect poses in a batch of frames with timing information.

        Args:
            frames: List of frame arrays

        Returns:
            List of pose detections per frame
        """
        start_time = time.time()
        if not self.pose_detector:
            logger.warning("Pose detector not available")
            return [None] * len(frames)

        pose_detections = []
        frame_timings = []

        try:
            for i, frame in enumerate(frames):
                frame_start = time.time()
                pose_keypoints = self.detect_pose(frame)
                pose_detections.append(pose_keypoints)

                frame_time = time.time() - frame_start
                frame_timings.append(frame_time)

                # Log every 10th frame for performance monitoring
                if i % 10 == 0:
                    frame_shape = frame.shape
                    logger.debug(
                        f"Frame {i}: shape={frame_shape}, pose_detected={pose_keypoints is not None}, time={frame_time:.3f}s"
                    )

            total_poses = sum(1 for p in pose_detections if p is not None)
            avg_frame_time = (
                sum(frame_timings) / len(frame_timings) if frame_timings else 0
            )
            total_time = sum(frame_timings)

            logger.info(
                f"Pose detection complete: {total_poses} poses detected out of {len(frames)} frames"
            )
            logger.info(
                f"⏱️ Average frame time: {avg_frame_time:.3f}s, Total time: {total_time:.3f}s"
            )

        except (RuntimeError, ValueError, OSError) as e:
            logger.error(f"Error in batch pose detection: {e}")
            pose_detections = [None] * len(frames)

        log_timing("Pose Detection", start_time)
        return pose_detections

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

    def draw_pose_overlay(
        self, frame: np.ndarray, keypoints: Dict[str, List[float]]
    ) -> np.ndarray:
        """
        Draw pose keypoints and connections on frame.

        Args:
            frame: Input frame
            keypoints: Pose keypoints dictionary

        Returns:
            Frame with pose overlay
        """
        if not keypoints:
            return frame

        # Define connections between keypoints (tennis-focused back view)
        # Focus on upper body stroke mechanics and lower body positioning
        connections = [
            # Upper body stroke connections
            ("left_shoulder", "right_shoulder"),  # Shoulder line
            ("left_shoulder", "left_elbow"),  # Left arm
            ("right_shoulder", "right_elbow"),  # Right arm
            ("left_elbow", "left_wrist"),  # Left forearm
            ("right_elbow", "right_wrist"),  # Right forearm
            # Core connections
            ("left_shoulder", "left_hip"),  # Left torso
            ("right_shoulder", "right_hip"),  # Right torso
            ("left_hip", "right_hip"),  # Hip line
            # Lower body positioning
            ("left_hip", "left_knee"),  # Left thigh
            ("right_hip", "right_knee"),  # Right thigh
            ("left_knee", "left_ankle"),  # Left shin
            ("right_knee", "right_ankle"),  # Right shin
        ]

        # Draw connections
        for connection in connections:
            if connection[0] in keypoints and connection[1] in keypoints:
                pt1 = tuple(map(int, keypoints[connection[0]]))
                pt2 = tuple(map(int, keypoints[connection[1]]))
                cv2.line(frame, pt1, pt2, (0, 255, 0), 2)

        # Draw keypoints
        for keypoint_name, coords in keypoints.items():
            if coords:
                x, y = int(coords[0]), int(coords[1])
                cv2.circle(frame, (x, y), 5, (255, 0, 0), -1)
                cv2.putText(
                    frame,
                    keypoint_name,
                    (x + 10, y - 10),
                    cv2.FONT_HERSHEY_SIMPLEX,
                    0.3,
                    (255, 255, 255),
                    1,
                )

        return frame

    def _safe_restore_file(self, temp_path: Path, target_path: Path) -> None:
        """
        Safely restore a file from temporary location to target location.

        Args:
            temp_path: Path to temporary file
            target_path: Path to restore file to
        """
        try:
            if not temp_path.exists():
                logger.warning(
                    f"Temporary file does not exist for restoration: {temp_path}"
                )
                return

            # Remove target file if it exists to avoid rename conflicts
            if target_path.exists():
                try:
                    target_path.unlink()
                except OSError as e:
                    logger.warning(
                        f"Failed to remove existing target file {target_path}: {e}"
                    )
                    # Try with a backup name if we can't remove the original
                    backup_path = target_path.with_suffix(
                        f".backup_{target_path.suffix}"
                    )
                    temp_path.rename(backup_path)
                    logger.info(f"Restored file to backup location: {backup_path}")
                    return

            # Restore the file
            temp_path.rename(target_path)
            logger.info(f"Successfully restored file from {temp_path} to {target_path}")

        except OSError as e:
            logger.error(
                f"Failed to restore file from {temp_path} to {target_path}: {e}"
            )
            # File is left at temp_path location for manual cleanup

    def analyze_video(
        self,
        video_path: Path,
        include_pose: bool = True,
        confidence_threshold: Optional[float] = None,
        video_quality_level: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Perform comprehensive video analysis with ball detection and pose estimation.

        Args:
            video_path: Path to video file
            include_pose: Whether to include pose detection (default: True)
            confidence_threshold: Optional confidence threshold (if not provided, uses default)
            video_quality_level: Video quality level for model selection

        Returns:
            Analysis results dictionary with timing information
        """
        start_time = time.time()
        logger.info(
            f"Starting analysis of {video_path} (pose detection: {include_pose})"
        )

        # Track overall timing
        analysis_start = time.time()
        stage_timings = {}

        # Extract frames
        frame_extraction_start = time.time()
        frames = self.extract_frames(video_path)
        stage_timings["frame_extraction"] = time.time() - frame_extraction_start

        if not frames:
            return {
                "error": "Failed to extract frames from video",
                "frames_processed": 0,
                "ball_detections": [],
                "pose_detections": [],
                "analysis_summary": {},
                "timing": stage_timings,
            }

        # Select YOLO model based on video quality
        selected_model = self._select_yolo_model(video_quality_level)

        # Check if the selected model exists in available models
        if not self.yolo_models or selected_model not in self.yolo_models:
            logger.warning(f"Selected YOLO model '{selected_model}' not available")
            if self.yolo_models:
                # Use the first available model as fallback
                fallback_model = next(iter(self.yolo_models.keys()))
                logger.info(f"Using fallback model: {fallback_model}")
                self.ball_detector = self.yolo_models[fallback_model]
                selected_model = fallback_model
            else:
                # No models available at all
                logger.error("No YOLO models available for ball detection")
                return {
                    "error": "Ball detection models not available",
                    "frames_processed": len(frames),
                    "ball_detections": [[] for _ in frames],
                    "pose_detections": [],
                    "analysis_summary": {
                        "total_frames": len(frames),
                        "frames_with_balls": 0,
                        "total_ball_detections": 0,
                        "average_detections_per_frame": 0,
                        "detection_rate": 0,
                        "frames_with_pose": 0,
                        "pose_detection_rate": 0,
                        "video_quality": {},
                        "confidence_threshold_used": confidence_threshold
                        or settings.BALL_CONFIDENCE_THRESHOLD,
                        "yolo_model_used": "none",
                        "yolo_model_selection_reason": "No models available",
                    },
                    "timing": stage_timings,
                }
        else:
            self.ball_detector = self.yolo_models[selected_model]

        logger.info(
            f"Selected YOLO model: {selected_model} (quality: {video_quality_level or 'unknown'})"
        )

        # Use provided confidence threshold or default
        adaptive_confidence_threshold = (
            confidence_threshold or settings.BALL_CONFIDENCE_THRESHOLD
        )
        logger.info(f"Using confidence threshold: {adaptive_confidence_threshold:.3f}")

        # Detect balls with confidence threshold
        ball_detection_start = time.time()
        ball_detections = self.detect_balls(
            frames, confidence_threshold=adaptive_confidence_threshold
        )
        stage_timings["ball_detection"] = time.time() - ball_detection_start

        # Detect poses (if enabled)
        pose_detections = []
        annotated_frames = []

        if include_pose and self.pose_detector:
            logger.info("Starting pose detection...")
            logger.info(f"Processing {len(frames)} frames for pose detection")

            pose_detection_start = time.time()
            pose_detections = self.detect_poses_batch(frames)
            stage_timings["pose_detection"] = time.time() - pose_detection_start

            # Create annotated frames
            annotation_start = time.time()
            for i, frame in enumerate(frames):
                pose_keypoints = pose_detections[i]

                # Create annotated frame with both ball and pose overlays
                annotated_frame = frame.copy()

                # Draw ball detections
                for detection in ball_detections[i]:
                    bbox = detection["bbox"]
                    cv2.rectangle(
                        annotated_frame,
                        (bbox[0], bbox[1]),
                        (bbox[2], bbox[3]),
                        (0, 0, 255),
                        2,
                    )
                    cv2.putText(
                        annotated_frame,
                        f"Ball: {detection['confidence']:.2f}",
                        (bbox[0], bbox[1] - 10),
                        cv2.FONT_HERSHEY_SIMPLEX,
                        0.5,
                        (0, 0, 255),
                        1,
                    )

                # Draw pose overlay
                if pose_keypoints:
                    annotated_frame = self.draw_pose_overlay(
                        annotated_frame, pose_keypoints
                    )

                annotated_frames.append(annotated_frame)

            stage_timings["frame_annotation"] = time.time() - annotation_start
        else:
            logger.info("Skipping pose detection (disabled or model not available)")
            pose_detections = [None] * len(frames)
            annotated_frames = frames.copy()

        # Calculate analysis summary
        total_ball_detections = sum(len(d) for d in ball_detections)
        frames_with_balls = sum(1 for d in ball_detections if d)
        frames_with_pose = sum(1 for p in pose_detections if p is not None)

        # Create annotated video (only for pose detection, skip if no poses found)
        annotated_video_path = None
        if frames_with_pose > 0:
            logger.info(
                f"Creating annotated video with {frames_with_pose} frames containing poses"
            )
            video_creation_start = time.time()
            annotated_video_path = self._create_annotated_video(
                video_path, annotated_frames
            )
            stage_timings["video_creation"] = time.time() - video_creation_start

            if annotated_video_path:
                logger.info(
                    f"Successfully created annotated video: {annotated_video_path}"
                )
            else:
                logger.warning("Failed to create annotated video")
        else:
            logger.info("No poses detected, skipping annotated video creation")

        # Calculate total analysis time
        total_analysis_time = time.time() - analysis_start
        stage_timings["total_analysis"] = total_analysis_time

        analysis_summary = {
            "total_frames": len(frames),
            "frames_with_balls": frames_with_balls,
            "total_ball_detections": total_ball_detections,
            "average_detections_per_frame": total_ball_detections / len(frames)
            if frames
            else 0,
            "detection_rate": frames_with_balls / len(frames) if frames else 0,
            "frames_with_pose": frames_with_pose,
            "pose_detection_rate": frames_with_pose / len(frames) if frames else 0,
            "video_quality": {},  # Quality assessment is now done during upload
            "confidence_threshold_used": adaptive_confidence_threshold,
            "yolo_model_used": selected_model,
            "yolo_model_selection_reason": f"Quality-based selection: {video_quality_level or 'unknown'} quality",
        }

        # Log detailed timing breakdown
        logger.info("📊 Analysis Timing Breakdown:")
        for stage, duration in stage_timings.items():
            percentage = (
                (duration / total_analysis_time) * 100 if total_analysis_time > 0 else 0
            )
            logger.info(f"  {stage}: {duration:.3f}s ({percentage:.1f}%)")

        results = {
            "frames_processed": len(frames),
            "ball_detections": ball_detections,
            "pose_detections": pose_detections,
            "analysis_summary": analysis_summary,
            "video_path": str(video_path),
            "annotated_video_path": str(annotated_video_path)
            if annotated_video_path
            else None,
            "timing": stage_timings,
        }

        logger.info(f"Analysis complete: {analysis_summary}")
        log_timing("Video Analysis", start_time)
        return results

    def _create_annotated_video(
        self, original_video_path: Path, annotated_frames: List[np.ndarray]
    ) -> Optional[Path]:
        """
        Create annotated video with pose and ball overlays.

        Args:
            original_video_path: Path to original video
            annotated_frames: List of frames with overlays

        Returns:
            Path to annotated video file
        """
        start_time = time.time()
        if not annotated_frames:
            logger.warning("No annotated frames provided, skipping video creation")
            return None

        try:
            # Get video properties from original video
            cap = cv2.VideoCapture(str(original_video_path))
            if not cap.isOpened():
                logger.error(f"Could not open original video: {original_video_path}")
                return None

            fps = cap.get(cv2.CAP_PROP_FPS)
            width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
            height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
            cap.release()

            # Validate FPS - use fallback if invalid
            if fps <= 0 or fps > 120:  # Reasonable FPS range
                logger.warning(f"Invalid FPS detected: {fps}, using fallback of 30 fps")
                fps = 30.0

            logger.info(f"Video properties: {width}x{height}, {fps} fps")

            # Create output path using settings
            from app.core.config import settings

            output_dir = Path(settings.PROCESSED_DIR)
            output_dir.mkdir(parents=True, exist_ok=True)
            logger.info(f"Output directory: {output_dir.absolute()}")

            original_name = original_video_path.stem
            annotated_path = output_dir / f"{original_name}_annotated.mp4"
            logger.info(f"Annotated video path: {annotated_path.absolute()}")

            # Check if file already exists and is valid
            if annotated_path.exists():
                file_size = annotated_path.stat().st_size
                if file_size > 0:
                    logger.info(
                        f"Annotated video already exists: {annotated_path} ({file_size} bytes)"
                    )
                    return annotated_path
                else:
                    logger.warning(
                        f"Existing annotated video is empty, recreating: {annotated_path}"
                    )
                    annotated_path.unlink()

            # Create video writer with any working codec first, then convert to H.264
            # No audio track - we don't need sound for analysis videos
            # Try different codecs in order of preference
            codecs_to_try = ["mp4v", "XVID", "MJPG"]  # Use any working codec
            out = None

            for codec in codecs_to_try:
                try:
                    fourcc = cv2.VideoWriter_fourcc(*codec)
                    out = cv2.VideoWriter(
                        str(annotated_path), fourcc, fps, (width, height)
                    )
                    if out.isOpened():
                        logger.info(
                            f"Successfully created video writer with codec: {codec}"
                        )
                        break
                    else:
                        out.release()
                        out = None
                except (OSError, RuntimeError, ValueError) as e:
                    logger.warning(
                        f"Failed to create video writer with codec {codec}: {e}"
                    )
                    if out:
                        out.release()
                        out = None

            if not out or not out.isOpened():
                logger.error(
                    f"Could not create video writer for: {annotated_path} with any available codec"
                )
                return None

            # Write frames
            frames_written = 0
            for frame in annotated_frames:
                # Resize frame if needed
                if frame.shape[:2] != (height, width):
                    frame = cv2.resize(frame, (width, height))
                out.write(frame)
                frames_written += 1

            out.release()
            logger.info(
                f"Successfully created annotated video: {annotated_path} ({frames_written} frames)"
            )

            # Verify the file was created and has content
            if not annotated_path.exists():
                logger.error(f"Annotated video file was not created: {annotated_path}")
                return None

            file_size = annotated_path.stat().st_size
            if file_size == 0:
                logger.error(f"Annotated video file is empty: {annotated_path}")
                annotated_path.unlink()
                return None

            logger.info(
                f"Annotated video file created successfully: {annotated_path} ({file_size} bytes)"
            )

            # Convert to H.264 for better browser compatibility using FFmpeg
            import subprocess
            import uuid

            temp_path = None
            conversion_successful = False

            try:
                # Create a unique temporary filename to avoid conflicts
                unique_suffix = str(uuid.uuid4())[:8]
                temp_path = annotated_path.with_suffix(f".temp_{unique_suffix}.mp4")

                # Safely rename original file to temporary name
                # Remove temp file if it somehow already exists
                if temp_path.exists():
                    temp_path.unlink()
                annotated_path.rename(temp_path)

                # Use FFmpeg to convert to H.264
                # Note: FFmpeg is installed in Docker container and required for local development
                cmd = [
                    "ffmpeg",
                    "-y",  # Overwrite output
                    "-i",
                    str(temp_path),  # Input file
                    "-c:v",
                    "libx264",  # Use H.264 codec
                    "-preset",
                    "fast",  # Fast encoding
                    "-crf",
                    "23",  # Good quality
                    "-pix_fmt",
                    "yuv420p",  # Pixel format for browser compatibility
                    str(annotated_path),  # Output file
                ]

                logger.info(f"Running FFmpeg conversion: {' '.join(cmd)}")
                result = subprocess.run(cmd, capture_output=True, text=True)  # noqa: S603

                if result.returncode == 0:
                    logger.info(f"Successfully converted to H.264: {annotated_path}")
                    conversion_successful = True
                    # Try to remove temp file - if this fails, don't rollback
                    try:
                        temp_path.unlink()
                        temp_path = None  # Mark as cleaned up
                    except OSError as cleanup_error:
                        logger.warning(
                            f"Failed to clean up temp file {temp_path}: {cleanup_error}"
                        )
                        # Don't rollback - conversion was successful
                else:
                    logger.warning(f"FFmpeg conversion failed: {result.stderr}")
                    logger.warning(f"FFmpeg stdout: {result.stdout}")
                    # Fallback: restore original file
                    self._safe_restore_file(temp_path, annotated_path)

            except subprocess.SubprocessError as e:
                logger.warning(f"FFmpeg subprocess error: {e}")
                if temp_path and not conversion_successful:
                    self._safe_restore_file(temp_path, annotated_path)
            except (OSError, RuntimeError, ValueError) as e:
                logger.warning(f"Failed to convert to H.264: {e}")
                if temp_path and not conversion_successful:
                    self._safe_restore_file(temp_path, annotated_path)

            # Final verification
            if annotated_path.exists():
                final_size = annotated_path.stat().st_size
                logger.info(
                    f"Final annotated video: {annotated_path} ({final_size} bytes)"
                )
                if final_size > 0:
                    log_timing("Video Creation", start_time)
                    return annotated_path
                else:
                    logger.error(f"Final annotated video is empty: {annotated_path}")
                    annotated_path.unlink()
                    return None
            else:
                logger.error(f"Final annotated video does not exist: {annotated_path}")
                return None

        except (OSError, RuntimeError, ValueError) as e:
            logger.error(f"Error creating annotated video: {e}")
            import traceback

            logger.error(f"Traceback: {traceback.format_exc()}")
            return None

    def get_video_metadata(self, video_path: Path) -> Dict[str, Any]:
        """
        Extract basic video metadata.

        Args:
            video_path: Path to video file

        Returns:
            Video metadata dictionary
        """
        try:
            cap = cv2.VideoCapture(str(video_path))
            if not cap.isOpened():
                return {"error": "Could not open video file"}

            metadata = {
                "width": int(cap.get(cv2.CAP_PROP_FRAME_WIDTH)),
                "height": int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT)),
                "fps": float(cap.get(cv2.CAP_PROP_FPS)),
                "frame_count": int(cap.get(cv2.CAP_PROP_FRAME_COUNT)),
                "duration": float(cap.get(cv2.CAP_PROP_FRAME_COUNT))
                / float(cap.get(cv2.CAP_PROP_FPS)),
                "codec": int(cap.get(cv2.CAP_PROP_FOURCC)),
            }

            cap.release()
            return metadata

        except (OSError, RuntimeError, ValueError) as e:
            logger.error(f"Error extracting video metadata: {e}")
            return {"error": str(e)}


def assess_video_quality(frames: List[np.ndarray]) -> Dict[str, Any]:
    """
    Assess video quality and return quality metrics and recommended confidence thresholds.

    Args:
        frames: List of video frames to analyze

    Returns:
        Dictionary containing quality metrics and recommended thresholds
    """
    if not frames:
        return {
            "quality_score": 0.0,
            "blur_score": 0.0,
            "lighting_score": 0.0,
            "resolution_score": 0.0,
            "recommended_confidence_threshold": settings.BALL_CONFIDENCE_THRESHOLD,
            "quality_level": "unknown",
        }

    # Sample frames for analysis (use every 10th frame to avoid performance issues)
    sample_frames = frames[::10] if len(frames) > 10 else frames

    # Calculate blur score using Laplacian variance
    blur_scores = []
    for frame in sample_frames:
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
    for frame in sample_frames:
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
    quality_score = blur_quality * 0.4 + lighting_quality * 0.4 + resolution_score * 0.2

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

    logger.info(
        f"Video quality assessment: {quality_level} (score: {quality_score:.2f})"
    )
    logger.info(
        f"  Blur: {blur_quality:.2f}, Lighting: {lighting_quality:.2f}, Resolution: {resolution_score:.2f}"
    )
    logger.info(f"  Recommended confidence threshold: {recommended_threshold:.2f}")

    return {
        "quality_score": float(quality_score),
        "blur_score": float(blur_quality),
        "lighting_score": float(lighting_quality),
        "resolution_score": float(resolution_score),
        "recommended_confidence_threshold": float(recommended_threshold),
        "quality_level": quality_level,
        "frame_count_analyzed": len(sample_frames),
    }


# Global CV service instance
cv_service = CVService()
