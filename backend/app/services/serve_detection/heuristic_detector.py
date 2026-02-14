"""Heuristic-based serve window detection using pose features."""

import logging
from dataclasses import dataclass
from typing import Dict, List, Optional

import numpy as np

logger = logging.getLogger(__name__)

# Duration thresholds for valid serve windows
MIN_SERVE_DURATION = 0.5  # seconds - minimum time for a serve motion
MAX_SERVE_DURATION = 8.0  # seconds - maximum time (includes setup)

# Gap threshold for merging nearby "arm raised" segments
# If there's a brief dip (e.g., 0.3s) between raised arm frames, merge them
GAP_MERGE_THRESHOLD = 0.5  # seconds

# For very long raised-arm clusters, use velocity to isolate likely serve motion
LONG_CLUSTER_VELOCITY_THRESHOLD = 80.0  # pixels/sec
LONG_CLUSTER_EXPANSION = 0.8  # seconds around motion bursts

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

# Fallback confidence penalty applied when proposals come from relaxed pass
FALLBACK_CONFIDENCE_PENALTY = 0.15

# Bounds for adaptive velocity threshold
ADAPTIVE_VELOCITY_MIN = 30.0  # pixels/sec - floor for slow-motion clips
ADAPTIVE_VELOCITY_MAX = 120.0  # pixels/sec - ceiling to avoid over-filtering


@dataclass
class AngleProfile:
    """Camera-angle-specific detection parameters."""

    name: str
    # Gap merge tolerance (seconds) - how much gap between arm-raised frames to merge
    gap_merge_threshold: float = GAP_MERGE_THRESHOLD
    # Padding before/after detected windows (seconds)
    padding_before: float = PADDING_BEFORE
    padding_after: float = PADDING_AFTER
    # Velocity threshold for splitting long clusters (pixels/sec)
    long_cluster_velocity_threshold: float = LONG_CLUSTER_VELOCITY_THRESHOLD
    # Expansion around motion bursts (seconds)
    long_cluster_expansion: float = LONG_CLUSTER_EXPANSION
    # Min/max serve duration (seconds)
    min_serve_duration: float = MIN_SERVE_DURATION
    max_serve_duration: float = MAX_SERVE_DURATION
    # Whether to use adaptive (motion-normalized) velocity threshold
    use_adaptive_velocity: bool = True


# Camera angle profiles: tuned detection parameters per angle
ANGLE_PROFILES: Dict[str, AngleProfile] = {
    "behind": AngleProfile(
        name="behind",
        gap_merge_threshold=0.4,
        padding_before=0.3,
        padding_after=0.4,
        long_cluster_velocity_threshold=90.0,
        long_cluster_expansion=0.7,
    ),
    "profile": AngleProfile(
        name="profile",
        gap_merge_threshold=0.6,
        padding_before=0.4,
        padding_after=0.6,
        long_cluster_velocity_threshold=70.0,
        long_cluster_expansion=1.0,
        max_serve_duration=10.0,
    ),
    "unknown": AngleProfile(
        name="unknown",
        gap_merge_threshold=0.5,
        padding_before=0.3,
        padding_after=0.5,
        long_cluster_velocity_threshold=80.0,
        long_cluster_expansion=0.8,
    ),
}

DEFAULT_PROFILE = ANGLE_PROFILES["unknown"]


def get_angle_profile(camera_angle: Optional[str] = None) -> AngleProfile:
    """Get the detection profile for a given camera angle."""
    if camera_angle and camera_angle in ANGLE_PROFILES:
        return ANGLE_PROFILES[camera_angle]
    return DEFAULT_PROFILE


def compute_motion_stats(features: List[Dict[str, float | bool]]) -> Dict[str, float]:
    """
    Compute per-video motion statistics from pose features.

    Used to derive adaptive thresholds that handle slow-motion and
    varied capture cadences without requiring user input.

    Returns:
        Dictionary with velocity percentiles, arm-raise density, and
        other stats for threshold adaptation.
    """
    velocities = [
        f.get("max_wrist_velocity", 0.0)
        for f in features
        if f.get("has_pose", False) and f.get("max_wrist_velocity", 0.0) > 0
    ]
    arm_raised_count = sum(
        1 for f in features if f.get("any_wrist_above_shoulder", False)
    )
    pose_count = sum(1 for f in features if f.get("has_pose", False))

    if not velocities:
        return {
            "velocity_p50": 0.0,
            "velocity_p75": 0.0,
            "velocity_p90": 0.0,
            "velocity_max": 0.0,
            "arm_raise_density": 0.0,
            "pose_density": 0.0,
        }

    vel_array = np.array(velocities)
    total = len(features) if features else 1

    return {
        "velocity_p50": float(np.percentile(vel_array, 50)),
        "velocity_p75": float(np.percentile(vel_array, 75)),
        "velocity_p90": float(np.percentile(vel_array, 90)),
        "velocity_max": float(np.max(vel_array)),
        "arm_raise_density": arm_raised_count / total,
        "pose_density": pose_count / total,
    }


