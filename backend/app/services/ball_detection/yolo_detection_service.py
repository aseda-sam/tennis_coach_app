"""Ball detection service using fine-tuned YOLOv8 + ByteTrack for tennis ball tracking.

Close-up portrait phone footage where the ball is 20-100+ px.

Internal flow per window:
  1. Iterate frames individually
  2. Run YOLO inference -> sv.Detections -> ByteTrack tracker assigns track IDs
  3. After all frames: select the track with highest peak displacement (= moving ball)
  4. Build output dicts using only positions from the selected track
  5. After all windows: apply TrajectorySmoother (spline interpolation for short gaps)
"""

# pyright: reportMissingImports=false, reportPrivateImportUsage=false, reportCallIssue=false, reportOptionalOperand=false, reportArgumentType=false
# supervision and ultralytics are optional ML deps (installed in worker only).

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


# Sliding window size for peak displacement track selection.
# 5 frames ≈ 0.17s at 30fps — captures the toss arc burst.
PEAK_WINDOW: int = 5

# Minimum peak-window displacement (px) for a track to qualify as a moving
# serve ball. Tracks below this are treated as static — return None rather
# than picking the least-bad option. Real toss arcs span tens to hundreds
# of px in a 5-frame window; sub-pixel jitter accumulates to ~1-2 px.
MIN_BALL_PEAK_DISPLACEMENT_PX: float = 5.0

# Static-distractor scan parameters. A track (or pooled cluster across
# windows) is a distractor if it is "still enough" and "persistent enough."
DISTRACTOR_MAX_DISPLACEMENT_PX: float = 3.0
DISTRACTOR_MIN_POOLED_FRAMES: int = 30
DISTRACTOR_SPATIAL_RADIUS_PX: float = 5.0


def _collect_track_positions(
    tracked_frames: List[tuple],
) -> dict[int, list[tuple[float, float]]]:
    """Group ByteTrack output by track id: returns {tid: [(cx, cy), ...]}."""
    out: dict[int, list[tuple[float, float]]] = {}
    for _idx, _ts, tracked in tracked_frames:
        if tracked.tracker_id is None:
            continue
        for i, tid in enumerate(tracked.tracker_id):
            bbox = tracked.xyxy[i]
            cx = float((bbox[0] + bbox[2]) / 2.0)
            cy = float((bbox[1] + bbox[3]) / 2.0)
            out.setdefault(int(tid), []).append((cx, cy))
    return out


def _peak_window_displacement(
    positions: list[tuple[float, float]],
    window: int = PEAK_WINDOW,
) -> float:
    """Largest sliding-window total of consecutive displacements."""
    if len(positions) < 2:
        return 0.0
    displacements = [
        math.hypot(
            positions[i + 1][0] - positions[i][0],
            positions[i + 1][1] - positions[i][1],
        )
        for i in range(len(positions) - 1)
    ]
    w = min(window, len(displacements))
    return max(sum(displacements[i : i + w]) for i in range(len(displacements) - w + 1))


def _identify_static_distractors(
    tracked_frames_per_window: List[List[tuple]],
    *,
    max_displacement_px: float = DISTRACTOR_MAX_DISPLACEMENT_PX,
    min_pooled_frames: int = DISTRACTOR_MIN_POOLED_FRAMES,
    spatial_radius_px: float = DISTRACTOR_SPATIAL_RADIUS_PX,
) -> List[set[int]]:
    """Identify static distractor track IDs per window via cross-window pooling.

    Real tennis sessions often have stationary balls lying on the court that
    a strong fine-tuned model detects confidently across the whole video.
    These appear as long, low-displacement tracks — qualitatively different
    from the moving serve ball. Pooling evidence across windows lets us
    catch flickery distractors that miss the threshold in any single window.

    A pooled cluster (tracks across windows whose mean centroids fall
    within `spatial_radius_px`) is flagged as static if every track in the
    cluster has displacement < `max_displacement_px` AND the cluster's
    total frame count is ≥ `min_pooled_frames`.

    Args:
        tracked_frames_per_window: One ByteTrack-tagged frame list per window.

    Returns:
        List of distractor-track-id sets, one per window (same order as input).
    """
    if not tracked_frames_per_window:
        return []

    # Per-window per-track stats: (window_idx, track_id, mean_x, mean_y,
    # n_frames, max_disp_proxy)
    per_track: list[tuple[int, int, float, float, int, float]] = []
    for wi, frames in enumerate(tracked_frames_per_window):
        positions_by_tid = _collect_track_positions(frames)
        for tid, positions in positions_by_tid.items():
            xs = [p[0] for p in positions]
            ys = [p[1] for p in positions]
            mean_x = sum(xs) / len(xs)
            mean_y = sum(ys) / len(ys)
            # Bounding-box diagonal of all positions — tight upper bound on
            # max pairwise distance, O(n) instead of O(n^2).
            disp = math.hypot(max(xs) - min(xs), max(ys) - min(ys))
            per_track.append((wi, tid, mean_x, mean_y, len(positions), disp))

    # Spatial union-find clustering by mean position
    n = len(per_track)
    parent = list(range(n))

    def find(i: int) -> int:
        while parent[i] != i:
            parent[i] = parent[parent[i]]
            i = parent[i]
        return i

    def union(i: int, j: int) -> None:
        ri, rj = find(i), find(j)
        if ri != rj:
            parent[ri] = rj

    for i in range(n):
        for j in range(i + 1, n):
            d = math.hypot(
                per_track[i][2] - per_track[j][2], per_track[i][3] - per_track[j][3]
            )
            if d <= spatial_radius_px:
                union(i, j)

    clusters: dict[int, list[int]] = {}
    for i in range(n):
        clusters.setdefault(find(i), []).append(i)

    distractors: List[set[int]] = [set() for _ in tracked_frames_per_window]
    for cluster in clusters.values():
        total_frames = sum(per_track[i][4] for i in cluster)
        max_disp = max(per_track[i][5] for i in cluster)
        if total_frames >= min_pooled_frames and max_disp < max_displacement_px:
            for i in cluster:
                wi, tid = per_track[i][0], per_track[i][1]
                distractors[wi].add(tid)

    return distractors


