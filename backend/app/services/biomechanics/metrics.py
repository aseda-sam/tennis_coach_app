"""Biomechanics metrics computation for a single serve window.

Computes all metrics from pose frames + phase boundaries.
Pure computation — no DB access.
"""

import logging
from typing import Dict, List, Optional

import numpy as np
from pydantic import BaseModel

from app.services.biomechanics.angle_calculations import (
    calculate_contact_point_height,
    calculate_hip_shoulder_separation,
    calculate_racket_drop_depth,
    calculate_shoulder_abduction,
    calculate_trunk_rotation,
)
from app.services.biomechanics.phase_segmentation import PhaseWindow, ServePhase
from app.services.posture_analysis import calculate_elbow_angle, calculate_knee_angle

logger = logging.getLogger(__name__)


# Metadata for API: unit and phase per metric (no thresholds/scoring)
METRIC_META: Dict[str, Dict[str, str]] = {
    "elbow_angle_at_contact": {"unit": "deg", "phase": "contact"},
    "knee_flexion_min_deg": {"unit": "deg", "phase": "loading"},
    "toss_peak_height": {"unit": "normalized", "phase": "wind_up"},
    "trunk_rotation_at_trophy": {"unit": "deg", "phase": "cocking"},
    "trunk_rotation_at_contact": {"unit": "deg", "phase": "contact"},
    "shoulder_abduction_at_trophy": {"unit": "deg", "phase": "cocking"},
    "shoulder_abduction_at_contact": {"unit": "deg", "phase": "contact"},
    "racket_drop_depth": {"unit": "normalized", "phase": "acceleration"},
    "contact_point_height": {"unit": "normalized", "phase": "contact"},
    "hip_shoulder_separation_max": {"unit": "deg", "phase": "loading"},
    "hip_shoulder_separation_at_contact": {"unit": "deg", "phase": "contact"},
    "kinetic_chain_sequence": {"unit": "", "phase": "acceleration"},
    "kinetic_chain_correct": {"unit": "", "phase": "acceleration"},
    "kinetic_chain_timing_gaps_ms": {"unit": "ms", "phase": "acceleration"},
}


def metrics_to_flat_list(metrics: "BiomechanicsMetrics") -> List[Dict]:
    """Convert BiomechanicsMetrics to flat list of {metric_name, value, unit, phase}."""
    result = []
    data = metrics.model_dump()
    for name, value in data.items():
        # Skip list-valued metrics (API returns scalar values only)
        if isinstance(value, list):
            continue
        # Convert bool to float for kinetic_chain_correct
        if isinstance(value, bool):
            value = 1.0 if value else 0.0
        meta = METRIC_META.get(name, {"unit": "", "phase": None})
        result.append(
            {
                "metric_name": name,
                "value": value,
                "unit": meta["unit"],
                "phase": meta["phase"],
            }
        )
    return result


class BiomechanicsMetrics(BaseModel):
    """All computed metrics for a single serve window."""

    # Existing metrics
    elbow_angle_at_contact: Optional[float] = None
    knee_flexion_min_deg: Optional[float] = None
    toss_peak_height: Optional[float] = None

    # Trunk rotation
    trunk_rotation_at_trophy: Optional[float] = None
    trunk_rotation_at_contact: Optional[float] = None

    # Shoulder
    shoulder_abduction_at_trophy: Optional[float] = None
    shoulder_abduction_at_contact: Optional[float] = None

    # Racket drop
    racket_drop_depth: Optional[float] = None

    # Contact point
    contact_point_height: Optional[float] = None

    # Hip-shoulder separation
    hip_shoulder_separation_max: Optional[float] = None
    hip_shoulder_separation_at_contact: Optional[float] = None

    # Kinetic chain
    kinetic_chain_sequence: Optional[List[str]] = None
    kinetic_chain_correct: Optional[bool] = None
    kinetic_chain_timing_gaps_ms: Optional[List[float]] = None


