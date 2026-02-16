"""Extended biomechanics angle calculations for tennis serve analysis.

All functions take pose_landmarks dicts with keypoints as [x, y] or [x, y, confidence].
Screen coordinates: Y increases downward.

Reuses _calculate_angle_between_points from posture_analysis.py for 3-point angles.
Reuses midpoint/distance from serve_detection/feature_extractor.py for geometry.
"""

import math
from typing import Dict, List, Optional

import numpy as np

from app.services.posture_analysis import _calculate_angle_between_points
from app.services.serve_detection.feature_extractor import distance, midpoint


def _get_point(pose: Dict, key: str) -> Optional[List[float]]:
    """Extract [x, y] from a keypoint, stripping confidence if present."""
    point = pose.get(key)
    if point is None:
        return None
    return point[:2]


def _torso_length(pose: Dict) -> Optional[float]:
    """Calculate torso length (shoulder midpoint to hip midpoint). Returns None if zero."""
    ls = _get_point(pose, "left_shoulder")
    rs = _get_point(pose, "right_shoulder")
    lh = _get_point(pose, "left_hip")
    rh = _get_point(pose, "right_hip")
    if not all([ls, rs, lh, rh]):
        return None
    shoulder_center = midpoint(ls, rs)
    hip_center = midpoint(lh, rh)
    length = distance(shoulder_center, hip_center)
    return length if length > 0 else None


def calculate_trunk_rotation(pose: Dict) -> Optional[float]:
    """Calculate trunk rotation angle between shoulder line and hip line.

    Measures the angular difference between the shoulder line vector
    and the hip line vector. Returns degrees (0 = aligned).

    Args:
        pose: Keypoints dict with left/right shoulder and hip.

    Returns:
        Rotation angle in degrees, or None if keypoints missing.
    """
    ls = _get_point(pose, "left_shoulder")
    rs = _get_point(pose, "right_shoulder")
    lh = _get_point(pose, "left_hip")
    rh = _get_point(pose, "right_hip")

    if not all([ls, rs, lh, rh]):
        return None

    # Shoulder line vector (left to right)
    shoulder_vec = np.array([rs[0] - ls[0], rs[1] - ls[1]])
    # Hip line vector (left to right)
    hip_vec = np.array([rh[0] - lh[0], rh[1] - lh[1]])

    # Angle between the two vectors
    shoulder_norm = np.linalg.norm(shoulder_vec)
    hip_norm = np.linalg.norm(hip_vec)
    if shoulder_norm == 0 or hip_norm == 0:
        return 0.0

    cos_angle = np.dot(shoulder_vec, hip_vec) / (shoulder_norm * hip_norm)
    cos_angle = np.clip(cos_angle, -1.0, 1.0)
    angle_deg = float(np.degrees(np.arccos(cos_angle)))

    return angle_deg


def calculate_shoulder_abduction(pose: Dict, side: str) -> Optional[float]:
    """Calculate shoulder abduction angle (hip-shoulder-elbow).

    Measures how far the arm is raised from the body. Larger angle = more abducted.
    At trophy position, this is typically 90-110 degrees.

    Args:
        pose: Keypoints dict.
        side: "left" or "right".

    Returns:
        Abduction angle in degrees, or None if invalid side or missing keypoints.
    """
    if side not in ("left", "right"):
        return None

    hip = _get_point(pose, f"{side}_hip")
    shoulder = _get_point(pose, f"{side}_shoulder")
    elbow = _get_point(pose, f"{side}_elbow")

    if not all([hip, shoulder, elbow]):
        return None

    try:
        return _calculate_angle_between_points(hip, shoulder, elbow)
    except (ValueError, ZeroDivisionError):
        return None


def calculate_hip_shoulder_separation(pose: Dict) -> Optional[float]:
    """Calculate hip-shoulder separation angle.

    Uses atan2-based orientation of each line, returning the absolute
    angular difference. Key for loading phase — larger separation means
    more stored rotational energy.

    Args:
        pose: Keypoints dict with left/right shoulder and hip.

    Returns:
        Separation angle in degrees (non-negative), or None if missing keypoints.
    """
    ls = _get_point(pose, "left_shoulder")
    rs = _get_point(pose, "right_shoulder")
    lh = _get_point(pose, "left_hip")
    rh = _get_point(pose, "right_hip")

    if not all([ls, rs, lh, rh]):
        return None

    shoulder_angle = math.atan2(rs[1] - ls[1], rs[0] - ls[0])
    hip_angle = math.atan2(rh[1] - lh[1], rh[0] - lh[0])

    diff = abs(math.degrees(shoulder_angle - hip_angle))
    # Normalize to 0-180
    if diff > 180:
        diff = 360 - diff

    return diff


def calculate_contact_point_height(pose: Dict, side: str) -> Optional[float]:
    """Calculate wrist height relative to shoulder, normalized by torso length.

    Positive = wrist above shoulder (good contact point).
    Negative = wrist below shoulder.

    Args:
        pose: Keypoints dict.
        side: "left" or "right".

    Returns:
        Normalized height (positive = above), or None if missing keypoints.
    """
    if side not in ("left", "right"):
        return None

    wrist = _get_point(pose, f"{side}_wrist")
    shoulder = _get_point(pose, f"{side}_shoulder")

    if not all([wrist, shoulder]):
        return None

    torso = _torso_length(pose)
    if torso is None:
        return None

    # Screen coords: smaller Y = higher. Height above shoulder = shoulder_y - wrist_y.
    height_above = shoulder[1] - wrist[1]
    return float(height_above / torso)


def calculate_racket_drop_depth(pose: Dict, side: str) -> Optional[float]:
    """Calculate racket drop depth (wrist below shoulder), normalized by torso.

    Positive = wrist below shoulder (racket drop).
    Negative = wrist above shoulder.

    Args:
        pose: Keypoints dict.
        side: "left" or "right".

    Returns:
        Normalized depth (positive = below), or None if missing keypoints.
    """
    if side not in ("left", "right"):
        return None

    wrist = _get_point(pose, f"{side}_wrist")
    shoulder = _get_point(pose, f"{side}_shoulder")

    if not all([wrist, shoulder]):
        return None

    torso = _torso_length(pose)
    if torso is None:
        return None

    # Screen coords: larger Y = lower. Depth below shoulder = wrist_y - shoulder_y.
    depth_below = wrist[1] - shoulder[1]
    return float(depth_below / torso)
