"""Biomechanics metrics computation for a single serve window.

Computes all metrics from pose frames + phase boundaries.
Pure computation — no DB access.
"""

import logging
from typing import Dict, List, Optional

from pydantic import BaseModel

from app.services.biomechanics.phase_segmentation import PhaseWindow
from app.services.biomechanics.posture_analysis import calculate_knee_angle

logger = logging.getLogger(__name__)


# Metadata for API: unit and phase per metric (no thresholds/scoring).
# Only metrics listed here appear in the API response (metrics_to_flat_list).
METRIC_META: Dict[str, Dict[str, str]] = {
    "knee_flexion_min_deg": {"unit": "deg", "phase": "loading"},
    "toss_peak_height": {"unit": "normalized", "phase": "release"},
    "toss_laterality": {"unit": "normalized", "phase": "release"},
}


def metrics_to_nested_dict(metrics: "BiomechanicsMetrics") -> dict:
    """Convert BiomechanicsMetrics to nested {phase: {metric_name: value}} dict for JSONB storage."""
    result: dict = {}
    data = metrics.model_dump()
    for name, meta in METRIC_META.items():
        value = data.get(name)
        if value is not None:
            phase = meta["phase"]
            result.setdefault(phase, {})[name] = value
    return result


def metrics_to_flat_list(nested: dict) -> List[Dict]:
    """Flatten nested JSONB {phase: {name: value}} to API list format.

    Only metrics with entries in METRIC_META are included in the output.
    """
    result = []
    for name, meta in METRIC_META.items():
        value = nested.get(meta["phase"], {}).get(name)
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

    knee_flexion_min_deg: Optional[float] = None
    toss_peak_height: Optional[float] = None
    toss_laterality: Optional[float] = None


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

    # Get contact frame (used to bound knee flexion + feet separation search)
    contact_frame = None
    if contact_timestamp is not None:
        contact_frame = int((contact_timestamp - serve_start) * fps)
        contact_frame = max(0, min(contact_frame, len(pose_frames) - 1))

    # Knee flexion — minimum angle from serve start through contact
    metrics.knee_flexion_min_deg = _compute_min_knee_flexion(pose_frames, contact_frame)

    return metrics


def _compute_min_knee_flexion(
    pose_frames: List[Optional[Dict]],
    contact_frame: Optional[int],
) -> Optional[float]:
    """Compute minimum knee flexion angle from serve start through contact.

    Searches from the beginning of the serve window to contact.  The deepest
    knee bend often occurs at or before trophy position, so we cannot rely on
    the loading-phase boundary (which may be dropped by monotonic enforcement
    when it precedes cocking).  Stopping at contact still excludes
    post-contact landing where a player might crouch.

    Values below 80° are rejected as single-frame pose artifacts.
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

    if min_angle is not None and min_angle < 80.0:
        return None

    return round(min_angle, 1) if min_angle is not None else None
