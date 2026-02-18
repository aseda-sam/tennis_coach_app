"""Auto-detect contact timestamp from ball + dominant-wrist proximity."""

import json
import logging
from typing import Any, Dict, List, Optional

from app.models.ball_detection import BallDetection
from app.models.pose_detection import PoseDetection
from app.models.serve_window import ServeWindow
from app.models.video import Video
from app.services.pose_data_service import get_pose_at_timestamp

logger = logging.getLogger(__name__)

# Minimum ball detection confidence to consider for contact
MIN_BALL_CONFIDENCE = 0.3

# Max ball-wrist distance (pixels) as fraction of approximate player height (frame height * 0.5)
# Contact: ball and racket/wrist are very close
DISTANCE_THRESHOLD_FRACTION = 0.15

# Ball must be in upper portion of frame (contact is overhead). Fraction of frame height.
UPPER_FRAME_Y_FRACTION = 0.5

# Toss window for peak: first 70% of serve duration (ball goes up then down)
TOSS_WINDOW_FRACTION = 0.7


def _toss_peak_timestamp(
    ball_list: List[Dict[str, Any]],
    start_sec: float,
    end_sec: float,
) -> Optional[float]:
    """Return timestamp (seconds) of toss peak = frame with minimum ball_y in toss window."""
    start_ms = start_sec * 1000
    # Toss phase: start to 70% of window
    duration_sec = end_sec - start_sec
    toss_end_sec = start_sec + duration_sec * TOSS_WINDOW_FRACTION
    end_ms = toss_end_sec * 1000

    best_ts_ms: Optional[float] = None
    best_y = float("inf")
    for det in ball_list:
        if det.get("ball_y") is None:
            continue
        ts_ms = det.get("timestamp_ms")
        if ts_ms is None:
            continue
        if start_ms <= ts_ms <= end_ms and det["ball_y"] < best_y:
            best_y = det["ball_y"]
            best_ts_ms = ts_ms
    if best_ts_ms is None:
        return None
    return best_ts_ms / 1000.0


def _distance_px(ball_x: float, ball_y: float, wrist_x: float, wrist_y: float) -> float:
    """Euclidean distance in pixel space."""
    return ((ball_x - wrist_x) ** 2 + (ball_y - wrist_y) ** 2) ** 0.5


def _detect_contact_by_proximity(
    ball_list: List[Dict[str, Any]],
    pose_detection: PoseDetection,
    serve_window: ServeWindow,
    video: Video,
    dominant_hand: str,
    toss_peak_sec: Optional[float],
    fps: float,
    video_height: float,
    player_height_px: float,
) -> Optional[float]:
    """Find contact as the frame after toss peak where ball is closest to dominant wrist."""
    wrist_key = f"{dominant_hand}_wrist"
    # Only consider frames after toss peak
    if toss_peak_sec is not None:
        min_ts_sec = toss_peak_sec
    else:
        min_ts_sec = serve_window.start_timestamp

    start_sec = serve_window.start_timestamp
    end_sec = serve_window.end_timestamp
    # Upper portion of frame (contact overhead)
    upper_y_threshold = video_height * (1.0 - UPPER_FRAME_Y_FRACTION)
    distance_threshold_px = max(20.0, player_height_px * DISTANCE_THRESHOLD_FRACTION)

    best_ts_sec: Optional[float] = None
    best_dist = float("inf")

    for det in ball_list:
        ts_ms = det.get("timestamp_ms")
        if ts_ms is None:
            continue
        ts_sec = ts_ms / 1000.0
        if ts_sec < min_ts_sec or ts_sec > end_sec or ts_sec < start_sec:
            continue
        if det.get("confidence") is None or det["confidence"] < MIN_BALL_CONFIDENCE:
            continue
        ball_x = det.get("ball_x")
        ball_y = det.get("ball_y")
        if ball_x is None or ball_y is None:
            continue
        if ball_y > upper_y_threshold:
            continue

        pose = get_pose_at_timestamp(pose_detection, video, ts_sec)
        if not pose:
            continue
        wrist = pose.get(wrist_key)
        if not wrist or len(wrist) < 2:
            continue

        dist = _distance_px(ball_x, ball_y, wrist[0], wrist[1])
        if dist < best_dist and dist <= distance_threshold_px:
            best_dist = dist
            best_ts_sec = ts_sec

    return best_ts_sec