def _select_ball_track(
    tracked_frames: List[tuple],
    *,
    excluded_track_ids: Optional[set[int]] = None,
    min_peak_displacement_px: float = MIN_BALL_PEAK_DISPLACEMENT_PX,
) -> Optional[int]:
    """Pick the track ID with the highest peak displacement (= moving ball).

    For each track, computes pairwise displacements between consecutive positions,
    then finds the maximum total displacement in any sliding window of PEAK_WINDOW
    frames. This catches the toss arc regardless of how many stationary ball-in-hand
    frames exist in the same track.

    Tracks in `excluded_track_ids` (e.g., flagged static distractors) are skipped.
    If no remaining track's peak exceeds `min_peak_displacement_px`, returns None
    rather than the least-bad option.

    Args:
        tracked_frames: List of (frame_index, timestamp_ms, sv.Detections) tuples.
        excluded_track_ids: Track IDs to skip (typically flagged distractors).
        min_peak_displacement_px: Threshold below which no track qualifies.

    Returns:
        The track ID of the most-moving qualifying object, or None if none qualify.
    """
    track_positions = _collect_track_positions(tracked_frames)
    excluded = excluded_track_ids or set()

    best_id: Optional[int] = None
    best_peak = 0.0
    for tid, positions in track_positions.items():
        if tid in excluded:
            continue
        peak = _peak_window_displacement(positions)
        if peak > best_peak:
            best_id, best_peak = tid, peak

    if best_peak < min_peak_displacement_px:
        return None
    return best_id


class YoloBallDetectionService:
    """Detect tennis balls in video using fine-tuned YOLOv8 + ByteTrack."""

    def __init__(
        self, device: Optional[str] = None, imgsz: Optional[int] = None
    ) -> None:
        self._model: Optional[object] = None
        self._ball_class: int = FINE_TUNED_BALL_CLASS
        self._device: Optional[str] = device
        self._imgsz: int = imgsz if imgsz is not None else settings.YOLO_IMGSZ
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

            # Log which compute device YOLO selected (CPU / MPS / CUDA)
            device = getattr(self._model, "device", "unknown")
            self._logger.info("YOLO inference device: %s", device)
            if self._device:
                self._logger.info(
                    "YOLO inference requested device override: %s", self._device
                )
            self._logger.info("YOLO inference imgsz: %d", self._imgsz)

        return self._model

    def analyze_serve_windows(
        self,
        video_path: Path,
        windows: List[Dict[str, float]],
        padding_ms: float = 300,
        confidence: float = DEFAULT_CONFIDENCE,
    ) -> Dict[str, Any]:
        """Run YOLO ball detection within the given time windows.

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

        # First pass: run YOLO + ByteTrack on every window. We collect all
        # tracked_frames before track selection so the pooled static-distractor
        # scan can use evidence from across the whole video.
        per_window_tracked: List[List[tuple]] = []
        per_window_meta: List[Dict[str, Any]] = []

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

            tracker = sv.ByteTrack()
            tracked_frames: List[tuple] = []

            cap = cv2.VideoCapture(str(video_path))
            if not cap.isOpened():
                per_window_tracked.append(tracked_frames)
                per_window_meta.append(
                    {"start_frame": start_frame, "end_frame": end_frame}
                )
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

                if self._device:
                    results = model(
                        frame,
                        verbose=False,
                        device=self._device,
                        imgsz=self._imgsz,
                    )
                else:
                    results = model(frame, verbose=False, imgsz=self._imgsz)
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
            per_window_tracked.append(tracked_frames)
            per_window_meta.append({"start_frame": start_frame, "end_frame": end_frame})

        # Pooled cross-window scan: identify static distractor track ids per window.
        distractors_per_window = _identify_static_distractors(per_window_tracked)
        for wi, distractors in enumerate(distractors_per_window):
            if distractors:
                self._logger.info(
                    "Window %d: filtered %d static distractor track(s): %s",
                    wi,
                    len(distractors),
                    sorted(distractors),
                )

        # Second pass: select the moving-ball track per window and emit per-frame
        # detections. If no track passes the displacement gate, the window's
        # frames are emitted with ball_x/ball_y = None — better than confidently
        # writing a stationary distractor.
        for wi, tracked_frames in enumerate(per_window_tracked):
            ball_track_id = _select_ball_track(
                tracked_frames,
                excluded_track_ids=distractors_per_window[wi],
            )
            if ball_track_id is None:
                self._logger.info(
                    "Window %d: no moving-ball track met displacement gate (%.1f px)",
                    wi,
                    MIN_BALL_PEAK_DISPLACEMENT_PX,
                )

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

        # Spline interpolation: fill short gaps where YOLO missed the ball.
        # Relaxed params: YOLO detects the ball in fewer frames but with high
        # confidence, so we allow larger gaps and fewer anchors.
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
