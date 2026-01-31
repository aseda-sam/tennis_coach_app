"""Heuristic-based serve window detection using pose features."""

import logging
from typing import Dict, List

logger = logging.getLogger(__name__)

# Duration thresholds for valid serve windows
MIN_SERVE_DURATION = 0.5  # seconds - minimum time for a serve motion
MAX_SERVE_DURATION = 8.0  # seconds - maximum time (includes setup)

# Gap threshold for merging nearby "arm raised" segments
# If there's a brief dip (e.g., 0.3s) between raised arm frames, merge them
GAP_MERGE_THRESHOLD = 0.5  # seconds

# Padding to add before/after detected serve windows
# Captures the setup and follow-through
PADDING_BEFORE = 0.3  # seconds before first "arm raised" frame
PADDING_AFTER = 0.5  # seconds after last "arm raised" frame

# Confidence weights
CONFIDENCE_WEIGHTS = {
    "peak_height": 0.3,
    "velocity_spike": 0.3,
    "both_arms": 0.2,
    "duration": 0.2,
}


def cluster_frames(frame_indices: List[int], gap_threshold: int) -> List[List[int]]:
    """
    Cluster frame indices that are within gap_threshold frames of each other.

    Args:
        frame_indices: List of frame indices to cluster
        gap_threshold: Maximum gap between frames to be in same cluster

    Returns:
        List of clusters, each cluster is a list of frame indices
    """
    if not frame_indices:
        return []

    sorted_frames = sorted(frame_indices)
    clusters: List[List[int]] = []
    current_cluster = [sorted_frames[0]]

    for i in range(1, len(sorted_frames)):
        if sorted_frames[i] - sorted_frames[i - 1] <= gap_threshold:
            current_cluster.append(sorted_frames[i])
        else:
            clusters.append(current_cluster)
            current_cluster = [sorted_frames[i]]

    clusters.append(current_cluster)
    return clusters


def calculate_confidence(
    peak_height: float,
    peak_velocity: float,
    both_arms: bool,
    duration: float,
) -> float:
    """
    Calculate confidence score for a serve window proposal.

    Args:
        peak_height: Maximum wrist height (normalized by torso length)
        peak_velocity: Maximum wrist velocity (pixels/sec)
        both_arms: Whether both arms were raised
        duration: Window duration in seconds

    Returns:
        Confidence score between 0.0 and 1.0
    """
    # Normalize height score
    # A height of 1.0 = wrist is 1 torso length above hips (good trophy position)
    # A height of 1.5+ = excellent reach (max score)
    height_score = min(peak_height / 1.5, 1.0) if peak_height > 0 else 0.0

    # Normalize velocity score
    # 400+ pixels/sec is a fast swing (max score)
    velocity_score = min(peak_velocity / 400.0, 1.0) if peak_velocity > 0 else 0.0

    # Duration score (optimal around 2-4 seconds for a full serve motion)
    if duration < MIN_SERVE_DURATION or duration > MAX_SERVE_DURATION:
        duration_score = 0.0
    elif 2.0 <= duration <= 4.0:
        duration_score = 1.0
    else:
        # Linear falloff from optimal range
        if duration < 2.0:
            duration_score = (duration - MIN_SERVE_DURATION) / (2.0 - MIN_SERVE_DURATION)
        else:
            duration_score = (MAX_SERVE_DURATION - duration) / (MAX_SERVE_DURATION - 4.0)

    # Weighted combination
    confidence = (
        CONFIDENCE_WEIGHTS["peak_height"] * height_score
        + CONFIDENCE_WEIGHTS["velocity_spike"] * velocity_score
        + CONFIDENCE_WEIGHTS["both_arms"] * (1.0 if both_arms else 0.0)
        + CONFIDENCE_WEIGHTS["duration"] * duration_score
    )

    return min(max(confidence, 0.0), 1.0)  # Clamp to [0, 1]


def merge_overlapping(proposals: List[Dict]) -> List[Dict]:
    """
    Merge overlapping proposals, keeping the one with highest confidence.

    Args:
        proposals: List of proposal dictionaries with start_timestamp, end_timestamp, confidence

    Returns:
        List of merged proposals
    """
    if not proposals:
        return []

    # Sort by start timestamp
    sorted_proposals = sorted(proposals, key=lambda p: p["start_timestamp"])

    merged: List[Dict] = []
    current = sorted_proposals[0]

    for next_proposal in sorted_proposals[1:]:
        # Check if overlapping (within 0.5 seconds)
        overlap_threshold = 0.5
        if next_proposal["start_timestamp"] <= current["end_timestamp"] + overlap_threshold:
            # Merge: extend end timestamp, keep higher confidence
            current["end_timestamp"] = max(current["end_timestamp"], next_proposal["end_timestamp"])
            current["confidence"] = max(current["confidence"], next_proposal["confidence"])
            # Merge detection features (keep peak values)
            if "detection_features" in current and "detection_features" in next_proposal:
                current_features = current["detection_features"]
                next_features = next_proposal["detection_features"]
                current["detection_features"] = {
                    "peak_frame": max(
                        current_features.get("peak_frame", 0),
                        next_features.get("peak_frame", 0),
                    ),
                    "peak_wrist_height": max(
                        current_features.get("peak_wrist_height", 0),
                        next_features.get("peak_wrist_height", 0),
                    ),
                    "peak_wrist_velocity": max(
                        current_features.get("peak_wrist_velocity", 0),
                        next_features.get("peak_wrist_velocity", 0),
                    ),
                }
        else:
            # No overlap, save current and move to next
            merged.append(current)
            current = next_proposal

    merged.append(current)
    return merged