def _detect_contact_by_velocity_reversal(
    ball_list: List[Dict[str, Any]],
    serve_window: ServeWindow,
    toss_peak_sec: Optional[float],
    fps: float,
) -> Optional[float]:
    """Find contact as the frame where ball vertical velocity reverses (after toss peak)."""
    if toss_peak_sec is None or len(ball_list) < 3:
        return None

    start_sec = serve_window.start_timestamp
    end_sec = serve_window.end_timestamp
    # Sort by timestamp
    sorted_dets = sorted(
        [
            d
            for d in ball_list
            if d.get("timestamp_ms") is not None and d.get("ball_y") is not None
        ],
        key=lambda d: d["timestamp_ms"],
    )
    if len(sorted_dets) < 3:
        return None

    # Find first frame after toss peak where ball_y starts increasing (ball going down)
    for i in range(1, len(sorted_dets) - 1):
        ts_sec = sorted_dets[i]["timestamp_ms"] / 1000.0
        if ts_sec < toss_peak_sec or ts_sec < start_sec or ts_sec > end_sec:
            continue
        prev_y = sorted_dets[i - 1].get("ball_y")
        curr_y = sorted_dets[i].get("ball_y")
        next_y = sorted_dets[i + 1].get("ball_y")
        if prev_y is None or curr_y is None or next_y is None:
            continue
        # Reversal: was going up (y decreasing), now going down (y increasing)
        if prev_y > curr_y and next_y > curr_y:
            return round(ts_sec, 4)

    return None


def detect_contact_timestamp(
    ball_detection: BallDetection,
    pose_detection: PoseDetection,
    serve_window: ServeWindow,
    video: Video,
    dominant_hand: str,
) -> Optional[float]:
    """Auto-detect contact timestamp from ball + wrist proximity.

    Returns contact timestamp in seconds, or None if detection fails.
    Only considers frames after toss peak. Falls back to ball velocity reversal
    if proximity does not yield a candidate.
    """
    try:
        if not ball_detection.ball_data:
            return None
        ball_list = json.loads(ball_detection.ball_data)
        if not ball_list:
            return None
    except (json.JSONDecodeError, TypeError):
        return None

    fps = video.fps if video.fps else 30.0
    video_height = float(video.height or 720)
    # Approximate player height for distance threshold
    player_height_px = video_height * 0.5
    if pose_detection and pose_detection.pose_data:
        pose_at_start = get_pose_at_timestamp(
            pose_detection, video, serve_window.start_timestamp
        )
        if pose_at_start:
            ls = pose_at_start.get("left_shoulder")
            rs = pose_at_start.get("right_shoulder")
            la = pose_at_start.get("left_ankle")
            ra = pose_at_start.get("right_ankle")
            if ls and rs and la and ra:
                shoulder_y = (ls[1] + rs[1]) / 2
                ankle_y = (la[1] + ra[1]) / 2
                h = ankle_y - shoulder_y
                if h > 0:
                    player_height_px = h

    start_sec = serve_window.start_timestamp
    end_sec = serve_window.end_timestamp
    toss_peak_sec = _toss_peak_timestamp(ball_list, start_sec, end_sec)

    result = _detect_contact_by_proximity(
        ball_list=ball_list,
        pose_detection=pose_detection,
        serve_window=serve_window,
        video=video,
        dominant_hand=dominant_hand,
        toss_peak_sec=toss_peak_sec,
        fps=fps,
        video_height=video_height,
        player_height_px=player_height_px,
    )

    if result is not None:
        return round(result, 4)

    result = _detect_contact_by_velocity_reversal(
        ball_list=ball_list,
        serve_window=serve_window,
        toss_peak_sec=toss_peak_sec,
        fps=fps,
    )
    return result
