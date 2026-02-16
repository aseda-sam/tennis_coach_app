"""Pose data helpers for biomechanics and overlays."""

import json
import logging
from typing import Dict, List, Optional

from sqlalchemy.orm import Session

from app.models.ball_detection import BallDetection
from app.models.pose_detection import PoseDetection
from app.models.serve_attempt import ServeAttempt
from app.models.video import Video

logger = logging.getLogger(__name__)


def _extract_keypoints(frame_data: Optional[Dict]) -> Optional[Dict]:
    """
    Extract keypoints from frame data, handling both old and new formats.

    Args:
        frame_data: Frame data from pose_detections (either keypoints dict directly
                   or wrapper dict with frame_index/timestamp_ms/keypoints)

    Returns:
        Keypoints dict if available, None otherwise
    """
    if frame_data is None:
        return None

    # New format: {"frame_index": ..., "timestamp_ms": ..., "keypoints": {...}}
    if isinstance(frame_data, dict) and "keypoints" in frame_data:
        return frame_data.get("keypoints")

    # Old format: keypoints dict directly (backward compatibility)
    return frame_data


def _select_best_pose_detection(db: Session, video_id: int) -> Optional[PoseDetection]:
    """
    Select the best pose detection record for analysis.

    Prefers: latest 'refine' > latest 'full' > latest 'scout'.
    Always orders by created_at desc for deterministic selection.

    Args:
        db: Database session
        video_id: Video ID

    Returns:
        Best PoseDetection record, or None if none found
    """
    # Query all completed pose detections for this video, ordered by created_at desc
    all_detections = (
        db.query(PoseDetection)
        .filter(
            PoseDetection.video_id == video_id,
            PoseDetection.status == "completed",
        )
        .order_by(PoseDetection.created_at.desc())
        .all()
    )

    if not all_detections:
        return None

    # Prefer refine > full > scout
    for detection in all_detections:
        if detection.detection_mode == "refine":
            logger.info(
                "Selected refine pose detection %s for video %s",
                detection.id,
                video_id,
            )
            return detection

    for detection in all_detections:
        if detection.detection_mode == "full":
            logger.info(
                "Selected full pose detection %s for video %s",
                detection.id,
                video_id,
            )
            return detection

    # Fall back to scout (or any other mode)
    detection = all_detections[0]
    logger.info(
        "Selected %s pose detection %s for video %s",
        detection.detection_mode,
        detection.id,
        video_id,
    )
    return detection


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
    serve_attempt: ServeAttempt,
    ball_detection: BallDetection,
    video: Video,
    pose_detection: Optional[PoseDetection],
) -> Optional[Dict[str, any]]:
    """
    Compute toss peak height and timestamp for a serve attempt from ball detection data.

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
    start_sec = serve_attempt.start_timestamp
    if serve_attempt.contact_timestamp is not None:
        end_sec = serve_attempt.contact_timestamp
    else:
        duration = serve_attempt.end_timestamp - serve_attempt.start_timestamp
        end_sec = serve_attempt.start_timestamp + duration * 0.8

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

    return {
        "toss_peak_height": round(toss_peak_height, 4)
        if toss_peak_height is not None
        else None,
        "toss_peak_timestamp": round(toss_peak_timestamp, 4),
    }


def get_pose_frames_in_window(
    pose_detection: PoseDetection,
    video: Video,
    start_timestamp: float,
    end_timestamp: float,
) -> List[Optional[Dict]]:
    """
    Get pose data for all frames within a time window.

    Args:
        pose_detection: PoseDetection object with pose_data
        video: Video object with fps metadata
        start_timestamp: Start timestamp in seconds
        end_timestamp: End timestamp in seconds

    Returns:
        List of pose landmarks dictionaries (one per frame), or None for frames without pose
    """
    try:
        if not pose_detection.pose_data:
            logger.warning("No pose data available")
            return []

        # Deserialize pose data
        raw_pose_data = json.loads(pose_detection.pose_data)

        if not raw_pose_data:
            logger.warning("Empty pose data")
            return []

        # Calculate frame range from timestamps and FPS
        fps = video.fps if video.fps else 30.0
        start_frame = int(start_timestamp * fps)
        end_frame = int(end_timestamp * fps)

        # Extract frames in window
        frames = []
        for frame_idx in range(start_frame, min(end_frame + 1, len(raw_pose_data))):
            if frame_idx < len(raw_pose_data):
                frame_data = raw_pose_data[frame_idx]
                keypoints = _extract_keypoints(frame_data)
                frames.append(keypoints)
            else:
                frames.append(None)

        return frames

    except (json.JSONDecodeError, ValueError, KeyError) as e:
        logger.error("Error getting pose frames in window: %s", e)
        return []


def get_pose_at_timestamp(
    pose_detection: PoseDetection, video: Video, timestamp: float
) -> Optional[Dict]:
    """
    Get pose data for the frame closest to a given timestamp.

    Args:
        pose_detection: PoseDetection object with pose_data
        video: Video object with fps metadata
        timestamp: Timestamp in seconds

    Returns:
        Pose landmarks for the frame closest to timestamp, or None if not found
    """
    try:
        if not pose_detection.pose_data:
            logger.warning("No pose data available")
            return None

        # Deserialize pose data
        raw_pose_data = json.loads(pose_detection.pose_data)

        if not raw_pose_data:
            logger.warning("Empty pose data")
            return None

        # Calculate frame from timestamp and FPS
        fps = video.fps if video.fps else 30.0
        target_frame = int(timestamp * fps)
        logger.debug(
            f"Calculated frame {target_frame} from timestamp {timestamp}s using FPS: {fps}"
        )

        # Find the closest available frame
        if target_frame < len(raw_pose_data):
            frame_data = raw_pose_data[target_frame]
            keypoints = _extract_keypoints(frame_data)
            if keypoints is not None:
                return keypoints

        # If exact frame not found, search for nearest frame with pose data
        for offset in range(1, min(10, len(raw_pose_data))):  # Search within 10 frames
            # Try frames before and after
            for direction in [-1, 1]:
                frame_idx = target_frame + (offset * direction)
                if 0 <= frame_idx < len(raw_pose_data):
                    frame_data = raw_pose_data[frame_idx]
                    keypoints = _extract_keypoints(frame_data)
                    if keypoints is not None:
                        logger.info(
                            f"Using frame {frame_idx} (offset {offset * direction}) "
                            f"for timestamp {timestamp}s"
                        )
                        return keypoints

        logger.warning("No pose data found near timestamp %ss", timestamp)
        return None

    except (json.JSONDecodeError, ValueError, KeyError) as e:
        logger.error("Error getting pose at timestamp: %s", e)
        return None
