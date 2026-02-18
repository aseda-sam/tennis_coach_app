"""Serve phase segmentation using heuristic detection from pose keypoints.

Segments a serve into 8 Kovacs phases by analyzing feature curves
(wrist height, velocity, knee bend) across the serve window.
"""

import logging
from enum import Enum
from typing import Dict, List, Optional, Tuple

import numpy as np
from pydantic import BaseModel

from app.services.serve_detection.feature_extractor import (
    extract_frame_features,
)

logger = logging.getLogger(__name__)

ANALYSIS_VERSION = "phase-seg-v1"

# Heuristic multipliers for phase detection (Kovacs 8-stage model)
ACCELERATION_VELOCITY_MULTIPLIER = (
    2.0  # Wrist velocity > mean * this = acceleration onset
)
DECELERATION_VELOCITY_FRACTION = (
    0.5  # Wrist velocity < peak * this = deceleration onset
)


class ServePhase(str, Enum):
    START = "start"
    RELEASE = "release"
    LOADING = "loading"
    COCKING = "cocking"
    ACCELERATION = "acceleration"
    CONTACT = "contact"
    DECELERATION = "deceleration"
    FINISH = "finish"


# Ordered list of phases for monotonic enforcement
PHASE_ORDER = [
    ServePhase.START,
    ServePhase.RELEASE,
    ServePhase.LOADING,
    ServePhase.COCKING,
    ServePhase.ACCELERATION,
    ServePhase.CONTACT,
    ServePhase.DECELERATION,
    ServePhase.FINISH,
]


class PhaseWindow(BaseModel):
    phase: ServePhase
    start_timestamp: float
    end_timestamp: float
    start_frame: int
    end_frame: int
    confidence: float
    detected: bool


class PhaseSegmentationResult(BaseModel):
    phases: List[PhaseWindow]
    analysis_version: str
    total_phases_detected: int
    total_phases_possible: int


def segment_serve_phases(
    pose_frames: List[Optional[Dict]],
    fps: float,
    serve_start: float,
    serve_end: float,
    contact_timestamp: Optional[float],
    dominant_hand: str,
    video_width: int,
    video_height: int,
) -> PhaseSegmentationResult:
    """Segment a serve into Kovacs 8-stage phases using pose keypoint heuristics.

    Based on Kovacs & Ellenbecker (2011) 8-stage tennis serve model:
    Start, Release, Loading, Cocking, Acceleration, Contact, Deceleration, Finish.

    Args:
        pose_frames: List of pose keypoint dicts (one per frame), None for missing.
        fps: Video frames per second.
        serve_start: Serve window start in seconds.
        serve_end: Serve window end in seconds.
        contact_timestamp: Ball contact timestamp in seconds, or None.
        dominant_hand: "left" or "right".
        video_width: Video width in pixels.
        video_height: Video height in pixels.

    Returns:
        PhaseSegmentationResult with detected phases.
    """
    if fps <= 0:
        fps = 30.0

    frame_shape = (video_height, video_width, 3)
    total_frames = len(pose_frames)

    # Extract per-frame features
    features = _extract_feature_curves(pose_frames, fps, frame_shape)

    # Determine toss arm and dominant arm
    toss_side = "left" if dominant_hand == "right" else "right"
    dom_side = dominant_hand

    # Detect each phase boundary
    detections: Dict[ServePhase, Tuple[int, float]] = {}

    # 1. Start — first frame
    detections[ServePhase.START] = (0, 1.0)

    # 2. Release — toss arm wrist rises above shoulder
    release_frame = _detect_release(pose_frames, toss_side)
    if release_frame is not None:
        detections[ServePhase.RELEASE] = (release_frame, 0.8)

    # 3. Loading — frame with maximum knee-hip ratio (deepest knee bend)
    loading_frame = _detect_loading(features)
    if loading_frame is not None:
        detections[ServePhase.LOADING] = (loading_frame, 0.7)

    # 4. Cocking — both wrists above shoulders + peak wrist height (trophy pose)
    cocking_frame = _detect_cocking(pose_frames, features)
    if cocking_frame is not None:
        detections[ServePhase.COCKING] = (cocking_frame, 0.7)

    # 5. Acceleration — dominant wrist velocity spike
    accel_frame = _detect_acceleration(features)
    if accel_frame is not None:
        detections[ServePhase.ACCELERATION] = (accel_frame, 0.6)

    # 6. Contact — from timestamp
    if contact_timestamp is not None:
        contact_frame = int((contact_timestamp - serve_start) * fps)
        contact_frame = max(0, min(contact_frame, total_frames - 1))
        detections[ServePhase.CONTACT] = (contact_frame, 1.0)

    # 7. Deceleration — dominant wrist velocity drops after contact
    contact_f = detections.get(ServePhase.CONTACT, (None, 0))[0]
    if contact_f is not None:
        decel_frame = _detect_deceleration(features, contact_f)
        if decel_frame is not None:
            detections[ServePhase.DECELERATION] = (decel_frame, 0.6)

    # 8. Finish — dominant wrist drops below shoulder after contact
    if contact_f is not None:
        finish_frame = _detect_finish(pose_frames, dom_side, contact_f)
        if finish_frame is not None:
            detections[ServePhase.FINISH] = (finish_frame, 0.7)

    # Enforce monotonic ordering: remove out-of-order phases
    phases = _enforce_monotonic(detections, total_frames, fps, serve_start, serve_end)

    return PhaseSegmentationResult(
        phases=phases,
        analysis_version=ANALYSIS_VERSION,
        total_phases_detected=len(phases),
        total_phases_possible=8,
    )