def compute_adaptive_velocity_threshold(
    motion_stats: Dict[str, float],
    base_threshold: float = LONG_CLUSTER_VELOCITY_THRESHOLD,
) -> float:
    """
    Derive a motion-normalized velocity threshold for splitting long clusters.

    For slow-motion clips, absolute velocities are lower because the same
    physical motion spans more frames. We use the video's own velocity
    distribution to set a meaningful threshold, bounded within safe limits.
    """
    p75 = motion_stats.get("velocity_p75", 0.0)
    p90 = motion_stats.get("velocity_p90", 0.0)

    if p90 <= 0:
        return base_threshold

    # Use a threshold between p75 and p90 - frames above this are "active"
    adaptive = p75 + 0.4 * (p90 - p75)

    # Clamp within safe bounds
    adaptive = max(ADAPTIVE_VELOCITY_MIN, min(ADAPTIVE_VELOCITY_MAX, adaptive))

    logger.info(
        "Adaptive velocity threshold: %.1f (p75=%.1f, p90=%.1f, base=%.1f)",
        adaptive,
        p75,
        p90,
        base_threshold,
    )
    return adaptive


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
    max_duration: float = MAX_SERVE_DURATION,
) -> float:
    """
    Calculate confidence score for a serve window proposal.

    Args:
        peak_height: Maximum wrist height (normalized by torso length)
        peak_velocity: Maximum wrist velocity (pixels/sec)
        both_arms: Whether both arms were raised
        duration: Window duration in seconds
        max_duration: Maximum allowed serve duration (profile-dependent)

    Returns:
        Confidence score between 0.0 and 1.0
    """
    # Normalize height score
    height_score = min(peak_height / 1.5, 1.0) if peak_height > 0 else 0.0

    # Normalize velocity score
    velocity_score = min(peak_velocity / 400.0, 1.0) if peak_velocity > 0 else 0.0

    # Duration score (optimal around 2-4 seconds for a full serve motion)
    if duration < MIN_SERVE_DURATION or duration > max_duration:
        duration_score = 0.0
    elif 2.0 <= duration <= 4.0:
        duration_score = 1.0
    else:
        if duration < 2.0:
            duration_score = (duration - MIN_SERVE_DURATION) / (
                2.0 - MIN_SERVE_DURATION
            )
        else:
            duration_score = (max_duration - duration) / (max_duration - 4.0)

    confidence = (
        CONFIDENCE_WEIGHTS["peak_height"] * height_score
        + CONFIDENCE_WEIGHTS["velocity_spike"] * velocity_score
        + CONFIDENCE_WEIGHTS["both_arms"] * (1.0 if both_arms else 0.0)
        + CONFIDENCE_WEIGHTS["duration"] * duration_score
    )

    return min(max(confidence, 0.0), 1.0)


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
        if (
            next_proposal["start_timestamp"]
            <= current["end_timestamp"] + overlap_threshold
        ):
            # Merge: extend end timestamp, keep higher confidence
            current["end_timestamp"] = max(
                current["end_timestamp"], next_proposal["end_timestamp"]
            )
            current["confidence"] = max(
                current["confidence"], next_proposal["confidence"]
            )
            # Merge detection features (keep peak values)
            if (
                "detection_features" in current
                and "detection_features" in next_proposal
            ):
                current_features = current["detection_features"]
                next_features = next_proposal["detection_features"]
                current["detection_features"] = {
                    "first_raised_frame": min(
                        current_features.get("first_raised_frame", 0),
                        next_features.get("first_raised_frame", 0),
                    ),
                    "last_raised_frame": max(
                        current_features.get("last_raised_frame", 0),
                        next_features.get("last_raised_frame", 0),
                    ),
                    "raised_frame_count": current_features.get("raised_frame_count", 0)
                    + next_features.get("raised_frame_count", 0),
                    "peak_wrist_height": max(
                        current_features.get("peak_wrist_height", 0),
                        next_features.get("peak_wrist_height", 0),
                    ),
                    "peak_wrist_velocity": max(
                        current_features.get("peak_wrist_velocity", 0),
                        next_features.get("peak_wrist_velocity", 0),
                    ),
                    "both_arms_raised": current_features.get("both_arms_raised", False)
                    or next_features.get("both_arms_raised", False),
                }
        else:
            # No overlap, save current and move to next
            merged.append(current)
            current = next_proposal

    merged.append(current)
    return merged


