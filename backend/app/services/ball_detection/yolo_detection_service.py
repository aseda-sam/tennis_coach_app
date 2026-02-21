"""Ball detection service using fine-tuned YOLOv8 + ByteTrack for tennis ball tracking.

Replaces TrackNetV2 for our use case (close-up portrait phone footage where the
ball is 20-100+ px). Public interface is identical to TrackNetBallDetectionService
so rq_tasks.py requires only a one-line import swap.

Internal flow per window:
  1. Iterate frames individually (no triplet stacking needed)
  2. Run YOLO inference → sv.Detections → ByteTrack tracker assigns track IDs
  3. After all frames: select the track with highest total displacement (= moving ball)
  4. Build output dicts using only positions from the selected track
  5. After all windows: apply TrajectorySmoother (velocity filter + spline interpolation)
"""

from __future__ import annotations

import logging
import math
import time
from pathlib import Path
from typing import Any, Dict, List, Optional

import cv2
import numpy as np

try:
    import supervision as sv
except ImportError:
    sv = None  # type: ignore[assignment]

from app.core.config import settings
from app.services.ball_detection.trajectory_smoother import TrajectorySmoother
from app.utils.video_utils import get_video_rotation

logger = logging.getLogger(__name__)

DEFAULT_CONFIDENCE: float = 0.25

# Class index for "sports ball" in COCO (used by base YOLOv8).
# Fine-tuned models typically have class 0 = "tennis-ball".
COCO_SPORTS_BALL_CLASS: int = 32
FINE_TUNED_BALL_CLASS: int = 0


def _rotate_frame(frame: np.ndarray, rotation: int) -> np.ndarray:
    """Rotate frame to match display orientation (same logic as pose detection)."""
    if rotation in (-90, 270):
        return cv2.rotate(frame, cv2.ROTATE_90_CLOCKWISE)
    if rotation in (90, -270):
        return cv2.rotate(frame, cv2.ROTATE_90_COUNTERCLOCKWISE)
    if rotation in (180, -180):
        return cv2.rotate(frame, cv2.ROTATE_180)
    return frame


def _select_ball_track(
    tracked_frames: List[tuple],
) -> Optional[int]:
    """Pick the track ID with the highest total displacement (= moving ball).

    Static background objects (court balls, lights) get tracks with near-zero
    displacement. The tossed ball gets a track with high displacement across frames.

    Args:
        tracked_frames: List of (frame_index, timestamp_ms, sv.Detections) tuples.

    Returns:
        The track ID of the most-moving object, or None if no tracks found.
    """
    track_positions: dict[int, list[tuple[float, float]]] = {}

    for _idx, _ts, tracked in tracked_frames:
        if tracked.tracker_id is None:
            continue
        for i, tid in enumerate(tracked.tracker_id):
            bbox = tracked.xyxy[i]
            cx = float((bbox[0] + bbox[2]) / 2.0)
            cy = float((bbox[1] + bbox[3]) / 2.0)
            track_positions.setdefault(int(tid), []).append((cx, cy))

    best_id: Optional[int] = None
    best_disp = 0.0
    for tid, positions in track_positions.items():
        total_disp = sum(
            math.hypot(
                positions[i + 1][0] - positions[i][0],
                positions[i + 1][1] - positions[i][1],
            )
            for i in range(len(positions) - 1)
        )
        if total_disp > best_disp:
            best_id, best_disp = tid, total_disp

    return best_id


