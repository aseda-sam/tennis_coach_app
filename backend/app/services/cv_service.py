"""
Computer Vision Service for tennis video analysis.
Handles video processing, ball detection, and player tracking.
"""

import logging
from pathlib import Path
from typing import Any, Dict, List, Optional, Sequence, Tuple

import cv2
import numpy as np

logger = logging.getLogger(__name__)


class CVService:
    """Computer Vision service for tennis video analysis."""

    def __init__(self) -> None:
        """Initialize the CV service."""
        self.ball_detector = None
        self.pose_detector = None
        self._initialize_models()

    def _initialize_models(self) -> None:
        """Initialize YOLO and MediaPipe models."""
        try:
            # Initialize YOLO for ball detection
            from ultralytics import YOLO

            self.ball_detector = YOLO("yolov8n.pt")  # Use nano model for speed
            logger.info("YOLO model initialized successfully")
        except ImportError:
            logger.warning("Ultralytics not available, ball detection disabled")
            self.ball_detector = None
        except (OSError, RuntimeError) as e:
            logger.error(f"Failed to initialize YOLO: {e}")
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
        frames = []
        try:
            cap = cv2.VideoCapture(str(video_path))
            if not cap.isOpened():
                logger.error(f"Could not open video: {video_path}")
                return frames

            frame_count = 0
            total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
            fps = cap.get(cv2.CAP_PROP_FPS)

            # Calculate frame interval to get max_frames (or process all frames if max_frames is None)
            if max_frames is None:
                interval = 1  # Process every frame
            else:
                interval = (
                    total_frames // max_frames if total_frames > max_frames else 1
                )

            logger.info(f"Extracting frames from {video_path}")
            logger.info(
                f"Total frames: {total_frames}, FPS: {fps}, Interval: {interval}"
            )

            # Process all frames if max_frames is None, otherwise limit to max_frames
            max_frames_to_process = (
                max_frames if max_frames is not None else total_frames
            )
            while frame_count < max_frames_to_process:
                ret, frame = cap.read()
                if not ret:
                    break

                # Only keep frames at interval
                if frame_count % interval == 0:
                    frames.append(frame)

                frame_count += 1

                # Skip frames to maintain interval
                if interval > 1:
                    for _ in range(interval - 1):
                        cap.read()

            cap.release()
            logger.info(f"Extracted {len(frames)} frames")

        except (OSError, RuntimeError, ValueError) as e:
            logger.error(f"Error extracting frames: {e}")

        return frames

    def detect_balls(self, frames: List[np.ndarray]) -> List[List[Dict[str, Any]]]:
        """
        Detect tennis balls in frames using YOLO.

        Args:
            frames: List of frame arrays

        Returns:
            List of detections per frame
        """
        if not self.ball_detector:
            logger.warning("Ball detector not available")
            return [[] for _ in frames]

        detections = []
        try:
            for i, frame in enumerate(frames):
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
                            if class_id == 32 and confidence > 0.5:
                                frame_detections.append(
                                    {
                                        "bbox": [int(x1), int(y1), int(x2), int(y2)],
                                        "confidence": float(confidence),
                                        "class_id": class_id,
                                        "frame_index": i,
                                    }
                                )

                detections.append(frame_detections)
                logger.debug(f"Frame {i}: {len(frame_detections)} ball detections")

            total_detections = sum(len(d) for d in detections)
            logger.info(f"Total ball detections: {total_detections}")

        except (RuntimeError, ValueError, OSError) as e:
            logger.error(f"Error in ball detection: {e}")
            detections = [[] for _ in frames]

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

    def analyze_video(
        self, video_path: Path, include_pose: bool = True
    ) -> Dict[str, Any]:
        """
        Perform comprehensive video analysis with ball detection and pose estimation.

        Args:
            video_path: Path to video file
            include_pose: Whether to include pose detection (default: True)

        Returns:
            Analysis results dictionary
        """
        logger.info(
            f"Starting analysis of {video_path} (pose detection: {include_pose})"
        )

        # Extract frames
        frames = self.extract_frames(video_path)
        if not frames:
            return {
                "error": "Failed to extract frames from video",
                "frames_processed": 0,
                "ball_detections": [],
                "pose_detections": [],
                "analysis_summary": {},
            }

        # Detect balls
        ball_detections = self.detect_balls(frames)

        # Detect poses (if enabled)
        pose_detections = []
        annotated_frames = []

        if include_pose and self.pose_detector:
            logger.info("Starting pose detection...")
            logger.info(f"Processing {len(frames)} frames for pose detection")
            for i, frame in enumerate(frames):
                pose_keypoints = self.detect_pose(frame)
                pose_detections.append(pose_keypoints)

                # Log every 10th frame for debugging
                if i % 10 == 0:
                    frame_shape = frame.shape
                    logger.info(
                        f"Frame {i}: shape={frame_shape}, pose_detected={pose_keypoints is not None}"
                    )

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
            annotated_video_path = self._create_annotated_video(
                video_path, annotated_frames
            )
            if annotated_video_path:
                logger.info(
                    f"Successfully created annotated video: {annotated_video_path}"
                )
            else:
                logger.warning("Failed to create annotated video")
        else:
            logger.info("No poses detected, skipping annotated video creation")

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
        }

        results = {
            "frames_processed": len(frames),
            "ball_detections": ball_detections,
            "pose_detections": pose_detections,
            "analysis_summary": analysis_summary,
            "video_path": str(video_path),
            "annotated_video_path": str(annotated_video_path)
            if annotated_video_path
            else None,
        }

        logger.info(f"Analysis complete: {analysis_summary}")
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
        if not annotated_frames:
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

            logger.info(f"Video properties: {width}x{height}, {fps} fps")

            # Create output path (use main data directory)
            output_dir = Path("../data/videos/processed")
            output_dir.mkdir(parents=True, exist_ok=True)
            logger.info(f"Output directory: {output_dir.absolute()}")

            original_name = original_video_path.stem
            annotated_path = output_dir / f"{original_name}_annotated.mp4"
            logger.info(f"Annotated video path: {annotated_path.absolute()}")

            # Create video writer with H.264 codec for better browser compatibility
            # No audio track - we don't need sound for analysis videos
            fourcc = cv2.VideoWriter_fourcc(*"avc1")
            out = cv2.VideoWriter(str(annotated_path), fourcc, fps, (width, height))

            if not out.isOpened():
                logger.error(f"Could not create video writer for: {annotated_path}")
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
            return annotated_path

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


# Global CV service instance
cv_service = CVService()