def split_long_cluster(
    cluster: List[int],
    features: List[Dict[str, float | bool]],
    fps: float,
    velocity_threshold: float = LONG_CLUSTER_VELOCITY_THRESHOLD,
    expansion: float = LONG_CLUSTER_EXPANSION,
    gap_merge: float = GAP_MERGE_THRESHOLD,
    max_duration: float = MAX_SERVE_DURATION,
    padding_frames: int = 0,
) -> List[List[int]]:
    """
    Split a very long raised-arm cluster into motion-focused subclusters.

    Strategy:
    1) keep frames in the cluster with meaningful wrist velocity
    2) cluster those active frames
    3) expand each active cluster by a small buffer to include setup/release
    4) fallback to a centered segment if no active frames are found

    Args:
        padding_frames: Total padding (before + after) that will be added
            later; subtracted from max_frames so the final padded window
            stays within max_duration.
    """
    if not cluster or fps <= 0:
        return []

    first_frame = min(cluster)
    last_frame = max(cluster)
    max_frames = max(1, int(max_duration * fps) - padding_frames)
    if last_frame - first_frame + 1 <= max_frames:
        return [cluster]

    active_frames = [
        i
        for i in cluster
        if features[i].get("max_wrist_velocity", 0.0) >= velocity_threshold
    ]

    if not active_frames:
        mid = (first_frame + last_frame) // 2
        half = max_frames // 2
        start = max(first_frame, mid - half)
        end = min(last_frame, start + max_frames - 1)
        start = max(first_frame, end - max_frames + 1)
        return [list(range(start, end + 1))]

    expansion_frames = int(expansion * fps)
    active_gap_frames = int(gap_merge * fps)
    active_clusters = cluster_frames(active_frames, active_gap_frames)

    ranges: List[tuple[int, int]] = []
    for active_cluster in active_clusters:
        start = max(first_frame, min(active_cluster) - expansion_frames)
        end = min(last_frame, max(active_cluster) + expansion_frames)
        if end - start + 1 > max_frames:
            peak_frame = max(
                range(start, end + 1),
                key=lambda idx: features[idx].get("max_wrist_velocity", 0.0),
            )
            half = max_frames // 2
            start = max(first_frame, peak_frame - half)
            end = min(last_frame, start + max_frames - 1)
            start = max(first_frame, end - max_frames + 1)
        ranges.append((start, end))

    # Merge overlapping ranges to avoid duplicate windows
    if not ranges:
        return []
    ranges.sort(key=lambda x: x[0])
    merged_ranges = [ranges[0]]
    for start, end in ranges[1:]:
        prev_start, prev_end = merged_ranges[-1]
        if start <= prev_end:
            merged_ranges[-1] = (prev_start, max(prev_end, end))
        else:
            merged_ranges.append((start, end))

    return [list(range(start, end + 1)) for start, end in merged_ranges]