class YoloBallDetectionService:
    """Detect tennis balls in video using fine-tuned YOLOv8 + ByteTrack."""

    def __init__(self) -> None:
        self._model: Optional[object] = None
        self._ball_class: int = FINE_TUNED_BALL_CLASS
        self._logger = logger

    def _get_model(self) -> object:
        """Lazy-load YOLO model from ml_models/yolo_tennis_ball.pt."""
        if self._model is None:
            try:
                from ultralytics import YOLO
            except ImportError as exc:
                raise ImportError(
                    "ultralytics is required for YOLO ball detection. "
                    "Install with: pip install ultralytics"
                ) from exc

            model_path = Path(settings.ML_MODELS_DIR) / "yolo_tennis_ball.pt"
            if not model_path.exists():
                raise FileNotFoundError(
                    f"YOLO weights not found at {model_path}. "
                    "See docs/ball-detection-fine-tuning.md for training instructions."
                )

            self._model = YOLO(str(model_path))

            # Detect whether this is a fine-tuned model (1 class) or base COCO model
            model_names = getattr(self._model, "names", {})
            if len(model_names) > 10:
                # Base COCO model — use sports-ball class
                self._ball_class = COCO_SPORTS_BALL_CLASS
                self._logger.info(
                    "Loaded base COCO YOLO model (class %d = sports ball)",
                    COCO_SPORTS_BALL_CLASS,
                )
            else:
                self._ball_class = FINE_TUNED_BALL_CLASS
                self._logger.info(
                    "Loaded fine-tuned YOLO model (%d classes)", len(model_names)
                )

            self._logger.info("YOLO model loaded from %s", model_path)

        return self._model

    def analyze_serve_windows(
        self,
        video_path: Path,
        windows: List[Dict[str, float]],
        padding_ms: float = 300,
        confidence: float = DEFAULT_CONFIDENCE,
    ) -> Dict[str, Any]:
        """Run YOLO ball detection within the given time windows.

        Same return schema as TrackNetBallDetectionService so downstream code
        (contact_detector, toss_metrics, serve_biomechanics_service) works unchanged.

        Per-frame dict schema (in ball_detections list):
            frame_index: int
            timestamp_ms: float
            ball_x: float | None
            ball_y: float | None
            confidence: float | None   -- YOLO bbox confidence (0-1)
            interpolated: bool         -- True if filled by spline post-processing

        Args:
            video_path: Path to the video file.
            windows: List of dicts with start_ms and end_ms.
            padding_ms: Padding before/after each window (milliseconds).
            confidence: Minimum YOLO confidence to accept a detection.

        Returns:
            Dict with keys: ball_detections, total_frames, frames_with_ball,
            detection_rate, processing_time_seconds, frame_processing_rate, status,
            video_path.
        """
        start_time = time.time()
        self._logger.info(
            "Starting YOLO ball detection for %d windows in: %s",
            len(windows),
            video_path,
        )

        try:
            model = self._get_model()
        except (ImportError, FileNotFoundError) as exc:
            return self._error_result(start_time, str(exc))

        if sv is None:
            return self._error_result(
                start_time,
                "supervision is required for ByteTrack tracking. "
                "Install with: pip install supervision",
            )

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

        raw_detections: List[Dict[str, Any]] = []
        total_frames = 0

        for window in windows:
            start_ms = window.get("start_ms", 0.0)
            end_ms = window.get("end_ms", 0.0)
            padded_start_ms = max(0.0, start_ms - padding_ms)
            padded_end_ms = min(
                (total_video_frames / fps * 1000) if fps > 0 else end_ms + padding_ms,
                end_ms + padding_ms,
            )
            start_frame = int(padded_start_ms * fps / 1000.0) if fps > 0 else 0
            end_frame = min(
                int(padded_end_ms * fps / 1000.0) if fps > 0 else total_video_frames,
                total_video_frames,
            )

            # ByteTrack tracker — fresh instance per window
            tracker = sv.ByteTrack()
            tracked_frames: List[tuple] = []

            cap = cv2.VideoCapture(str(video_path))
            if not cap.isOpened():
                continue
            cap.set(cv2.CAP_PROP_ORIENTATION_AUTO, 0)
            cap.set(cv2.CAP_PROP_POS_FRAMES, start_frame)

            idx = start_frame
            while idx <= end_frame and idx < total_video_frames:
                ret, frame = cap.read()
                if not ret:
                    break

                if rotation != 0:
                    frame = _rotate_frame(frame, rotation)

                timestamp_ms = (idx * 1000.0 / fps) if fps > 0 else 0.0

                results = model(frame, verbose=False)
                detections = sv.Detections.from_ultralytics(results[0])

                # Filter to ball class only, above confidence threshold
                mask = (detections.class_id == self._ball_class) & (
                    detections.confidence >= confidence
                )
                detections = detections[mask]

                tracked = tracker.update_with_detections(detections)
                tracked_frames.append((idx, timestamp_ms, tracked))

                idx += 1
                total_frames += 1

            cap.release()

            # Select the ball track: highest total displacement
            ball_track_id = _select_ball_track(tracked_frames)

            # Build output dicts from the selected track
            for fidx, ts, tracked in tracked_frames:
                if ball_track_id is not None and tracked.tracker_id is not None:
                    track_mask = tracked.tracker_id == ball_track_id
                    if track_mask.any():
                        bbox = tracked.xyxy[track_mask][0]
                        cx = float((bbox[0] + bbox[2]) / 2.0)
                        cy = float((bbox[1] + bbox[3]) / 2.0)
                        conf = float(tracked.confidence[track_mask][0])
                        raw_detections.append(
                            {
                                "frame_index": fidx,
                                "timestamp_ms": ts,
                                "ball_x": cx,
                                "ball_y": cy,
                                "confidence": conf,
                                "interpolated": False,
                            }
                        )
                        continue

                raw_detections.append(
                    {
                        "frame_index": fidx,
                        "timestamp_ms": ts,
                        "ball_x": None,
                        "ball_y": None,
                        "confidence": None,
                        "interpolated": False,
                    }
                )

        # Post-processing: velocity filter + spline interpolation.
        # Relaxed params vs TrackNet defaults: YOLO detects the ball in fewer frames
        # but with high confidence, so we allow larger gaps and fewer anchors.
        smoother = TrajectorySmoother(
            max_gap_frames=15,
            min_anchors=2,
        )
        ball_detections = smoother.smooth(raw_detections)

        frames_with_ball = sum(
            1 for d in ball_detections if d.get("ball_x") is not None
        )
        processing_time = time.time() - start_time

        self._logger.info(
            "YOLO detection complete: %d/%d frames with ball in %.2fs",
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
