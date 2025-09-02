"""
Ball detection service for tennis video analysis.

This service handles tennis ball detection using YOLO models,
providing independent ball detection functionality.
"""

import json
import logging
import time
from pathlib import Path
from typing import Any, Dict, List, Optional

import numpy as np
from sqlalchemy.orm import Session

from app.core.config import settings
from app.models.ball_detection import BallDetection

logger = logging.getLogger(__name__)


class BallDetectionService:
    """Service for detecting tennis balls in videos using YOLO models."""

    def __init__(self) -> None:
        """Initialize the ball detection service."""
        self.yolo_models = {}
        self.logger = logger
        self._initialize_yolo_models()

    def _initialize_yolo_models(self) -> None:
        """Initialize YOLO models for ball detection."""
        start_time = time.time()
        self.yolo_models = {}

        try:
            from ultralytics import YOLO

            # Try to initialize models one by one to handle partial failures
            models_to_try = [
                (model_name, model_path)
                for model_name, model_path in settings.YOLO_MODELS.items()
            ]

            for model_name, model_path in models_to_try:
                try:
                    self.logger.info(f"Loading YOLO model: {model_name} ({model_path})")
                    self.yolo_models[model_name] = YOLO(model_path)
                    self.logger.info(f"Successfully loaded YOLO model: {model_name}")
                except (OSError, RuntimeError, ImportError) as e:
                    self.logger.warning(f"Failed to load YOLO model {model_name}: {e}")
                    continue

            if self.yolo_models:
                self.logger.info(
                    f"Loaded {len(self.yolo_models)} YOLO models successfully"
                )
            else:
                self.logger.error("No YOLO models could be loaded")

        except ImportError as e:
            self.logger.error(f"Failed to import ultralytics: {e}")
        except (OSError, RuntimeError) as e:
            self.logger.error(f"Unexpected error during model initialization: {e}")

        elapsed_time = time.time() - start_time
        self.logger.info(f"YOLO model initialization completed in {elapsed_time:.3f}s")

    def _select_yolo_model(self, video_quality_level: Optional[str] = None) -> str:
        """
        Select appropriate YOLO model based on video quality.

        Args:
            video_quality_level: Quality level from video assessment

        Returns:
            Selected model name
        """
        if not self.yolo_models:
            raise RuntimeError("No YOLO models available for ball detection")

        if not video_quality_level or video_quality_level == "unknown":
            # Return the first available model (prefer nano if available)
            preferred_order = ["nano", "small", "medium", "large"]
            for model_type in preferred_order:
                if model_type in self.yolo_models:
                    return model_type
            return next(iter(self.yolo_models.keys()))

        # Model selection logic based on quality
        quality_model_mapping = {
            "excellent": "small",  # Use better model for excellent quality
            "good": "small",  # Use better model for good quality
            "fair": "nano",  # Use faster model for fair quality
            "poor": "nano",  # Use faster model for poor quality
        }

        preferred_model = quality_model_mapping.get(video_quality_level, "nano")

        # Return preferred model if available, otherwise first available
        if preferred_model in self.yolo_models:
            return preferred_model
        return next(iter(self.yolo_models.keys()))

    def detect_balls_in_frames(
        self,
        frames: List[np.ndarray],
        confidence_threshold: Optional[float] = None,
        video_quality_level: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Detect tennis balls in video frames.

        Args:
            frames: List of video frames
            confidence_threshold: Confidence threshold for detections
            video_quality_level: Video quality level for model selection

        Returns:
            Dictionary containing detection results and metadata
        """
        if not frames:
            return self._get_empty_detection_result()

        start_time = time.time()

        # Set confidence threshold
        if confidence_threshold is None:
            confidence_threshold = settings.BALL_CONFIDENCE_THRESHOLD

        # Select YOLO model based on video quality
        selected_model = self._select_yolo_model(video_quality_level)

        if selected_model not in self.yolo_models:
            raise RuntimeError(f"Selected YOLO model '{selected_model}' not available")

        ball_detector = self.yolo_models[selected_model]
        self.logger.info(
            f"Using YOLO model: {selected_model} (quality: {video_quality_level or 'unknown'})"
        )

        # Perform ball detection
        all_detections = []
        confidence_scores = []
        frames_with_balls = 0
        total_detections = 0

        for i, frame in enumerate(frames):
            try:
                # Run YOLO detection
                results = ball_detector(frame, verbose=False)

                frame_detections = []
                for result in results:
                    boxes = result.boxes
                    if boxes is not None:
                        for box in boxes:
                            confidence = float(box.conf.cpu().numpy())
                            if confidence >= confidence_threshold:
                                # Get bounding box coordinates
                                bbox = box.xyxy.cpu().numpy().flatten()

                                detection = {
                                    "bbox": [
                                        float(bbox[0]),
                                        float(bbox[1]),
                                        float(bbox[2]),
                                        float(bbox[3]),
                                    ],
                                    "confidence": confidence,
                                    "frame_index": i,
                                }
                                frame_detections.append(detection)
                                confidence_scores.append(confidence)
                                total_detections += 1

                if frame_detections:
                    frames_with_balls += 1

                all_detections.append(frame_detections)

            except (RuntimeError, ValueError) as e:
                self.logger.warning(f"Error processing frame {i}: {e}")
                all_detections.append([])

        processing_time = time.time() - start_time

        # Calculate statistics
        detection_rate = frames_with_balls / len(frames) if frames else 0
        avg_detections_per_frame = total_detections / len(frames) if frames else 0
        frame_processing_rate = (
            len(frames) / processing_time if processing_time > 0 else 0
        )

        # Calculate confidence statistics
        confidence_stats = {}
        if confidence_scores:
            confidence_stats = {
                "average": float(np.mean(confidence_scores)),
                "min": float(np.min(confidence_scores)),
                "max": float(np.max(confidence_scores)),
                "std": float(np.std(confidence_scores)),
            }

        result = {
            "total_frames": len(frames),
            "frames_with_balls": frames_with_balls,
            "total_detections": total_detections,
            "detection_rate": detection_rate,
            "average_detections_per_frame": avg_detections_per_frame,
            "processing_time_seconds": processing_time,
            "frame_processing_rate": frame_processing_rate,
            "model_used": selected_model,
            "confidence_threshold": confidence_threshold,
            "model_selection_reason": f"Quality-based selection: {video_quality_level or 'unknown'} quality",
            "detection_data": all_detections,
            "confidence_stats": confidence_stats,
        }

        self.logger.info(
            f"Ball detection completed: {frames_with_balls}/{len(frames)} frames with balls "
            f"({detection_rate:.1%} detection rate), {total_detections} total detections, "
            f"model: {selected_model}, processing: {processing_time:.2f}s"
        )

        return result

    def analyze_video_file(
        self,
        video_path: Path,
        confidence_threshold: Optional[float] = None,
        video_quality_level: Optional[str] = None,
        max_frames: Optional[int] = None,
    ) -> Dict[str, Any]:
        """
        Analyze video file for ball detection.

        Args:
            video_path: Path to video file
            confidence_threshold: Confidence threshold for detections
            video_quality_level: Video quality level for model selection
            max_frames: Maximum number of frames to process

        Returns:
            Dictionary containing detection results
        """
        # Extract frames from video
        frames = self._extract_frames(video_path, max_frames)

        if not frames:
            self.logger.warning(f"No frames extracted from {video_path}")
            return self._get_empty_detection_result()

        # Perform ball detection on frames
        return self.detect_balls_in_frames(
            frames, confidence_threshold, video_quality_level
        )

    def save_detection_results(
        self, db: Session, video_id: int, detection_results: Dict[str, Any]
    ) -> BallDetection:
        """
        Save ball detection results to database.

        Args:
            db: Database session
            video_id: ID of the video
            detection_results: Detection results from detect_balls_in_frames

        Returns:
            Created BallDetection record
        """
        # Create BallDetection record
        ball_detection = BallDetection(
            video_id=video_id,
            total_frames=detection_results["total_frames"],
            frames_with_balls=detection_results["frames_with_balls"],
            total_ball_detections=detection_results["total_detections"],
            average_detections_per_frame=detection_results[
                "average_detections_per_frame"
            ],
            detection_rate=detection_results["detection_rate"],
            model_used=detection_results["model_used"],
            confidence_threshold=detection_results["confidence_threshold"],
            model_selection_reason=detection_results["model_selection_reason"],
            detection_data=json.dumps(detection_results["detection_data"]),
            confidence_scores=json.dumps(detection_results["confidence_stats"]),
            processing_time_seconds=detection_results["processing_time_seconds"],
            frame_processing_rate=detection_results["frame_processing_rate"],
            status="completed",
        )

        # Set confidence statistics if available
        if detection_results.get("confidence_stats"):
            stats = detection_results["confidence_stats"]
            ball_detection.average_confidence = stats.get("average")
            ball_detection.min_confidence = stats.get("min")
            ball_detection.max_confidence = stats.get("max")

        # Set completion timestamp
        from sqlalchemy.sql import func

        ball_detection.completed_at = func.now()

        # Save to database
        db.add(ball_detection)
        db.commit()
        db.refresh(ball_detection)

        self.logger.info(
            f"Saved ball detection results for video {video_id} (detection_id: {ball_detection.id})"
        )
        return ball_detection

    def get_detection_by_video_id(
        self, db: Session, video_id: int
    ) -> Optional[BallDetection]:
        """
        Get ball detection results for a video.

        Args:
            db: Database session
            video_id: ID of the video

        Returns:
            BallDetection record if found, None otherwise
        """
        return (
            db.query(BallDetection).filter(BallDetection.video_id == video_id).first()
        )

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
        import cv2

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

            # Calculate frame interval if max_frames is specified
            frame_interval = 1
            if max_frames and total_frames > max_frames:
                frame_interval = max(1, total_frames // max_frames)

            frame_count = 0
            extracted_count = 0

            while True:
                ret, frame = cap.read()
                if not ret:
                    break

                # Extract frame at interval
                if frame_count % frame_interval == 0:
                    frames.append(frame)
                    extracted_count += 1

                    # Stop if we've reached max_frames
                    if max_frames and extracted_count >= max_frames:
                        break

                frame_count += 1

            cap.release()
            self.logger.info(
                f"Extracted {len(frames)} frames from {total_frames} total frames"
            )

        except (OSError, RuntimeError) as e:
            self.logger.error(f"Error extracting frames from {video_path}: {e}")

        return frames

    def _get_empty_detection_result(self) -> Dict[str, Any]:
        """
        Get empty detection result for error cases.

        Returns:
            Empty detection result dictionary
        """
        return {
            "total_frames": 0,
            "frames_with_balls": 0,
            "total_detections": 0,
            "detection_rate": 0.0,
            "average_detections_per_frame": 0.0,
            "processing_time_seconds": 0.0,
            "frame_processing_rate": 0.0,
            "model_used": "none",
            "confidence_threshold": settings.BALL_CONFIDENCE_THRESHOLD,
            "model_selection_reason": "No frames to process",
            "detection_data": [],
            "confidence_stats": {},
        }