def _run_detection_pass(
    features: List[Dict[str, float | bool]],
    fps: float,
    profile: AngleProfile,
    motion_stats: Dict[str, float],
    pass_label: str = "primary",
) -> List[Dict]:
    """
    Core detection logic factored out so it can be called for both
    the primary pass and the fallback pass with different parameters.

    Returns:
        List of proposal dictionaries (before final merge).
    """
    n_frames = len(features)
    gap_frames = int(profile.gap_merge_threshold * fps)
    padding_before_frames = int(profile.padding_before * fps)
    padding_after_frames = int(profile.padding_after * fps)

    # Determine velocity threshold for splitting long clusters
    if profile.use_adaptive_velocity:
        velocity_threshold = compute_adaptive_velocity_threshold(
            motion_stats, profile.long_cluster_velocity_threshold
        )
    else:
        velocity_threshold = profile.long_cluster_velocity_threshold

    logger.info(
        "[%s] Detection pass with profile=%s, gap=%.2fs, vel_thresh=%.1f, max_dur=%.1fs",
        pass_label,
        profile.name,
        profile.gap_merge_threshold,
        velocity_threshold,
        profile.max_serve_duration,
    )

    # Find all frames where any wrist is above shoulder
    raised_arm_frames: List[int] = [
        i for i, f in enumerate(features) if f.get("any_wrist_above_shoulder", False)
    ]

    logger.info(
        "[%s] Found %d frames with wrist above shoulder (%.1f%% of video)",
        pass_label,
        len(raised_arm_frames),
        100 * len(raised_arm_frames) / n_frames if n_frames else 0,
    )

    if not raised_arm_frames:
        return []

    # Cluster nearby raised-arm frames
    clusters = cluster_frames(raised_arm_frames, gap_frames)
    logger.info("[%s] Clustered into %d potential serve windows", pass_label, len(clusters))

    # Convert clusters to proposals with padding
    proposals: List[Dict] = []
    for cluster in clusters:
        if not cluster:
            continue

        processing_clusters = [cluster]
        raw_duration = (max(cluster) - min(cluster)) / fps
        if raw_duration > profile.max_serve_duration:
            split_clusters = split_long_cluster(
                cluster,
                features,
                fps,
                velocity_threshold=velocity_threshold,
                expansion=profile.long_cluster_expansion,
                gap_merge=profile.gap_merge_threshold,
                max_duration=profile.max_serve_duration,
                padding_frames=padding_before_frames + padding_after_frames,
            )
            if split_clusters:
                logger.info(
                    "[%s] Split long cluster (%.2fs) into %d motion-focused subcluster(s)",
                    pass_label,
                    raw_duration,
                    len(split_clusters),
                )
                processing_clusters = split_clusters

        for candidate_cluster in processing_clusters:
            if not candidate_cluster:
                continue
            first_raised = min(candidate_cluster)
            last_raised = max(candidate_cluster)

            start_frame = max(0, first_raised - padding_before_frames)
            end_frame = min(n_frames - 1, last_raised + padding_after_frames)

            start_ts = start_frame / fps
            end_ts = end_frame / fps
            duration = end_ts - start_ts

            if duration < profile.min_serve_duration:
                logger.debug(
                    "[%s] Skipping cluster: duration %.2fs < %.2fs",
                    pass_label,
                    duration,
                    profile.min_serve_duration,
                )
                continue
            if duration > profile.max_serve_duration:
                logger.debug(
                    "[%s] Skipping cluster: duration %.2fs > %.2fs",
                    pass_label,
                    duration,
                    profile.max_serve_duration,
                )
                continue

            peak_height = max(
                features[i].get("max_wrist_height", 0.0) for i in candidate_cluster
            )
            peak_velocity = max(
                features[i].get("max_wrist_velocity", 0.0)
                for i in range(start_frame, end_frame + 1)
            )
            both_arms_ever = any(
                features[i].get("both_arms_raised", False) for i in candidate_cluster
            )

            confidence = calculate_confidence(
                peak_height=peak_height,
                peak_velocity=peak_velocity,
                both_arms=both_arms_ever,
                duration=duration,
                max_duration=profile.max_serve_duration,
            )

            logger.info(
                "[%s] Serve window: %.2fs - %.2fs (duration: %.2fs, confidence: %.2f)",
                pass_label,
                start_ts,
                end_ts,
                duration,
                confidence,
            )

            proposals.append(
                {
                    "start_timestamp": start_ts,
                    "end_timestamp": end_ts,
                    "confidence": confidence,
                    "detection_features": {
                        "first_raised_frame": first_raised,
                        "last_raised_frame": last_raised,
                        "raised_frame_count": len(candidate_cluster),
                        "peak_wrist_height": peak_height,
                        "peak_wrist_velocity": peak_velocity,
                        "both_arms_raised": both_arms_ever,
                        "detection_pass": pass_label,
                        "profile": profile.name,
                    },
                }
            )

    return proposals


def _build_relaxed_profile(profile: AngleProfile) -> AngleProfile:
    """
    Build a relaxed version of a profile for the fallback pass.

    Widens gaps, extends max duration, lowers velocity threshold,
    and adds more padding -- all bounded to avoid nonsensical values.
    """
    return AngleProfile(
        name=f"{profile.name}_relaxed",
        gap_merge_threshold=min(profile.gap_merge_threshold * 1.5, 1.5),
        padding_before=min(profile.padding_before * 1.5, 1.0),
        padding_after=min(profile.padding_after * 1.5, 1.0),
        long_cluster_velocity_threshold=max(
            profile.long_cluster_velocity_threshold * 0.5, ADAPTIVE_VELOCITY_MIN
        ),
        long_cluster_expansion=min(profile.long_cluster_expansion * 1.5, 2.0),
        min_serve_duration=max(profile.min_serve_duration * 0.6, 0.3),
        max_serve_duration=min(profile.max_serve_duration * 1.25, 12.0),
        use_adaptive_velocity=profile.use_adaptive_velocity,
    )


