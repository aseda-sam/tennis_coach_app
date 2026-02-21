"""Auto-detect contact timestamp from ball + dominant-wrist proximity."""

import json
import logging
from typing import Any, Dict, List, Optional

from app.core.config import settings
from app.models.ball_detection import BallDetection
from app.models.pose_detection import PoseDetection
from app.models.serve_window import ServeWindow
from app.models.video import Video
from app.services.pose_data_service import (
    get_pose_at_timestamp,
    get_pose_frames_in_window,
)

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

# V2 detector: search in a bounded window after acceleration onset.
CONTACT_V2_ACCEL_VELOCITY_MULTIPLIER = 2.0
CONTACT_V2_SEARCH_WINDOW_FRACTION = 0.45
CONTACT_V2_SEARCH_WINDOW_MIN_SECONDS = 1.5
CONTACT_V2_SEARCH_WINDOW_MAX_SECONDS = 2.5
CONTACT_V2_RELAXED_DISTANCE_MULTIPLIER = 3.0
CONTACT_V2_RELAXED_DISTANCE_FRACTION = 0.45
CONTACT_V2_RELAXED_MIN_DISTANCE_PX = 70.0


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
    min_ts_override_sec: Optional[float] = None,
    max_ts_override_sec: Optional[float] = None,
) -> Optional[float]:
    """Find contact as the frame after toss peak where ball is closest to dominant wrist."""
    wrist_key = f"{dominant_hand}_wrist"
    # Only consider frames after toss peak
    if min_ts_override_sec is not None:
        min_ts_sec = min_ts_override_sec
    elif toss_peak_sec is not None:
        min_ts_sec = toss_peak_sec
    else:
        min_ts_sec = serve_window.start_timestamp

    start_sec = serve_window.start_timestamp
    end_sec = (
        min(serve_window.end_timestamp, max_ts_override_sec)
        if max_ts_override_sec is not None
        else serve_window.end_timestamp
    )
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


def _collect_proximity_candidates(
    ball_list: List[Dict[str, Any]],
    pose_detection: PoseDetection,
    serve_window: ServeWindow,
    video: Video,
    dominant_hand: str,
    toss_peak_sec: Optional[float],
    video_height: float,
    min_ts_override_sec: Optional[float] = None,
    max_ts_override_sec: Optional[float] = None,
) -> list[tuple[float, float]]:
    """Collect (timestamp, distance_px) candidates that pass non-distance gates."""
    wrist_key = f"{dominant_hand}_wrist"
    if min_ts_override_sec is not None:
        min_ts_sec = min_ts_override_sec
    elif toss_peak_sec is not None:
        min_ts_sec = toss_peak_sec
    else:
        min_ts_sec = serve_window.start_timestamp

    start_sec = serve_window.start_timestamp
    end_sec = (
        min(serve_window.end_timestamp, max_ts_override_sec)
        if max_ts_override_sec is not None
        else serve_window.end_timestamp
    )
    upper_y_threshold = video_height * (1.0 - UPPER_FRAME_Y_FRACTION)
    candidates: list[tuple[float, float]] = []

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
        candidates.append((ts_sec, dist))

    return candidates


def _best_proximity_candidate_within_threshold(
    candidates: list[tuple[float, float]], threshold_px: float
) -> Optional[float]:
    """Return timestamp of closest candidate if it satisfies threshold, else None."""
    if not candidates:
        return None
    best_ts_sec, best_dist = min(candidates, key=lambda c: c[1])
    if best_dist <= threshold_px:
        return best_ts_sec
    return None


def _v2_search_window_seconds(serve_window: ServeWindow) -> float:
    """Compute phase-gated v2 search window length from serve duration."""
    duration = max(0.0, serve_window.end_timestamp - serve_window.start_timestamp)
    window = duration * CONTACT_V2_SEARCH_WINDOW_FRACTION
    return max(
        CONTACT_V2_SEARCH_WINDOW_MIN_SECONDS,
        min(CONTACT_V2_SEARCH_WINDOW_MAX_SECONDS, window),
    )


def _dominant_wrist_acceleration_timestamp(
    pose_detection: PoseDetection,
    serve_window: ServeWindow,
    video: Video,
    dominant_hand: str,
) -> Optional[float]:
    """Estimate acceleration onset from dominant wrist velocity spike."""
    fps = video.fps if video.fps else 30.0
    if fps <= 0:
        return None

    pose_frames = get_pose_frames_in_window(
        pose_detection,
        video,
        serve_window.start_timestamp,
        serve_window.end_timestamp,
    )
    if len(pose_frames) < 3:
        return None

    wrist_key = f"{dominant_hand}_wrist"
    velocities: list[tuple[int, float]] = []

    prev_wrist: Optional[list[float]] = None
    for idx, frame in enumerate(pose_frames):
        if not frame:
            continue
        wrist = frame.get(wrist_key)
        if not wrist or len(wrist) < 2:
            continue
        if prev_wrist is not None:
            dt = 1.0 / fps
            velocity = (
                _distance_px(wrist[0], wrist[1], prev_wrist[0], prev_wrist[1]) / dt
            )
            velocities.append((idx, velocity))
        prev_wrist = wrist

    if len(velocities) < 3:
        return None

    mean_vel = sum(v for _, v in velocities) / len(velocities)
    if mean_vel <= 0:
        return None

    threshold = mean_vel * CONTACT_V2_ACCEL_VELOCITY_MULTIPLIER
    for idx, vel in velocities:
        if vel > threshold:
            return serve_window.start_timestamp + (idx / fps)

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
    Only considers frames after toss peak and requires proximity criteria.
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

    detector_version = (settings.AUTO_CONTACT_DETECTOR_VERSION or "v1").lower()

    if detector_version == "v2":
        accel_ts = _dominant_wrist_acceleration_timestamp(
            pose_detection=pose_detection,
            serve_window=serve_window,
            video=video,
            dominant_hand=dominant_hand,
        )
        min_ts = max(
            toss_peak_sec
            if toss_peak_sec is not None
            else serve_window.start_timestamp,
            accel_ts if accel_ts is not None else serve_window.start_timestamp,
        )
        max_ts = min(
            serve_window.end_timestamp, min_ts + _v2_search_window_seconds(serve_window)
        )
        candidates = _collect_proximity_candidates(
            ball_list=ball_list,
            pose_detection=pose_detection,
            serve_window=serve_window,
            video=video,
            dominant_hand=dominant_hand,
            toss_peak_sec=toss_peak_sec,
            video_height=video_height,
            min_ts_override_sec=min_ts,
            max_ts_override_sec=max_ts,
        )
        strict_threshold_px = max(20.0, player_height_px * DISTANCE_THRESHOLD_FRACTION)
        result = _best_proximity_candidate_within_threshold(
            candidates, strict_threshold_px
        )
        if result is None and candidates:
            relaxed_threshold_px = max(
                CONTACT_V2_RELAXED_MIN_DISTANCE_PX,
                strict_threshold_px * CONTACT_V2_RELAXED_DISTANCE_MULTIPLIER,
                player_height_px * CONTACT_V2_RELAXED_DISTANCE_FRACTION,
            )
            result = _best_proximity_candidate_within_threshold(
                candidates, relaxed_threshold_px
            )
            if result is not None:
                logger.info(
                    "Auto-contact v2 used relaxed proximity threshold %.1fpx "
                    "(strict %.1fpx) for serve window %s",
                    relaxed_threshold_px,
                    strict_threshold_px,
                    getattr(serve_window, "id", None),
                )
    else:
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

    if result is None:
        return None

    return round(result, 4)
