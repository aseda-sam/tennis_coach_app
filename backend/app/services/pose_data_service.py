"""Pose data helpers for biomechanics and overlays."""

import json
import logging
from typing import Dict, List, Optional

from sqlalchemy.orm import Session

from app.models.pose_detection import PoseDetection
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
