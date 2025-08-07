"""
Computer Vision Service for tennis video analysis.
Handles video processing, ball detection, and player tracking.
"""

import logging
from pathlib import Path
from typing import Any, Dict, List

import cv2
import numpy as np

logger = logging.getLogger(__name__)


class CVService:
    """Computer Vision service for tennis video analysis."""

    def __init__(self):
        """Initialize the CV service."""
        self.ball_detector = None
        self.pose_detector = None
        self._initialize_models()

    def _initialize_models(self) -> None:
        """Initialize YOLO and other CV models."""
        try:
            # Initialize YOLO for ball detection
            from ultralytics import YOLO

            self.ball_detector = YOLO("yolov8n.pt")  # Use nano model for speed
            logger.info("YOLO model initialized successfully")
        except ImportError:
            logger.warning("Ultralytics not available, ball detection disabled")
            self.ball_detector = None
        except Exception as e:
            logger.error(f"Failed to initialize YOLO: {e}")
            self.ball_detector = None

    def extract_frames(
        self, video_path: Path, max_frames: int = 100
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
            total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
            fps = cap.get(cv2.CAP_PROP_FPS)

            # Calculate frame interval to get max_frames
            if total_frames > max_frames:
                interval = total_frames // max_frames
            else:
                interval = 1

            logger.info(f"Extracting frames from {video_path}")
            logger.info(
                f"Total frames: {total_frames}, FPS: {fps}, Interval: {interval}"
            )

            while frame_count < max_frames:
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

        except Exception as e:
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

        except Exception as e:
            logger.error(f"Error in ball detection: {e}")
            detections = [[] for _ in frames]

        return detections

    def analyze_video(self, video_path: Path) -> Dict[str, Any]:
        """
        Perform comprehensive video analysis.

        Args:
            video_path: Path to video file

        Returns:
            Analysis results dictionary
        """
        logger.info(f"Starting analysis of {video_path}")

        # Extract frames
        frames = self.extract_frames(video_path)
        if not frames:
            return {
                "error": "Failed to extract frames from video",
                "frames_processed": 0,
                "ball_detections": [],
                "analysis_summary": {},
            }

        # Detect balls
        ball_detections = self.detect_balls(frames)

        # Calculate analysis summary
        total_detections = sum(len(d) for d in ball_detections)
        frames_with_balls = sum(1 for d in ball_detections if d)

        analysis_summary = {
            "total_frames": len(frames),
            "frames_with_balls": frames_with_balls,
            "total_ball_detections": total_detections,
            "average_detections_per_frame": total_detections / len(frames)
            if frames
            else 0,
            "detection_rate": frames_with_balls / len(frames) if frames else 0,
        }

        results = {
            "frames_processed": len(frames),
            "ball_detections": ball_detections,
            "analysis_summary": analysis_summary,
            "video_path": str(video_path),
        }

        logger.info(f"Analysis complete: {analysis_summary}")
        return results

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

        except Exception as e:
            logger.error(f"Error extracting video metadata: {e}")
            return {"error": str(e)}


# Global CV service instance
cv_service = CVService()
