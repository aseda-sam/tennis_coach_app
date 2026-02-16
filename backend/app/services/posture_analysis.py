"""
Posture analysis service for tennis coaching.

This module provides lightweight posture utilities used by serve analysis.
"""

import logging
from typing import Dict, List, Optional, Tuple

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
        # Serve-only MVP: ignore non-serve stroke types.
        if stroke_type and stroke_type.lower() != "serve":
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
        logger.error("Error calculating elbow angle: %s", e)
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


def calculate_knee_angle(pose_landmarks: Dict, side: str) -> Optional[float]:
    """
    Calculate knee flexion angle from pose landmarks.

    Args:
        pose_landmarks: Dictionary with keypoint coordinates (x, y, confidence)
                       Expected format: {"left_hip": [x, y, confidence], ...}
        side: Which leg ('left' or 'right')

    Returns:
        Knee flexion angle in degrees (hip-knee-ankle), or None if keypoints missing
    """
    try:
        # Validate side
        if side not in ["left", "right"]:
            logger.warning(f"Invalid side: {side}. Expected 'left' or 'right'")
            return None

        # Extract keypoint coordinates for the specified side
        if side == "right":
            hip = pose_landmarks.get("right_hip")
            knee = pose_landmarks.get("right_knee")
            ankle = pose_landmarks.get("right_ankle")
        else:  # left
            hip = pose_landmarks.get("left_hip")
            knee = pose_landmarks.get("left_knee")
            ankle = pose_landmarks.get("left_ankle")

        # Check if all required keypoints are available
        if not all([hip, knee, ankle]):
            logger.debug(
                f"Insufficient keypoints for {side} leg knee angle calculation"
            )
            return None

        # Calculate knee flexion angle (hip-knee-ankle)
        return _calculate_angle_between_points(
            hip[:2],  # [x, y]
            knee[:2],  # [x, y]
            ankle[:2],  # [x, y]
        )

    except (ValueError, KeyError, IndexError) as e:
        logger.error("Error calculating knee angle: %s", e)
        return None


def calculate_knee_hip_ratio(
    pose_landmarks: Dict, frame_shape: Optional[Tuple[int, int, int]] = None
) -> Optional[float]:
    """
    Calculate knee-hip ratio (normalized by torso length) from pose landmarks.

    Ratio = (avg_knee_y - avg_hip_y) / torso_length. In image coords Y increases
    downward, so a larger positive value means knees further below hips (deeper
    bend). Used by phase segmentation to find the loading frame (deepest bend).

    Args:
        pose_landmarks: Dictionary with keypoint coordinates (x, y, confidence)
        frame_shape: Optional frame shape (height, width, channels) for normalization

    Returns:
        Knee-hip ratio (positive when knees below hips), or None if keypoints missing
    """
    try:
        from app.services.serve_detection.feature_extractor import (
            distance,
            midpoint,
        )

        # Extract keypoints
        left_hip = pose_landmarks.get("left_hip")
        right_hip = pose_landmarks.get("right_hip")
        left_knee = pose_landmarks.get("left_knee")
        right_knee = pose_landmarks.get("right_knee")
        left_shoulder = pose_landmarks.get("left_shoulder")
        right_shoulder = pose_landmarks.get("right_shoulder")

        if not all(
            [left_hip, right_hip, left_knee, right_knee, left_shoulder, right_shoulder]
        ):
            logger.debug("Insufficient keypoints for knee-hip ratio calculation")
            return None

        # Calculate averages
        avg_knee_y = (left_knee[1] + right_knee[1]) / 2
        avg_hip_y = (left_hip[1] + right_hip[1]) / 2
        hip_center = midpoint(left_hip[:2], right_hip[:2])
        shoulder_center = midpoint(left_shoulder[:2], right_shoulder[:2])

        # Calculate torso length (scale factor)
        torso_length = distance(hip_center, shoulder_center)
        if torso_length == 0:
            torso_length = 1.0  # Avoid division by zero

        # Knee-hip ratio: positive = knees below hips
        knee_hip_ratio = (avg_knee_y - avg_hip_y) / torso_length

        return float(knee_hip_ratio)

    except (ValueError, KeyError, IndexError, ImportError) as e:
        logger.error("Error calculating knee-hip ratio: %s", e)
        return None
