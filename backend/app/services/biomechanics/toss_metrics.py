"""Toss metrics computation from ball detection data.

Computes toss peak height, peak timestamp, and toss laterality for a serve window.
"""

import json
import logging
from typing import Dict, Optional

from sqlalchemy.orm import Session

from app.models.ball_detection import BallDetection
from app.models.pose_detection import PoseDetection
from app.models.serve_window import ServeWindow
from app.models.video import Video
from app.services.pose_data_service import get_pose_at_timestamp

logger = logging.getLogger(__name__)


def _get_best_ball_detection(db: Session, video_id: int) -> Optional[BallDetection]:
    """Get the latest completed ball detection for a video, if any."""
    return (
        db.query(BallDetection)
        .filter(
            BallDetection.video_id == video_id,
            BallDetection.status == "completed",
        )
        .order_by(BallDetection.created_at.desc())
        .first()
    )


def _compute_toss_metrics(
    serve_window: ServeWindow,
    ball_detection: BallDetection,
    video: Video,
    pose_detection: Optional[PoseDetection],
) -> Optional[Dict[str, any]]:
    """
    Compute toss peak height and timestamp for a serve window from ball detection data.

    Toss window: start_timestamp to contact_timestamp (or end_timestamp if no contact).
    Peak = frame with minimum ball_y (highest point in screen coords).
    toss_peak_height is normalized by player height (shoulder-to-ankle from pose).

    Returns:
        Dict with toss_peak_height (float), toss_peak_timestamp (float), or None if insufficient data.
    """
    try:
        if not ball_detection.ball_data:
            return None
        ball_list = json.loads(ball_detection.ball_data)
        if not ball_list:
            return None
    except (json.JSONDecodeError, TypeError):
        return None

    # Toss phase: from serve start until contact (or 80% of window if no contact)
    start_sec = serve_window.start_timestamp
    if serve_window.contact_timestamp is not None:
        end_sec = serve_window.contact_timestamp
    else:
        duration = serve_window.end_timestamp - serve_window.start_timestamp
        end_sec = serve_window.start_timestamp + duration * 0.8

    start_ms = start_sec * 1000
    end_ms = end_sec * 1000

    # Find the detection with smallest ball_y (highest point) in the toss window
    best = None
    best_y = float("inf")
    for det in ball_list:
        if det.get("ball_y") is None:
            continue
        ts_ms = det.get("timestamp_ms")
        if ts_ms is None:
            continue
        if start_ms <= ts_ms <= end_ms and det["ball_y"] < best_y:
            best_y = det["ball_y"]
            best = det

    if best is None:
        return None

    toss_peak_timestamp = best["timestamp_ms"] / 1000.0

    # Normalize height by player height (shoulder-to-ankle from pose)
    video_height = video.height or 720
    player_height_px = float(video_height) * 0.5
    shoulder_y: Optional[float] = None
    pose_at_start = None
    if pose_detection and pose_detection.pose_data:
        pose_at_start = get_pose_at_timestamp(pose_detection, video, start_sec)
        if pose_at_start:
            ls = pose_at_start.get("left_shoulder")
            rs = pose_at_start.get("right_shoulder")
            la = pose_at_start.get("left_ankle")
            ra = pose_at_start.get("right_ankle")
            if ls and rs and la and ra:
                shoulder_y = (ls[1] + rs[1]) / 2
                ankle_y = (la[1] + ra[1]) / 2
                player_height_px = ankle_y - shoulder_y
                if player_height_px <= 0:
                    player_height_px = float(video_height) * 0.5

    # Ball peak height above shoulder, in "body heights". Screen coords: smaller y = higher.
    if shoulder_y is not None:
        height_above_shoulder_px = shoulder_y - best_y
    else:
        height_above_shoulder_px = max(0, video_height * 0.2 - best_y)
    toss_peak_height = (
        height_above_shoulder_px / player_height_px if player_height_px > 0 else None
    )
    if toss_peak_height is not None and toss_peak_height < 0:
        toss_peak_height = 0.0

    # Toss laterality: horizontal distance of ball from body center, normalized
    toss_laterality: Optional[float] = None
    if best.get("ball_x") is not None and pose_at_start is not None:
        ls = pose_at_start.get("left_shoulder")
        rs = pose_at_start.get("right_shoulder")
        if ls and rs:
            body_center_x = (ls[0] + rs[0]) / 2
            toss_laterality = (best["ball_x"] - body_center_x) / player_height_px
            toss_laterality = round(toss_laterality, 4)

    return {
        "toss_peak_height": round(toss_peak_height, 4)
        if toss_peak_height is not None
        else None,
        "toss_peak_timestamp": round(toss_peak_timestamp, 4),
        "toss_laterality": toss_laterality,
    }
