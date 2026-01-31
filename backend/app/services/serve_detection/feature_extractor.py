"""Feature extraction from pose data for serve detection."""

import logging
from typing import Dict, List, Optional, Tuple

import numpy as np

logger = logging.getLogger(__name__)


def midpoint(point1: List[float], point2: List[float]) -> List[float]:
    """Calculate midpoint between two points."""
    return [(point1[0] + point2[0]) / 2, (point1[1] + point2[1]) / 2]


def distance(point1: List[float], point2: List[float]) -> float:
    """Calculate Euclidean distance between two points."""
    return np.sqrt((point1[0] - point2[0]) ** 2 + (point1[1] - point2[1]) ** 2)


def normalize_pose(
    pose_data: Dict[str, List[float]], frame_shape: Tuple[int, int, int]
) -> Dict[str, List[float]]:
    """
    Normalize pose keypoints: center on hip midpoint, scale by torso length.

    Args:
        pose_data: Dictionary of keypoint coordinates (x, y) in pixels
        frame_shape: Shape of the frame (height, width, channels)

    Returns:
        Dictionary of normalized keypoint coordinates
    """
    height, width = frame_shape[:2]

    # Calculate hip center (origin)
    left_hip = pose_data.get("left_hip", [width / 2, height / 2])
    right_hip = pose_data.get("right_hip", [width / 2, height / 2])
    hip_center = midpoint(left_hip, right_hip)

    # Calculate shoulder center
    left_shoulder = pose_data.get("left_shoulder", [width / 2, height / 2])
    right_shoulder = pose_data.get("right_shoulder", [width / 2, height / 2])
    shoulder_center = midpoint(left_shoulder, right_shoulder)

    # Calculate torso length (scale factor)
    torso_length = distance(hip_center, shoulder_center)
    if torso_length == 0:
        torso_length = 1.0  # Avoid division by zero

    # Normalize all keypoints
    normalized = {}
    for key, point in pose_data.items():
        # Center on hip midpoint
        centered_x = point[0] - hip_center[0]
        centered_y = point[1] - hip_center[1]
        # Scale by torso length
        normalized[key] = [centered_x / torso_length, centered_y / torso_length]

    return normalized


