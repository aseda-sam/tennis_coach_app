"""
Posture analysis service for tennis coaching.

This module provides functions to analyze player posture at ball contact moments.
Starting with simple elbow angle calculation as MVP.
"""

import json
import logging
from typing import Dict, List, Optional

import numpy as np
from sqlalchemy.orm import Session

from app.models.ball_contact import BallContact
from app.models.pose_detection import PoseDetection
from app.models.video import Video

logger = logging.getLogger(__name__)


def calculate_elbow_angle(
    pose_landmarks: Dict, contact_hand: str, stroke_type: Optional[str] = None
) -> Optional[float]:
    """
    Calculate elbow angle from pose landmarks for the contact hand.

    Args:
        pose_landmarks: Dictionary with keypoint coordinates (x, y, confidence)
                       Expected format: {"left_elbow": [x, y, confidence], ...}
        contact_hand: Which hand made contact ('left' or 'right')
        stroke_type: Type of stroke (optional, for future use)

    Returns:
        Elbow angle in degrees, or None if keypoints missing or invalid stroke type
    """
    try:
        # For now, focus on forehands only (single-handed strokes)
        # Backhands with both hands on racket are more complex and will be handled later
        if stroke_type and stroke_type.lower() not in ["forehand", "ground_stroke"]:
            logger.info(
                f"Skipping elbow angle calculation for stroke type: {stroke_type}"
            )
            return None

        # Validate contact hand
        if contact_hand not in ["left", "right"]:
            logger.warning(
                f"Invalid contact hand: {contact_hand}. Expected 'left' or 'right'"
            )
            return None

        # Extract keypoint coordinates for the contact hand
        if contact_hand == "right":
            shoulder = pose_landmarks.get("right_shoulder")
            elbow = pose_landmarks.get("right_elbow")
            wrist = pose_landmarks.get("right_wrist")
        else:  # left
            shoulder = pose_landmarks.get("left_shoulder")
            elbow = pose_landmarks.get("left_elbow")
            wrist = pose_landmarks.get("left_wrist")

        # Check if all required keypoints are available
        if not all([shoulder, elbow, wrist]):
            logger.warning(
                f"Insufficient keypoints for {contact_hand} arm elbow angle calculation"
            )
            return None

        # Calculate elbow angle
        return _calculate_angle_between_points(
            shoulder[:2],  # [x, y]
            elbow[:2],  # [x, y]
            wrist[:2],  # [x, y]
        )

    except (ValueError, KeyError, IndexError) as e:
        logger.error(f"Error calculating elbow angle: {e}")
        return None


def _calculate_angle_between_points(
    point1: List[float], point2: List[float], point3: List[float]
) -> float:
    """
    Calculate angle between three points using vector math.

    Args:
        point1: First point [x, y] (e.g., shoulder)
        point2: Second point [x, y] (e.g., elbow) - vertex of angle
        point3: Third point [x, y] (e.g., wrist)

    Returns:
        Angle in degrees
    """
    # Convert to numpy arrays
    p1 = np.array(point1)
    p2 = np.array(point2)  # vertex
    p3 = np.array(point3)

    # Calculate vectors
    v1 = p1 - p2  # vector from elbow to shoulder
    v2 = p3 - p2  # vector from elbow to wrist

    # Calculate angle using dot product
    cos_angle = np.dot(v1, v2) / (np.linalg.norm(v1) * np.linalg.norm(v2))

    # Clamp to avoid numerical errors
    cos_angle = np.clip(cos_angle, -1.0, 1.0)

    # Convert to degrees
    angle_rad = np.arccos(cos_angle)
    angle_deg = np.degrees(angle_rad)

    return float(angle_deg)


def get_pose_at_contact(
    ball_contact: BallContact, pose_detection: PoseDetection, video: Video
) -> Optional[Dict]:
    """
    Get pose data for the frame closest to ball contact timestamp.

    Args:
        ball_contact: BallContact object with video_timestamp
        pose_detection: PoseDetection object with pose_data
        video: Video object with fps metadata

    Returns:
        Pose landmarks for contact frame, or None if not found
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

        # Get video FPS to convert timestamp to frame index
        fps = video.fps if video.fps else 30.0  # Use actual FPS or fallback to 30
        logger.debug(f"Using FPS: {fps} for video {video.id}")

        # Calculate target frame index
        target_frame = int(ball_contact.video_timestamp * fps)

        # Find the closest available frame
        if target_frame < len(raw_pose_data):
            frame_data = raw_pose_data[target_frame]
            if frame_data is not None:
                return frame_data

        # If exact frame not found, search for nearest frame with pose data
        for offset in range(1, min(10, len(raw_pose_data))):  # Search within 10 frames
            # Try frames before and after
            for direction in [-1, 1]:
                frame_idx = target_frame + (offset * direction)
                if 0 <= frame_idx < len(raw_pose_data):
                    frame_data = raw_pose_data[frame_idx]
                    if frame_data is not None:
                        logger.info(
                            f"Using frame {frame_idx} (offset {offset * direction}) for contact at {ball_contact.video_timestamp}s"
                        )
                        return frame_data

        logger.warning(
            f"No pose data found near timestamp {ball_contact.video_timestamp}s"
        )
        return None

    except (json.JSONDecodeError, ValueError, KeyError) as e:
        logger.error(f"Error getting pose at contact: {e}")
        return None


def analyze_contact_posture(db: Session, ball_contact_id: int) -> Optional[float]:
    """
    Analyze posture for a specific ball contact.

    Args:
        db: Database session
        ball_contact_id: ID of the ball contact to analyze

    Returns:
        Calculated elbow angle, or None if analysis failed
    """
    try:
        # Fetch ball contact
        ball_contact = (
            db.query(BallContact).filter(BallContact.id == ball_contact_id).first()
        )

        if not ball_contact:
            logger.error(f"Ball contact {ball_contact_id} not found")
            return None

        # Fetch video for FPS metadata
        video = db.query(Video).filter(Video.id == ball_contact.video_id).first()
        if not video:
            logger.error(f"Video {ball_contact.video_id} not found")
            return None

        # Fetch pose detection for the same video
        pose_detection = (
            db.query(PoseDetection)
            .filter(
                PoseDetection.video_id == ball_contact.video_id,
                PoseDetection.status == "completed",
            )
            .first()
        )

        if not pose_detection:
            logger.error(
                f"No completed pose detection found for video {ball_contact.video_id}"
            )
            return None

        # Get pose data at contact moment
        pose_landmarks = get_pose_at_contact(ball_contact, pose_detection, video)

        if not pose_landmarks:
            logger.error(f"No pose data found for contact {ball_contact_id}")
            return None

        # Calculate elbow angle using contact hand and stroke type
        elbow_angle = calculate_elbow_angle(
            pose_landmarks, ball_contact.contact_hand, ball_contact.stroke_type
        )

        if elbow_angle is not None:
            logger.info(
                f"Calculated elbow angle {elbow_angle:.1f}° for {ball_contact.contact_hand}-handed {ball_contact.stroke_type or 'stroke'} contact {ball_contact_id}"
            )
        else:
            logger.warning(
                f"Failed to calculate elbow angle for contact {ball_contact_id} (hand: {ball_contact.contact_hand}, stroke: {ball_contact.stroke_type})"
            )

        return elbow_angle

    except (ValueError, KeyError, AttributeError) as e:
        logger.error(f"Error analyzing contact posture: {e}")
        return None