def detect_serve_windows(
    features: List[Dict[str, float | bool]],
    fps: float,
    camera_angle: Optional[str] = None,
) -> List[Dict[str, float | str | Dict]]:
    """
    Detect serve windows from frame-level features.

    Strategy:
    1. Select camera-angle profile for tuned detection parameters.
    2. Compute per-video motion stats for adaptive thresholds.
    3. Run primary detection pass.
    4. If no proposals found, run a fallback pass with relaxed parameters
       and apply a confidence penalty.

    Args:
        features: List of feature dictionaries per frame
        fps: Video frames per second
        camera_angle: Camera angle metadata ('behind', 'profile', or 'unknown'/None)

    Returns:
        List of proposal dictionaries with start_timestamp, end_timestamp,
        confidence, detection_features
    """
    if not features or fps <= 0:
        return []

    n_frames = len(features)
    profile = get_angle_profile(camera_angle)

    # Log feature statistics for debugging
    poses_count = sum(1 for f in features if f.get("has_pose", False))
    arm_raised_count = sum(
        1 for f in features if f.get("any_wrist_above_shoulder", False)
    )
    both_raised_count = sum(1 for f in features if f.get("both_arms_raised", False))

    heights = [
        f.get("max_wrist_height", 0.0) for f in features if f.get("has_pose", False)
    ]
    velocities = [
        f.get("max_wrist_velocity", 0.0) for f in features if f.get("has_pose", False)
    ]

    logger.info(
        "Feature stats for %d frames (%.1fs at %.1f fps), profile=%s:",
        n_frames,
        n_frames / fps,
        fps,
        profile.name,
    )
    logger.info("  - Frames with pose: %d", poses_count)
    logger.info("  - Frames with any wrist above shoulder: %d", arm_raised_count)
    logger.info("  - Frames with both arms raised: %d", both_raised_count)
    if heights:
        logger.info("  - Wrist height range: [%.2f, %.2f]", min(heights), max(heights))
        logger.info(
            "  - Wrist velocity range: [%.1f, %.1f]", min(velocities), max(velocities)
        )

    if poses_count == 0:
        logger.warning("No frames with pose data found")
        return []

    # Compute motion stats for adaptive thresholds
    motion_stats = compute_motion_stats(features)
    logger.info(
        "Motion stats: p50=%.1f, p75=%.1f, p90=%.1f, max=%.1f, arm_density=%.2f",
        motion_stats["velocity_p50"],
        motion_stats["velocity_p75"],
        motion_stats["velocity_p90"],
        motion_stats["velocity_max"],
        motion_stats["arm_raise_density"],
    )

    # --- Primary detection pass ---
    proposals = _run_detection_pass(
        features, fps, profile, motion_stats, pass_label="primary"
    )
    merged = merge_overlapping(proposals)

    # --- Fallback pass if primary found nothing ---
    if not merged:
        logger.info("Primary pass found no proposals; running fallback pass")
        relaxed_profile = _build_relaxed_profile(profile)
        fallback_proposals = _run_detection_pass(
            features, fps, relaxed_profile, motion_stats, pass_label="fallback"
        )

        # If camera_angle is unknown, also try the other profiles
        if camera_angle in (None, "unknown") and not fallback_proposals:
            for alt_angle in ("behind", "profile"):
                alt_profile = _build_relaxed_profile(ANGLE_PROFILES[alt_angle])
                alt_proposals = _run_detection_pass(
                    features,
                    fps,
                    alt_profile,
                    motion_stats,
                    pass_label=f"fallback_{alt_angle}",
                )
                fallback_proposals.extend(alt_proposals)

        # Apply confidence penalty to fallback proposals
        for p in fallback_proposals:
            p["confidence"] = max(0.0, p["confidence"] - FALLBACK_CONFIDENCE_PENALTY)

        merged = merge_overlapping(fallback_proposals)
        if merged:
            logger.info(
                "Fallback pass recovered %d proposal(s)", len(merged)
            )

    logger.info("Final result: %d serve windows detected", len(merged))
    return merged