def compute_biomechanics_metrics(
    pose_frames: List[Optional[Dict]],
    fps: float,
    serve_start: float,
    serve_end: float,
    contact_timestamp: Optional[float],
    dominant_hand: str,
    video_width: int,
    video_height: int,
    phases: Optional[List[PhaseWindow]] = None,
) -> BiomechanicsMetrics:
    """Compute all biomechanics metrics for one serve window.

    Args:
        pose_frames: Pose keypoints per frame within serve window.
        fps: Video FPS.
        serve_start: Start of serve window (seconds).
        serve_end: End of serve window (seconds).
        contact_timestamp: Contact time (seconds), or None.
        dominant_hand: "left" or "right".
        video_width: Video width px.
        video_height: Video height px.
        phases: Phase segmentation result (optional).

    Returns:
        BiomechanicsMetrics with all computed values.
    """
    if fps <= 0:
        fps = 30.0

    metrics = BiomechanicsMetrics()

    if not pose_frames:
        return metrics

    # Get contact frame
    contact_frame = None
    if contact_timestamp is not None:
        contact_frame = int((contact_timestamp - serve_start) * fps)
        contact_frame = max(0, min(contact_frame, len(pose_frames) - 1))

    # Get phase frames
    trophy_frame = _get_phase_frame(phases, ServePhase.COCKING, serve_start, fps)

    # Contact-frame metrics
    if contact_frame is not None and contact_frame < len(pose_frames):
        pose_at_contact = pose_frames[contact_frame]
        if pose_at_contact is not None:
            metrics.elbow_angle_at_contact = calculate_elbow_angle(
                pose_at_contact, dominant_hand, "serve"
            )
            metrics.trunk_rotation_at_contact = calculate_trunk_rotation(
                pose_at_contact
            )
            metrics.shoulder_abduction_at_contact = calculate_shoulder_abduction(
                pose_at_contact, dominant_hand
            )
            metrics.contact_point_height = calculate_contact_point_height(
                pose_at_contact, dominant_hand
            )
            metrics.hip_shoulder_separation_at_contact = (
                calculate_hip_shoulder_separation(pose_at_contact)
            )

    # Trophy-frame metrics
    if trophy_frame is not None and trophy_frame < len(pose_frames):
        pose_at_trophy = pose_frames[trophy_frame]
        if pose_at_trophy is not None:
            metrics.trunk_rotation_at_trophy = calculate_trunk_rotation(pose_at_trophy)
            metrics.shoulder_abduction_at_trophy = calculate_shoulder_abduction(
                pose_at_trophy, dominant_hand
            )

    # Racket drop — minimum wrist position between trophy and contact
    metrics.racket_drop_depth = _compute_racket_drop(
        pose_frames, dominant_hand, trophy_frame, contact_frame
    )

    # Knee flexion — minimum angle from serve start through contact
    metrics.knee_flexion_min_deg = _compute_min_knee_flexion(pose_frames, contact_frame)

    # Hip-shoulder separation — max across all frames
    metrics.hip_shoulder_separation_max = _compute_max_hip_shoulder_separation(
        pose_frames
    )

    # Kinetic chain analysis
    chain = _analyze_kinetic_chain(pose_frames, fps, dominant_hand)
    metrics.kinetic_chain_sequence = chain.get("sequence")
    metrics.kinetic_chain_correct = chain.get("correct")
    metrics.kinetic_chain_timing_gaps_ms = chain.get("timing_gaps_ms")

    return metrics


def _get_phase_frame(
    phases: Optional[List[PhaseWindow]],
    target_phase: ServePhase,
    serve_start: float,
    fps: float,
) -> Optional[int]:
    """Get the start frame index for a given phase."""
    if phases is None:
        return None
    for phase in phases:
        if phase.phase == target_phase:
            return phase.start_frame
    return None


def _compute_racket_drop(
    pose_frames: List[Optional[Dict]],
    dominant_hand: str,
    trophy_frame: Optional[int],
    contact_frame: Optional[int],
) -> Optional[float]:
    """Compute max racket drop depth between trophy and contact."""
    start = trophy_frame or 0
    end = contact_frame or len(pose_frames)
    end = min(end, len(pose_frames))

    max_depth = None
    for i in range(start, end):
        frame = pose_frames[i]
        if frame is None:
            continue
        depth = calculate_racket_drop_depth(frame, dominant_hand)
        if depth is not None and (max_depth is None or depth > max_depth):
            max_depth = depth

    return round(max_depth, 4) if max_depth is not None else None


def _compute_min_knee_flexion(
    pose_frames: List[Optional[Dict]],
    contact_frame: Optional[int],
) -> Optional[float]:
    """Compute minimum knee flexion angle from serve start through contact.

    Searches from the beginning of the serve window to contact.  The deepest
    knee bend often occurs at or before trophy position, so we cannot rely on
    the loading-phase boundary (which may be dropped by monotonic enforcement
    when it precedes cocking/trophy).  Stopping at contact still excludes
    post-contact landing where a player might crouch.
    """
    start = 0
    end = contact_frame + 1 if contact_frame is not None else len(pose_frames)
    end = min(end, len(pose_frames))

    min_angle = None
    for i in range(start, end):
        frame = pose_frames[i]
        if frame is None:
            continue
        for side in ("left", "right"):
            angle = calculate_knee_angle(frame, side)
            if angle is not None and (min_angle is None or angle < min_angle):
                min_angle = angle

    return round(min_angle, 1) if min_angle is not None else None