def detect_serve_windows(
    features: List[Dict[str, float | bool]], fps: float
) -> List[Dict[str, float | str | Dict]]:
    """
    Detect serve windows from frame-level features.

    Simple strategy based on wrist-above-shoulder detection:
    1. Find all frames where any wrist is above shoulder level
    2. Group consecutive/nearby frames into windows
    3. Add padding before/after for setup and follow-through

    This is based on the observation that during a serve motion,
    at least one arm (the racket arm) will be raised above shoulder level.

    Args:
        features: List of feature dictionaries per frame
        fps: Video frames per second

    Returns:
        List of proposal dictionaries with start_timestamp, end_timestamp, confidence, detection_features
    """
    if not features or fps <= 0:
        return []

    n_frames = len(features)
    gap_frames = int(GAP_MERGE_THRESHOLD * fps)
    padding_before_frames = int(PADDING_BEFORE * fps)
    padding_after_frames = int(PADDING_AFTER * fps)

    # Log feature statistics for debugging
    poses_count = sum(1 for f in features if f.get("has_pose", False))
    arm_raised_count = sum(1 for f in features if f.get("any_wrist_above_shoulder", False))
    both_raised_count = sum(1 for f in features if f.get("both_arms_raised", False))

    heights = [f.get("max_wrist_height", 0.0) for f in features if f.get("has_pose", False)]
    velocities = [f.get("max_wrist_velocity", 0.0) for f in features if f.get("has_pose", False)]

    logger.info(
        f"Feature stats for {n_frames} frames ({n_frames/fps:.1f}s at {fps:.1f} fps):"
    )
    logger.info(f"  - Frames with pose: {poses_count}")
    logger.info(f"  - Frames with any wrist above shoulder: {arm_raised_count}")
    logger.info(f"  - Frames with both arms raised: {both_raised_count}")
    if heights:
        logger.info(
            f"  - Wrist height range: [{min(heights):.2f}, {max(heights):.2f}]"
        )
        logger.info(
            f"  - Wrist velocity range: [{min(velocities):.1f}, {max(velocities):.1f}]"
        )

    if poses_count == 0:
        logger.warning("No frames with pose data found")
        return []

    # Step 1: Find all frames where any wrist is above shoulder
    # This is the core signal: arm raised = serve in progress
    raised_arm_frames: List[int] = []
    for i, f in enumerate(features):
        if f.get("any_wrist_above_shoulder", False):
            raised_arm_frames.append(i)

    logger.info(
        f"Found {len(raised_arm_frames)} frames with wrist above shoulder "
        f"({100*len(raised_arm_frames)/n_frames:.1f}% of video)"
    )

    if not raised_arm_frames:
        logger.info("No frames with raised arm detected - no serves found")
        return []

    # Step 2: Cluster nearby raised-arm frames into serve windows
    # Merge frames that are within GAP_MERGE_THRESHOLD of each other
    clusters = cluster_frames(raised_arm_frames, gap_frames)

    logger.info(f"Clustered into {len(clusters)} potential serve windows")

    # Step 3: Convert clusters to proposals with padding
    proposals: List[Dict] = []
    for cluster in clusters:
        if not cluster:
            continue

        # Get raw boundaries
        first_raised = min(cluster)
        last_raised = max(cluster)

        # Add padding
        start_frame = max(0, first_raised - padding_before_frames)
        end_frame = min(n_frames - 1, last_raised + padding_after_frames)

        # Convert to timestamps
        start_ts = start_frame / fps
        end_ts = end_frame / fps
        duration = end_ts - start_ts

        # Skip if too short or too long
        if duration < MIN_SERVE_DURATION:
            logger.debug(
                f"Skipping cluster: duration {duration:.2f}s < {MIN_SERVE_DURATION}s"
            )
            continue
        if duration > MAX_SERVE_DURATION:
            logger.debug(
                f"Skipping cluster: duration {duration:.2f}s > {MAX_SERVE_DURATION}s"
            )
            continue

        # Find peak metrics within the cluster for confidence scoring
        peak_height = max(
            features[i].get("max_wrist_height", 0.0) for i in cluster
        )
        peak_velocity = max(
            features[i].get("max_wrist_velocity", 0.0)
            for i in range(start_frame, end_frame + 1)
        )
        both_arms_ever = any(
            features[i].get("both_arms_raised", False) for i in cluster
        )

        confidence = calculate_confidence(
            peak_height=peak_height,
            peak_velocity=peak_velocity,
            both_arms=both_arms_ever,
            duration=duration,
        )

        logger.info(
            f"Serve window: {start_ts:.2f}s - {end_ts:.2f}s "
            f"(duration: {duration:.2f}s, confidence: {confidence:.2f})"
        )

        proposals.append({
            "start_timestamp": start_ts,
            "end_timestamp": end_ts,
            "confidence": confidence,
            "detection_features": {
                "first_raised_frame": first_raised,
                "last_raised_frame": last_raised,
                "raised_frame_count": len(cluster),
                "peak_wrist_height": peak_height,
                "peak_wrist_velocity": peak_velocity,
                "both_arms_raised": both_arms_ever,
            },
        })

    # Step 4: Merge any overlapping proposals
    merged = merge_overlapping(proposals)

    logger.info(f"Final result: {len(merged)} serve windows detected")
    return merged