def extract_frame_features(
    pose_data: Optional[Dict[str, List[float]]],
    prev_pose: Optional[Dict[str, List[float]]],
    fps: float,
    frame_shape: Tuple[int, int, int],
) -> Dict[str, float | bool]:
    """
    Extract serve-relevant features from a single frame's pose data.

    Args:
        pose_data: Current frame pose keypoints (x, y) in pixels, or None if no pose
        prev_pose: Previous frame pose keypoints for velocity calculation, or None
        fps: Video frames per second
        frame_shape: Shape of the frame (height, width, channels)

    Returns:
        Dictionary with features:
        - max_wrist_height: Normalized height of highest wrist above hips
        - any_wrist_above_shoulder: Whether at least one wrist is above shoulder (key serve indicator)
        - both_arms_raised: Whether both wrists are above shoulders (trophy position)
        - max_wrist_velocity: Maximum wrist velocity in pixels/sec
        - knee_hip_ratio: Ratio indicating knee bend (lower = more bend)
        - has_pose: Whether pose was detected in this frame
    """
    if pose_data is None:
        return {
            "max_wrist_height": 0.0,
            "any_wrist_above_shoulder": False,
            "both_arms_raised": False,
            "max_wrist_velocity": 0.0,
            "knee_hip_ratio": 0.0,
            "has_pose": False,
        }

    height, width = frame_shape[:2]

    # Normalize pose
    normalized = normalize_pose(pose_data, frame_shape)

    # Get keypoints (use original pixel coordinates for velocity, normalized for height)
    left_wrist = pose_data.get("left_wrist", [width / 2, height / 2])
    right_wrist = pose_data.get("right_wrist", [width / 2, height / 2])
    left_shoulder = pose_data.get("left_shoulder", [width / 2, height / 2])
    right_shoulder = pose_data.get("right_shoulder", [width / 2, height / 2])
    left_hip = pose_data.get("left_hip", [width / 2, height / 2])
    right_hip = pose_data.get("right_hip", [width / 2, height / 2])
    left_knee = pose_data.get("left_knee", [width / 2, height / 2])
    right_knee = pose_data.get("right_knee", [width / 2, height / 2])

    # Calculate hip center (for height calculations)
    hip_center = midpoint(left_hip, right_hip)

    # 1. Arm height (normalized) - key for trophy/contact detection
    # Higher = more likely in serve motion
    # Y increases downward, so subtract from hip_center Y
    left_wrist_height = (hip_center[1] - left_wrist[1]) / distance(hip_center, left_shoulder) if distance(hip_center, left_shoulder) > 0 else 0.0
    right_wrist_height = (hip_center[1] - right_wrist[1]) / distance(hip_center, right_shoulder) if distance(hip_center, right_shoulder) > 0 else 0.0
    max_wrist_height = max(left_wrist_height, right_wrist_height)

    # Use normalized coordinates for more accurate height calculation
    # Note: After normalization, hip center is at origin [0, 0]
    norm_left_wrist = normalized.get("left_wrist", [0, 0])
    norm_right_wrist = normalized.get("right_wrist", [0, 0])
    norm_left_shoulder = normalized.get("left_shoulder", [0, 0])
    norm_right_shoulder = normalized.get("right_shoulder", [0, 0])

    # Recalculate using normalized coordinates (Y is negative above hips)
    norm_left_wrist_height = -norm_left_wrist[1]  # Negative Y = above hips
    norm_right_wrist_height = -norm_right_wrist[1]
    max_wrist_height = max(norm_left_wrist_height, norm_right_wrist_height)

    # 2. Arm position relative to shoulders
    # In screen coordinates, Y increases downward
    # After normalization, negative Y = above hips
    # Check if wrists are above their respective shoulders
    norm_left_shoulder_y = -norm_left_shoulder[1]  # Height of left shoulder above hips
    norm_right_shoulder_y = -norm_right_shoulder[1]  # Height of right shoulder above hips

    left_wrist_above_shoulder = norm_left_wrist_height > norm_left_shoulder_y
    right_wrist_above_shoulder = norm_right_wrist_height > norm_right_shoulder_y

    # Key feature: ANY wrist above shoulder = likely in serve motion
    any_wrist_above_shoulder = left_wrist_above_shoulder or right_wrist_above_shoulder

    # Both arms raised (trophy position indicator)
    both_arms_raised = left_wrist_above_shoulder and right_wrist_above_shoulder

    # 3. Wrist velocity (if previous frame available)
    if prev_pose is not None:
        dt = 1.0 / fps if fps > 0 else 1.0
        prev_left_wrist = prev_pose.get("left_wrist", [width / 2, height / 2])
        prev_right_wrist = prev_pose.get("right_wrist", [width / 2, height / 2])

        left_wrist_velocity = distance(left_wrist, prev_left_wrist) / dt
        right_wrist_velocity = distance(right_wrist, prev_right_wrist) / dt
        max_wrist_velocity = max(left_wrist_velocity, right_wrist_velocity)
    else:
        max_wrist_velocity = 0.0

    # 4. Knee bend ratio (for loading phase detection)
    # Lower ratio = more bend (knees further below hips)
    avg_knee_y = (left_knee[1] + right_knee[1]) / 2
    avg_hip_y = (left_hip[1] + right_hip[1]) / 2
    torso_length = distance(hip_center, midpoint(left_shoulder, right_shoulder))
    if torso_length == 0:
        torso_length = 1.0
    knee_hip_ratio = (avg_knee_y - avg_hip_y) / torso_length  # Positive = knees below hips

    return {
        "max_wrist_height": max_wrist_height,
        "any_wrist_above_shoulder": any_wrist_above_shoulder,
        "both_arms_raised": both_arms_raised,
        "max_wrist_velocity": max_wrist_velocity,
        "knee_hip_ratio": knee_hip_ratio,
        "has_pose": True,
    }
