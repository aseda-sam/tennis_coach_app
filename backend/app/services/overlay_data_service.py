"""Service for overlay data operations."""

import json
import logging
from typing import Dict, List, Optional

from sqlalchemy.orm import Session

from app.api.schemas.overlay_data import PoseFrame, PoseOverlayData
from app.models.ball_detection import BallDetection
from app.models.pose_detection import PoseDetection
from app.services import video_service

logger = logging.getLogger(__name__)

# Maximum size for pose data JSON (50MB)
MAX_POSE_DATA_SIZE = 50 * 1024 * 1024


def get_pose_detection_for_overlay(
    db: Session,
    video_id: int,
) -> Optional[PoseDetection]:
    """Get the best pose detection for overlay rendering.

    Prefers "full" or "scout" mode (covers entire video).
    Falls back to any pose detection if no full/scout available.

    Args:
        db: Database session
        video_id: Video ID

    Returns:
        PoseDetection instance or None if not found
    """
    # Prefer "full" or "scout" mode for overlay (covers entire video)
    # "refine" mode only has data for serve windows, not suitable for full overlay
    pose_detection = (
        db.query(PoseDetection)
        .filter(
            PoseDetection.video_id == video_id,
            PoseDetection.detection_mode.in_(["full", "scout"]),
        )
        .order_by(PoseDetection.created_at.desc())
        .first()
    )

    # Fallback to any pose detection if no full/scout available
    if not pose_detection:
        pose_detection = (
            db.query(PoseDetection)
            .filter(PoseDetection.video_id == video_id)
            .order_by(PoseDetection.created_at.desc())
            .first()
        )

    return pose_detection


def format_overlay_data(
    db: Session,
    video_id: int,
) -> PoseOverlayData:
    """Format pose detection data for overlay rendering.

    Args:
        db: Database session
        video_id: Video ID

    Returns:
        PoseOverlayData with frame-by-frame pose keypoints

    Raises:
        ValueError: If video not found, no pose detection, or data invalid
        RuntimeError: If JSON parsing fails or data size exceeds limit
    """
    # Verify video exists
    video = video_service.get_video_by_id(db, video_id)
    if not video:
        raise ValueError(f"Video with ID {video_id} not found")

    # Get pose detection record
    pose_detection = get_pose_detection_for_overlay(db, video_id)

    if not pose_detection:
        raise ValueError(f"No pose detection found for video {video_id}")

    logger.debug(
        "Using pose detection %s (mode=%s) for overlay on video %s",
        pose_detection.id,
        pose_detection.detection_mode,
        video_id,
    )

    if pose_detection.status != "completed":
        raise ValueError(f"Pose detection {pose_detection.id} is not completed")

    # Parse pose data
    if not pose_detection.pose_data:
        raise ValueError(f"No pose data available for video {video_id}")

    # Validate JSON size before parsing
    pose_data_size = len(pose_detection.pose_data.encode("utf-8"))
    if pose_data_size > MAX_POSE_DATA_SIZE:
        logger.error(
            "Pose data too large for video %s: %d bytes (max: %d)",
            video_id,
            pose_data_size,
            MAX_POSE_DATA_SIZE,
        )
        raise ValueError("Pose data exceeds maximum size limit")

    try:
        raw_pose_data = json.loads(pose_detection.pose_data)
        confidence_scores = (
            json.loads(pose_detection.confidence_scores)
            if pose_detection.confidence_scores
            else []
        )
    except json.JSONDecodeError as e:
        logger.error("Failed to parse pose data JSON for video %s: %s", video_id, e)
        raise RuntimeError("Failed to parse pose detection data") from e

    # Build frame_index -> ball (x, y, confidence) from ball_detection if available
    ball_by_frame: Dict[int, tuple] = {}
    ball_detection = (
        db.query(BallDetection)
        .filter(
            BallDetection.video_id == video_id,
            BallDetection.status == "completed",
        )
        .order_by(BallDetection.created_at.desc())
        .first()
    )
    if ball_detection and ball_detection.ball_data:
        try:
            ball_list = json.loads(ball_detection.ball_data)
            for det in ball_list:
                idx = det.get("frame_index")
                if (
                    idx is not None
                    and det.get("ball_x") is not None
                    and det.get("ball_y") is not None
                ):
                    conf = det.get("confidence")
                    ball_by_frame[idx] = (
                        float(det["ball_x"]),
                        float(det["ball_y"]),
                        float(conf) if conf is not None else 0.0,
                    )
        except (json.JSONDecodeError, TypeError, KeyError):
            pass

    # Get video FPS (required for timestamp calculation)
    fps = video.fps
    if not fps or fps <= 0:
        fps = 30.0  # Default fallback
        logger.warning("Invalid FPS for video %s, using default 30.0", video_id)

    # Format frames
    frames: List[PoseFrame] = []
    for frame_index, frame_data in enumerate(raw_pose_data):
        # Handle both old format (dict of keypoints or None) and new format (dict with frame_index/timestamp_ms/keypoints)
        if isinstance(frame_data, dict) and "keypoints" in frame_data:
            # New format with timestamp_ms
            timestamp_ms = frame_data.get("timestamp_ms", 0.0)
            timestamp = timestamp_ms / 1000.0  # Convert to seconds
            frame_pose_data = frame_data.get("keypoints")
        else:
            # Old format (backward compatibility)
            frame_pose_data = frame_data
            timestamp = frame_index / fps if fps > 0 else 0.0

        # Get confidence for this frame
        confidence = (
            confidence_scores[frame_index]
            if frame_index < len(confidence_scores)
            else 0.0
        )

        # Format keypoints as dict (for frontend consumption)
        # Keep original format: {"left_shoulder": [x, y], ...}
        keypoints_dict: Dict[str, List[float]] = {}
        if frame_pose_data:
            for keypoint_name, coordinates in frame_pose_data.items():
                if isinstance(coordinates, list) and len(coordinates) >= 2:
                    # Store as [x, y] - frontend can add confidence if needed
                    keypoints_dict[keypoint_name] = [
                        float(coordinates[0]),
                        float(coordinates[1]),
                    ]

        ball_pos: Optional[List[float]] = None
        ball_conf: Optional[float] = None
        if frame_index in ball_by_frame:
            bx, by, bc = ball_by_frame[frame_index]
            ball_pos = [bx, by]
            ball_conf = bc

        frames.append(
            PoseFrame(
                frame_index=frame_index,
                timestamp=timestamp,
                keypoints=keypoints_dict,
                confidence=float(confidence) if confidence is not None else 0.0,
                ball_position=ball_pos,
                ball_confidence=ball_conf,
            )
        )

    # Get video dimensions
    width = video.width or 0
    height = video.height or 0

    return PoseOverlayData(
        video_id=video_id,
        fps=fps,
        total_frames=pose_detection.total_frames,
        width=width,
        height=height,
        frames=frames,
    )