def _compute_max_hip_shoulder_separation(
    pose_frames: List[Optional[Dict]],
) -> Optional[float]:
    """Find maximum hip-shoulder separation across all frames."""
    max_sep = None
    for frame in pose_frames:
        if frame is None:
            continue
        sep = calculate_hip_shoulder_separation(frame)
        if sep is not None and (max_sep is None or sep > max_sep):
            max_sep = sep

    return round(max_sep, 1) if max_sep is not None else None


def _analyze_kinetic_chain(
    pose_frames: List[Optional[Dict]],
    fps: float,
    dominant_hand: str,
) -> Dict:
    """Analyze kinetic chain sequence from pose velocity data.

    Correct proximal-to-distal sequence: hip → trunk → shoulder → elbow → wrist.
    Detects the frame where each segment's velocity first exceeds a threshold.
    """
    if len(pose_frames) < 5:
        return {"sequence": None, "correct": None, "timing_gaps_ms": None}

    dom = dominant_hand
    segments = {
        "hip": ("left_hip", "right_hip"),
        "trunk": ("left_shoulder", "right_shoulder"),
        "shoulder": (f"{dom}_shoulder", f"{dom}_elbow"),
        "elbow": (f"{dom}_elbow", f"{dom}_wrist"),
        "wrist": (f"{dom}_wrist", None),
    }

    correct_order = ["hip", "trunk", "shoulder", "elbow", "wrist"]

    # Compute velocity for each segment
    segment_onset: Dict[str, Optional[int]] = {}

    for seg_name, keys in segments.items():
        velocities = _compute_segment_velocities(pose_frames, fps, keys)
        if not velocities:
            continue

        mean_vel = (
            np.mean([v for v in velocities if v > 0])
            if any(v > 0 for v in velocities)
            else 0
        )
        threshold = mean_vel * 1.5 if mean_vel > 0 else 0

        # Find first frame exceeding threshold
        for i, vel in enumerate(velocities):
            if vel > threshold and threshold > 0:
                segment_onset[seg_name] = i
                break

    if len(segment_onset) < 3:
        return {"sequence": None, "correct": None, "timing_gaps_ms": None}

    # Sort by onset frame
    sorted_segments = sorted(segment_onset.items(), key=lambda x: x[1])
    sequence = [s[0] for s in sorted_segments]

    # Check if order matches correct proximal-to-distal
    present_correct = [s for s in correct_order if s in sequence]
    is_correct = sequence == present_correct

    # Compute timing gaps
    timing_gaps = []
    for i in range(1, len(sorted_segments)):
        gap_frames = sorted_segments[i][1] - sorted_segments[i - 1][1]
        gap_ms = (gap_frames / fps) * 1000 if fps > 0 else 0
        timing_gaps.append(round(gap_ms, 1))

    return {
        "sequence": sequence,
        "correct": is_correct,
        "timing_gaps_ms": timing_gaps,
    }


def _compute_segment_velocities(
    pose_frames: List[Optional[Dict]],
    fps: float,
    keys: tuple,
) -> List[float]:
    """Compute per-frame velocity for a body segment."""
    velocities = []
    for i in range(1, len(pose_frames)):
        prev = pose_frames[i - 1]
        curr = pose_frames[i]
        if prev is None or curr is None:
            velocities.append(0.0)
            continue

        if keys[1] is None:
            # Single point velocity (wrist)
            p1 = prev.get(keys[0])
            p2 = curr.get(keys[0])
            if p1 and p2:
                dx = p2[0] - p1[0]
                dy = p2[1] - p1[1]
                vel = np.sqrt(dx**2 + dy**2) * fps
                velocities.append(float(vel))
            else:
                velocities.append(0.0)
        else:
            # Midpoint velocity (for segments like hip, trunk)
            p1a = prev.get(keys[0])
            p1b = prev.get(keys[1])
            p2a = curr.get(keys[0])
            p2b = curr.get(keys[1])
            if all([p1a, p1b, p2a, p2b]):
                mid1 = [(p1a[0] + p1b[0]) / 2, (p1a[1] + p1b[1]) / 2]
                mid2 = [(p2a[0] + p2b[0]) / 2, (p2a[1] + p2b[1]) / 2]
                dx = mid2[0] - mid1[0]
                dy = mid2[1] - mid1[1]
                vel = np.sqrt(dx**2 + dy**2) * fps
                velocities.append(float(vel))
            else:
                velocities.append(0.0)

    return velocities
