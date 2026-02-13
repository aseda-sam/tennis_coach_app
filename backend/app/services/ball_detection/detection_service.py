"""
Ball detection service using YOLO (Ultralytics) for tennis ball tracking.

Uses COCO pre-trained model with class 32 ("sports ball") for MVP.
Processes only specified time windows (e.g. serve windows) to keep runtime low.
"""

import logging
import time
from pathlib import Path
from typing import TYPE_CHECKING, Any, Dict, List

import cv2
import numpy as np

from app.utils.video_utils import get_video_rotation

if TYPE_CHECKING:
    from ultralytics import YOLO

logger = logging.getLogger(__name__)

# COCO class index for "sports ball"
COCO_SPORTS_BALL_CLASS = 32

# Default confidence threshold for ball detection
DEFAULT_CONFIDENCE = 0.25


def _rotate_frame(frame: np.ndarray, rotation: int) -> np.ndarray:
    """Rotate frame to match display orientation (same logic as pose detection)."""
    if rotation == -90 or rotation == 270:
        return cv2.rotate(frame, cv2.ROTATE_90_CLOCKWISE)
    if rotation == 90 or rotation == -270:
        return cv2.rotate(frame, cv2.ROTATE_90_COUNTERCLOCKWISE)
    if rotation == 180 or rotation == -180:
        return cv2.rotate(frame, cv2.ROTATE_180)
    return frame


class BallDetectionService:
    """Service for detecting tennis balls in video using YOLO."""

    def __init__(self) -> None:
        self._model = None
        self._logger = logger

    def _get_model(self) -> "YOLO":
        """Lazy-load YOLO model (yolo11n.pt, auto-downloads on first use)."""
        if self._model is None:
            try:
                from ultralytics import YOLO

                self._model = YOLO("yolo11n.pt")
                self._logger.info("Ball detection model (yolo11n) loaded")
            except ImportError as e:
                self._logger.error("ultralytics not installed: %s", e)
                raise
        return self._model

    def analyze_serve_windows(
        self,
        video_path: Path,
        windows: List[Dict[str, float]],
        padding_ms: float = 300,
        confidence: float = DEFAULT_CONFIDENCE,
    ) -> Dict[str, Any]:
        """
        Run ball detection only within the given time windows.

        Args:
            video_path: Path to video file
            windows: List of dicts with start_ms and end_ms
            padding_ms: Padding before/after each window (milliseconds)
            confidence: Minimum detection confidence (0-1)

        Returns:
            Dict with ball_detections (list of per-frame results), total_frames,
            frames_with_ball, detection_rate, processing_time_seconds, etc.
        """
        start_time = time.time()
        self._logger.info(
            "Starting ball detection for %s windows in: %s", len(windows), video_path
        )

        try:
            model = self._get_model()
        except ImportError:
            return self._error_result(start_time, "Ball detection model not available")

        cap = cv2.VideoCapture(str(video_path))
        if not cap.isOpened():
            return self._error_result(start_time, "Could not open video file")

        fps = cap.get(cv2.CAP_PROP_FPS) or 30.0
        total_video_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
        cap.release()

        rotation = get_video_rotation(video_path)
        if rotation != 0:
            self._logger.info(
                "Applying rotation=%d to frames from %s", rotation, video_path
            )

        ball_detections: List[Dict[str, Any]] = []
        frames_with_ball = 0
        total_frames = 0

        for window in windows:
            start_ms = window.get("start_ms", 0.0)
            end_ms = window.get("end_ms", 0.0)
            padded_start_ms = max(0, start_ms - padding_ms)
            padded_end_ms = min(
                (total_video_frames / fps * 1000) if fps > 0 else end_ms + padding_ms,
                end_ms + padding_ms,
            )
            start_frame = int(padded_start_ms * fps / 1000.0) if fps > 0 else 0
            end_frame = min(
                int(padded_end_ms * fps / 1000.0) if fps > 0 else total_video_frames,
                total_video_frames,
            )

            cap = cv2.VideoCapture(str(video_path))
            if not cap.isOpened():
                continue
            cap.set(cv2.CAP_PROP_ORIENTATION_AUTO, 0)
            cap.set(cv2.CAP_PROP_POS_FRAMES, start_frame)

            frame_index = start_frame
            while frame_index <= end_frame and frame_index < total_video_frames:
                ret, frame = cap.read()
                if not ret:
                    break

                total_frames += 1
                timestamp_ms = (frame_index * 1000.0 / fps) if fps > 0 else 0.0

                if rotation != 0:
                    frame = _rotate_frame(frame, rotation)

                # YOLO expects BGR; OpenCV gives BGR
                results = model.predict(
                    frame,
                    classes=[COCO_SPORTS_BALL_CLASS],
                    conf=confidence,
                    verbose=False,
                )

                det = None
                if results and len(results) > 0:
                    boxes = results[0].boxes
                    if boxes is not None and len(boxes) > 0:
                        # Take highest-confidence detection
                        best = 0
                        for i in range(len(boxes)):
                            if boxes.conf[i].item() > boxes.conf[best].item():
                                best = i
                        x1, y1, x2, y2 = boxes.xyxy[best].tolist()
                        conf_val = boxes.conf[best].item()
                        center_x = (x1 + x2) / 2.0
                        center_y = (y1 + y2) / 2.0
                        det = {
                            "frame_index": frame_index,
                            "timestamp_ms": timestamp_ms,
                            "ball_x": center_x,
                            "ball_y": center_y,
                            "confidence": conf_val,
                        }
                        frames_with_ball += 1

                if det is None:
                    ball_detections.append(
                        {
                            "frame_index": frame_index,
                            "timestamp_ms": timestamp_ms,
                            "ball_x": None,
                            "ball_y": None,
                            "confidence": None,
                        }
                    )
                else:
                    ball_detections.append(det)

                frame_index += 1

            cap.release()

        processing_time = time.time() - start_time
        self._logger.info(
            "Ball detection complete: %s/%s frames with ball in %.2fs",
            frames_with_ball,
            total_frames,
            processing_time,
        )

        return {
            "ball_detections": ball_detections,
            "total_frames": total_frames,
            "frames_with_ball": frames_with_ball,
            "detection_rate": frames_with_ball / total_frames if total_frames else 0.0,
            "processing_time_seconds": processing_time,
            "frame_processing_rate": total_frames / processing_time
            if processing_time > 0
            else 0.0,
            "status": "completed",
            "video_path": str(video_path),
        }

    def _error_result(self, start_time: float, error: str) -> Dict[str, Any]:
        return {
            "error": error,
            "ball_detections": [],
            "total_frames": 0,
            "frames_with_ball": 0,
            "detection_rate": 0.0,
            "processing_time_seconds": time.time() - start_time,
            "frame_processing_rate": 0.0,
            "status": "failed",
        }