def _extract_feature_curves(
    pose_frames: List[Optional[Dict]],
    fps: float,
    frame_shape: Tuple[int, int, int],
) -> List[Dict]:
    """Extract per-frame features using existing feature extractor."""
    features = []
    prev_pose = None
    for frame_data in pose_frames:
        feat = extract_frame_features(frame_data, prev_pose, fps, frame_shape)
        features.append(feat)
        if frame_data is not None:
            prev_pose = frame_data
    return features


def _detect_release(pose_frames: List[Optional[Dict]], toss_side: str) -> Optional[int]:
    """Detect release: first frame where toss-arm wrist rises above shoulder."""
    wrist_key = f"{toss_side}_wrist"
    shoulder_key = f"{toss_side}_shoulder"

    for i, frame in enumerate(pose_frames):
        if frame is None:
            continue
        wrist = frame.get(wrist_key)
        shoulder = frame.get(shoulder_key)
        # Screen coords: smaller Y = higher
        if wrist and shoulder and wrist[1] < shoulder[1]:
            return i
    return None


def _detect_cocking(
    pose_frames: List[Optional[Dict]], features: List[Dict]
) -> Optional[int]:
    """Detect cocking phase onset: both arms raised + peak max_wrist_height (trophy pose)."""
    # Find frames where both arms are raised
    candidates = []
    for i, feat in enumerate(features):
        if feat.get("both_arms_raised", False):
            candidates.append((i, feat.get("max_wrist_height", 0.0)))

    if not candidates:
        return None

    # Pick the frame with highest wrist height among candidates
    best = max(candidates, key=lambda x: x[1])
    return best[0]


def _detect_loading(features: List[Dict]) -> Optional[int]:
    """Detect loading: frame with maximum knee-hip ratio (deepest knee bend).

    knee_hip_ratio is (avg_knee_y - avg_hip_y) / torso_length; in screen coords
    larger Y is lower, so a larger positive ratio means knees further below hips.
    """
    ratios = []
    for i, feat in enumerate(features):
        khr = feat.get("knee_hip_ratio", 0.0)
        if feat.get("has_pose", False) and khr > 0:
            ratios.append((i, khr))

    if not ratios:
        return None

    best = max(ratios, key=lambda x: x[1])
    return best[0]


def _detect_acceleration(features: List[Dict]) -> Optional[int]:
    """Detect acceleration: dominant wrist velocity exceeds 2x mean velocity."""
    velocities = [
        (i, feat.get("max_wrist_velocity", 0.0))
        for i, feat in enumerate(features)
        if feat.get("has_pose", False)
    ]

    if len(velocities) < 3:
        return None

    mean_vel = np.mean([v for _, v in velocities])
    if mean_vel <= 0:
        return None

    threshold = mean_vel * ACCELERATION_VELOCITY_MULTIPLIER

    # Find first frame exceeding threshold
    for i, vel in velocities:
        if vel > threshold:
            return i

    return None


def _detect_deceleration(features: List[Dict], contact_frame: int) -> Optional[int]:
    """Detect deceleration: wrist velocity drops below 50% of peak after contact."""
    # Get peak velocity around/before contact
    pre_contact = [
        feat.get("max_wrist_velocity", 0.0)
        for feat in features[max(0, contact_frame - 5) : contact_frame + 1]
    ]
    if not pre_contact:
        return None

    peak_vel = max(pre_contact)
    if peak_vel <= 0:
        return None

    threshold = peak_vel * DECELERATION_VELOCITY_FRACTION

    # Search after contact
    for i in range(contact_frame + 1, len(features)):
        vel = features[i].get("max_wrist_velocity", 0.0)
        if vel < threshold:
            return i

    return None


def _detect_finish(
    pose_frames: List[Optional[Dict]], dom_side: str, contact_frame: int
) -> Optional[int]:
    """Detect finish: dominant wrist drops below shoulder after contact."""
    wrist_key = f"{dom_side}_wrist"
    shoulder_key = f"{dom_side}_shoulder"

    for i in range(contact_frame + 1, len(pose_frames)):
        frame = pose_frames[i]
        if frame is None:
            continue
        wrist = frame.get(wrist_key)
        shoulder = frame.get(shoulder_key)
        # Screen coords: larger Y = lower
        if wrist and shoulder and wrist[1] > shoulder[1]:
            return i
    return None


def _enforce_monotonic(
    detections: Dict[ServePhase, Tuple[int, float]],
    total_frames: int,
    fps: float,
    serve_start: float,
    serve_end: float,
) -> List[PhaseWindow]:
    """Enforce monotonic phase ordering, discard out-of-order phases."""
    ordered_phases = []
    last_frame = -1

    for phase in PHASE_ORDER:
        if phase not in detections:
            continue
        frame, confidence = detections[phase]
        if frame <= last_frame and phase != ServePhase.START:
            # Out of order — skip this phase
            continue
        ordered_phases.append((phase, frame, confidence))
        last_frame = frame

    # Build PhaseWindows with start/end boundaries
    result = []
    for idx, (phase, frame, confidence) in enumerate(ordered_phases):
        # End frame is start of next phase (or end of serve)
        if idx + 1 < len(ordered_phases):
            end_frame = ordered_phases[idx + 1][1]
        else:
            end_frame = max(total_frames - 1, frame)

        start_ts = serve_start + frame / fps if fps > 0 else serve_start
        end_ts = serve_start + end_frame / fps if fps > 0 else serve_end

        result.append(
            PhaseWindow(
                phase=phase,
                start_timestamp=round(start_ts, 4),
                end_timestamp=round(end_ts, 4),
                start_frame=frame,
                end_frame=end_frame,
                confidence=confidence,
                detected=True,
            )
        )

    return result
