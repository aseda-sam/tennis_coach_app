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

logger = logging.getLogger(__name__)


def calculate_elbow_angle(pose_landmarks: Dict) -> Optional[float]:
    """
    Calculate elbow angle from pose landmarks.

    Args:
        pose_landmarks: Dictionary with keypoint coordinates (x, y, confidence)
                       Expected format: {"left_elbow": [x, y, confidence], ...}

    Returns:
        Elbow angle in degrees, or None if keypoints missing
    """
    try:
        # Extract keypoint coordinates
        # For tennis, we'll use the dominant hand (right hand for most players)
        # TODO: Make this configurable based on player's dominant hand

        # Try right arm first (right-handed players)
        right_shoulder = pose_landmarks.get("right_shoulder")
        right_elbow = pose_landmarks.get("right_elbow")
        right_wrist = pose_landmarks.get("right_wrist")

        if all([right_shoulder, right_elbow, right_wrist]):
            return _calculate_angle_between_points(
                right_shoulder[:2],  # [x, y]
                right_elbow[:2],     # [x, y]
                right_wrist[:2]      # [x, y]
            )

        # Fallback to left arm if right arm not available
        left_shoulder = pose_landmarks.get("left_shoulder")
        left_elbow = pose_landmarks.get("left_elbow")
        left_wrist = pose_landmarks.get("left_wrist")

        if all([left_shoulder, left_elbow, left_wrist]):
            return _calculate_angle_between_points(
                left_shoulder[:2],  # [x, y]
                left_elbow[:2],     # [x, y]
                left_wrist[:2]      # [x, y]
            )

        logger.warning("Insufficient keypoints for elbow angle calculation")
        return None

    except (ValueError, KeyError, IndexError) as e:
        logger.error(f"Error calculating elbow angle: {e}")
        return None


def _calculate_angle_between_points(
    point1: List[float],
    point2: List[float],
    point3: List[float]
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
    ball_contact: BallContact,
    pose_detection: PoseDetection
) -> Optional[Dict]:
    """
    Get pose data for the frame closest to ball contact timestamp.

    Args:
        ball_contact: BallContact object with video_timestamp
        pose_detection: PoseDetection object with pose_data

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
        # For now, we'll use a default FPS or try to estimate
        # TODO: Get actual FPS from video metadata
        estimated_fps = 30.0  # Default assumption

        # Calculate target frame index
        target_frame = int(ball_contact.video_timestamp * estimated_fps)

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
                        logger.info(f"Using frame {frame_idx} (offset {offset * direction}) for contact at {ball_contact.video_timestamp}s")
                        return frame_data

        logger.warning(f"No pose data found near timestamp {ball_contact.video_timestamp}s")
        return None

    except (json.JSONDecodeError, ValueError, KeyError) as e:
        logger.error(f"Error getting pose at contact: {e}")
        return None


def analyze_contact_posture(
    db: Session,
    ball_contact_id: int
) -> Optional[float]:
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
        ball_contact = db.query(BallContact).filter(
            BallContact.id == ball_contact_id
        ).first()

        if not ball_contact:
            logger.error(f"Ball contact {ball_contact_id} not found")
            return None

        # Fetch pose detection for the same video
        pose_detection = db.query(PoseDetection).filter(
            PoseDetection.video_id == ball_contact.video_id,
            PoseDetection.status == "completed"
        ).first()

        if not pose_detection:
            logger.error(f"No completed pose detection found for video {ball_contact.video_id}")
            return None

        # Get pose data at contact moment
        pose_landmarks = get_pose_at_contact(ball_contact, pose_detection)

        if not pose_landmarks:
            logger.error(f"No pose data found for contact {ball_contact_id}")
            return None

        # Calculate elbow angle
        elbow_angle = calculate_elbow_angle(pose_landmarks)

        if elbow_angle is not None:
            logger.info(f"Calculated elbow angle {elbow_angle:.1f}° for contact {ball_contact_id}")
        else:
            logger.warning(f"Failed to calculate elbow angle for contact {ball_contact_id}")

        return elbow_angle

    except (ValueError, KeyError, AttributeError) as e:
        logger.error(f"Error analyzing contact posture: {e}")
        return None
