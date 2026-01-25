"""
Posture analysis service for tennis coaching.

This module provides lightweight posture utilities used by serve analysis.
"""

import logging
from typing import Dict, List, Optional

import numpy as np

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
        # Supported stroke types for elbow angle calculation
        # Serves and forehands/ground_strokes are single-handed strokes that work well
        # Backhands with both hands on racket are more complex and will be handled later
        supported_strokes = ["forehand", "ground_stroke", "serve"]
        if stroke_type and stroke_type.lower() not in supported_strokes:
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
