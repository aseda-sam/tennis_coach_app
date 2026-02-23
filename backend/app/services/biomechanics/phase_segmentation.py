"""Serve phase segmentation using KTP-based detection from pose keypoints.

Segments a serve into 8 Kovacs phases by detecting 4 Key Time Points (KTPs)
and deriving phase intervals from them.

KTPs: Ball Release → Trophy Position → Racket Low Point → Ball Impact

Architecture rationale: see docs/decisions/003-phase-segmentation-redesign.md
"""

import logging
from enum import Enum
from typing import Any, Dict, List, Optional, Tuple

from pydantic import BaseModel

from app.services.serve_detection.feature_extractor import (
    extract_frame_features,
)

logger = logging.getLogger(__name__)

ANALYSIS_VERSION = "phase-seg-v2"

# Default confidence scores per phase
_PHASE_CONFIDENCE: Dict[str, float] = {
    "start": 1.0,
    "release": 0.8,
    "loading": 0.7,
    "cocking": 0.7,
    "acceleration": 0.7,
    "contact": 1.0,
    "deceleration": 0.6,
    "finish": 0.7,
}


class ServePhase(str, Enum):
    START = "start"
    RELEASE = "release"
    LOADING = "loading"
    COCKING = "cocking"
    ACCELERATION = "acceleration"
    CONTACT = "contact"
    DECELERATION = "deceleration"
    FINISH = "finish"


# Ordered list of phases (kept for downstream consumers)
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
    detection_meta: Optional[Dict[str, Any]] = None


def segment_serve_phases(
    pose_frames: List[Optional[Dict]],
    fps: float,
    serve_start: float,
    serve_end: float,
    contact_timestamp: Optional[float],
    dominant_hand: str,
    video_width: int,
    video_height: int,
    contact_source: Optional[str] = None,
) -> PhaseSegmentationResult:
    """Segment a serve into Kovacs 8-stage phases using KTP-based detection.

    Detects 4 Key Time Points (Ball Release, Trophy Position, Racket Low Point,
    Ball Impact) sequentially, then derives 8 phase intervals from them.

    Args:
        pose_frames: List of pose keypoint dicts (one per frame), None for missing.
        fps: Video frames per second.
        serve_start: Serve window start in seconds.
        serve_end: Serve window end in seconds.
        contact_timestamp: Ball contact timestamp in seconds, or None.
        dominant_hand: "left" or "right".
        video_width: Video width in pixels.
        video_height: Video height in pixels.
        contact_source: How contact_timestamp was set — "manual" or "auto".

    Returns:
        PhaseSegmentationResult with detected phases.
    """
    if fps <= 0:
        fps = 30.0

    frame_shape = (video_height, video_width, 3)
    total_frames = len(pose_frames)

    if total_frames == 0:
        phases = [
            _make_phase_window(ServePhase.START, 0, 0, serve_start, serve_start, 1.0)
        ]
        return PhaseSegmentationResult(
            phases=phases,
            analysis_version=ANALYSIS_VERSION,
            total_phases_detected=1,
            total_phases_possible=8,
        )

    # Extract per-frame features
    features = _extract_feature_curves(pose_frames, fps, frame_shape)

    toss_side = "left" if dominant_hand == "right" else "right"
    dom_side = dominant_hand

    # --- Detect 4 Key Time Points sequentially ---
    ktp_meta: Dict[str, Any] = {}

    # KTP 1: Ball Release (constrained to first 40% of serve)
    search_end_br = max(1, int(total_frames * 0.4))
    ball_release, br_meta = _detect_ball_release(pose_frames, toss_side, search_end_br)
    ktp_meta["ball_release"] = br_meta

    # KTP 2: Trophy Position (after ball release, first 70% of remaining)
    br_frame = ball_release if ball_release is not None else 0
    remaining = total_frames - br_frame
    search_end_tp = min(total_frames, br_frame + max(1, int(remaining * 0.7)))
    trophy_position, tp_meta = _detect_trophy_position(
        features, br_frame, search_end_tp
    )
    ktp_meta["trophy_position"] = tp_meta

    # KTP 3: Ball Impact (from contact_timestamp, tagged manually or auto-detected)
    ball_impact = None
    bi_meta: Dict[str, Any] = {"frame": None, "timestamp": None, "method": "not_tagged"}
    if contact_timestamp is not None:
        ball_impact = int((contact_timestamp - serve_start) * fps)
        ball_impact = max(0, min(ball_impact, total_frames - 1))
        bi_method = "ball_detection" if contact_source == "auto" else "user_tagged"
        bi_meta = {
            "frame": ball_impact,
            "timestamp": round(serve_start + ball_impact / fps, 4),
            "method": bi_method,
        }
    ktp_meta["ball_impact"] = bi_meta

    # KTP 4: Racket Low Point (after trophy, before impact or 85% of serve)
    tp_frame = trophy_position if trophy_position is not None else br_frame
    rlp_end = (
        ball_impact if ball_impact is not None else max(1, int(total_frames * 0.85))
    )
    racket_low_point, rlp_meta = _detect_racket_low_point(
        pose_frames, dom_side, tp_frame, rlp_end
    )
    ktp_meta["racket_low_point"] = rlp_meta

    # --- Build detection metadata ---
    detection_meta = {
        "ktps": ktp_meta,
        "feature_curves": _extract_feature_curve_arrays(features),
        "fps": fps,
        "total_frames": total_frames,
    }

    # --- Derive 8 phases from KTPs ---
    phases = _derive_phases_from_ktps(
        total_frames=total_frames,
        fps=fps,
        serve_start=serve_start,
        ball_release=ball_release,
        trophy_position=trophy_position,
        racket_low_point=racket_low_point,
        ball_impact=ball_impact,
        features=features,
        pose_frames=pose_frames,
        dom_side=dom_side,
    )

    return PhaseSegmentationResult(
        phases=phases,
        analysis_version=ANALYSIS_VERSION,
        total_phases_detected=len(phases),
        total_phases_possible=8,
        detection_meta=detection_meta,
    )


# --- Feature extraction ---


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


# --- Feature curve helpers ---


def _extract_feature_curve_arrays(features: List[Dict]) -> Dict[str, List[float]]:
    """Pluck the 3 key feature curves from per-frame feature dicts."""
    return {
        "max_wrist_height": [f.get("max_wrist_height", 0.0) for f in features],
        "knee_hip_ratio": [f.get("knee_hip_ratio", 0.0) for f in features],
        "max_wrist_velocity": [f.get("max_wrist_velocity", 0.0) for f in features],
    }


# --- KTP detectors ---


def _detect_ball_release(
    pose_frames: List[Optional[Dict]], toss_side: str, search_end: int
) -> Tuple[Optional[int], Dict[str, Any]]:
    """Detect ball release: first frame where toss-arm wrist rises above shoulder.

    Constrained to first 40% of serve window to avoid false positives.
    Returns (frame_or_none, metadata_dict).
    """
    wrist_key = f"{toss_side}_wrist"
    shoulder_key = f"{toss_side}_shoulder"
    search_window = [0, search_end]

    for i in range(min(search_end, len(pose_frames))):
        frame = pose_frames[i]
        if frame is None:
            continue
        wrist = frame.get(wrist_key)
        shoulder = frame.get(shoulder_key)
        # Screen coords: smaller Y = higher
        if wrist and shoulder and wrist[1] < shoulder[1]:
            return i, {
                "frame": i,
                "method": "toss_wrist_above_shoulder",
                "search_window": search_window,
            }
    return None, {
        "frame": None,
        "method": "toss_wrist_above_shoulder",
        "search_window": search_window,
    }


def _detect_trophy_position(
    features: List[Dict], search_start: int, search_end: int
) -> Tuple[Optional[int], Dict[str, Any]]:
    """Detect trophy position: peak wrist height with co-occurring knee bend.

    Composite detector:
    1. Find frames where any wrist is above its shoulder.
    2. Among candidates, find peak max_wrist_height.
    3. Validate knee bend co-occurrence (±5 frames must have ≥80% of max knee_hip_ratio).
    4. Fallback: peak max_wrist_height without arm-raise filter (for beginners).

    Returns (frame_or_none, metadata_dict).
    """
    n = len(features)
    search_end = min(search_end, n)
    search_window = [search_start, search_end]

    if search_start >= search_end:
        return None, {
            "frame": None,
            "method": "no_search_range",
            "search_window": search_window,
        }

    # Find max knee_hip_ratio across entire serve for validation threshold
    all_khr = [
        f.get("knee_hip_ratio", 0.0) for f in features if f.get("has_pose", False)
    ]
    max_khr = max(all_khr) if all_khr else 0.0
    khr_threshold = max_khr * 0.8 if max_khr > 0 else 0.0

    # Find candidate frames: any wrist above shoulder
    candidates = []
    for i in range(search_start, search_end):
        if features[i].get("any_wrist_above_shoulder", False):
            candidates.append((i, features[i].get("max_wrist_height", 0.0)))

    if candidates:
        # Sort by wrist height descending
        candidates.sort(key=lambda x: x[1], reverse=True)

        # Try each candidate, validate knee bend co-occurrence
        for candidates_tried, (frame_idx, wrist_height) in enumerate(
            candidates, start=1
        ):
            if _validate_knee_bend(features, frame_idx, khr_threshold):
                knee_ratio = features[frame_idx].get("knee_hip_ratio", 0.0)
                return frame_idx, {
                    "frame": frame_idx,
                    "method": "peak_wrist_height_with_knee_validation",
                    "search_window": search_window,
                    "wrist_height": round(wrist_height, 4),
                    "knee_validation": True,
                    "knee_ratio_at_frame": round(knee_ratio, 4),
                    "knee_threshold": round(khr_threshold, 4),
                    "candidates_tried": candidates_tried,
                }

        # No candidate passed knee validation — return highest wrist height
        best_idx, best_height = candidates[0]
        knee_ratio = features[best_idx].get("knee_hip_ratio", 0.0)
        return best_idx, {
            "frame": best_idx,
            "method": "peak_wrist_height_no_knee_validation",
            "search_window": search_window,
            "wrist_height": round(best_height, 4),
            "knee_validation": False,
            "knee_ratio_at_frame": round(knee_ratio, 4),
            "knee_threshold": round(khr_threshold, 4),
            "candidates_tried": len(candidates),
        }

    # Fallback: no wrist-above-shoulder frames — peak max_wrist_height
    best_frame = None
    best_height = -1.0
    for i in range(search_start, search_end):
        h = features[i].get("max_wrist_height", 0.0)
        if features[i].get("has_pose", False) and h > best_height:
            best_height = h
            best_frame = i
    return best_frame, {
        "frame": best_frame,
        "method": "fallback_peak_wrist_height",
        "search_window": search_window,
        "wrist_height": round(best_height, 4) if best_height >= 0 else None,
    }


def _validate_knee_bend(
    features: List[Dict], frame_idx: int, khr_threshold: float
) -> bool:
    """Check if knee bend co-occurs with the candidate frame (±5 frames)."""
    if khr_threshold <= 0:
        return True  # No knee bend data — skip validation

    n = len(features)
    window_start = max(0, frame_idx - 5)
    window_end = min(n, frame_idx + 6)

    window_ratios = [
        features[j].get("knee_hip_ratio", 0.0)
        for j in range(window_start, window_end)
        if features[j].get("has_pose", False)
    ]
    if not window_ratios:
        return False

    return max(window_ratios) >= khr_threshold


def _detect_racket_low_point(
    pose_frames: List[Optional[Dict]],
    dom_side: str,
    search_start: int,
    search_end: int,
) -> Tuple[Optional[int], Dict[str, Any]]:
    """Detect racket low point: dominant wrist at lowest spatial position.

    Finds the frame where dominant wrist Y is at its maximum (in screen coords,
    higher Y = lower position = racket behind back). Pure spatial check — no
    velocity thresholds, robust to pose jitter.

    Returns (frame_or_none, metadata_dict).
    """
    wrist_key = f"{dom_side}_wrist"
    max_y = -1.0
    best_frame = None
    search_window = [search_start, min(search_end, len(pose_frames))]

    for i in range(search_start, min(search_end, len(pose_frames))):
        frame = pose_frames[i]
        if frame is None:
            continue
        wrist = frame.get(wrist_key)
        if wrist is not None and wrist[1] > max_y:
            max_y = wrist[1]
            best_frame = i

    return best_frame, {
        "frame": best_frame,
        "method": "max_dominant_wrist_y",
        "search_window": search_window,
        "wrist_y": round(max_y, 4) if max_y >= 0 else None,
    }


# --- Post-contact detectors ---


def _smooth_velocities(features: List[Dict], window: int = 3) -> List[Dict]:
    """Return features with smoothed max_wrist_velocity (rolling average)."""
    velocities = [f.get("max_wrist_velocity", 0.0) for f in features]
    n = len(velocities)
    smoothed = []
    for i in range(n):
        start = max(0, i - window // 2)
        end = min(n, i + window // 2 + 1)
        avg_vel = sum(velocities[start:end]) / (end - start)
        feat_copy = dict(features[i])
        feat_copy["max_wrist_velocity"] = avg_vel
        smoothed.append(feat_copy)
    return smoothed


def _detect_finish_frame(
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


# --- Phase derivation ---


def _find_loading_start(
    features: List[Dict], search_start: int, search_end: int
) -> Optional[int]:
    """Find frame with peak knee bend between ball release and trophy position."""
    best_frame = None
    best_ratio = -1.0
    for i in range(search_start, min(search_end, len(features))):
        ratio = features[i].get("knee_hip_ratio", 0.0)
        if features[i].get("has_pose", False) and ratio > best_ratio:
            best_ratio = ratio
            best_frame = i
    return best_frame


def _derive_phases_from_ktps(
    total_frames: int,
    fps: float,
    serve_start: float,
    ball_release: Optional[int],
    trophy_position: Optional[int],
    racket_low_point: Optional[int],
    ball_impact: Optional[int],
    features: List[Dict],
    pose_frames: List[Optional[Dict]],
    dom_side: str,
) -> List[PhaseWindow]:
    """Derive 8 Kovacs phases from 4 Key Time Points.

    Builds a boundary list where each entry marks a phase start frame,
    then converts to PhaseWindows.
    """
    last_frame = max(total_frames - 1, 0)

    # Build boundary list: (frame, phase_that_starts_here)
    boundaries: List[Tuple[int, ServePhase]] = [(0, ServePhase.START)]

    if ball_release is not None:
        boundaries.append((ball_release, ServePhase.RELEASE))

    if trophy_position is not None:
        # Insert Loading before Cocking if knee bend detected between BR and TP
        if ball_release is not None:
            loading_start = _find_loading_start(features, ball_release, trophy_position)
            if (
                loading_start is not None
                and loading_start > ball_release
                and loading_start < trophy_position
            ):
                boundaries.append((loading_start, ServePhase.LOADING))
        boundaries.append((trophy_position, ServePhase.COCKING))

    if racket_low_point is not None:
        boundaries.append((racket_low_point, ServePhase.ACCELERATION))

    if ball_impact is not None:
        boundaries.append((ball_impact, ServePhase.CONTACT))
        contact_end = min(ball_impact + 1, last_frame)

        if contact_end < last_frame:
            finish_frame = _detect_finish_frame(pose_frames, dom_side, ball_impact)
            if finish_frame is not None and finish_frame > contact_end:
                boundaries.append((contact_end, ServePhase.DECELERATION))
                boundaries.append((finish_frame, ServePhase.FINISH))
            else:
                boundaries.append((contact_end, ServePhase.DECELERATION))

    # Convert boundaries to PhaseWindows
    result = []
    for idx in range(len(boundaries)):
        frame, phase = boundaries[idx]
        end_frame = boundaries[idx + 1][0] if idx + 1 < len(boundaries) else last_frame

        start_ts = serve_start + frame / fps
        end_ts = serve_start + end_frame / fps

        result.append(_make_phase_window(phase, frame, end_frame, start_ts, end_ts))

    return result


def _make_phase_window(
    phase: ServePhase,
    start_frame: int,
    end_frame: int,
    start_timestamp: float,
    end_timestamp: float,
    confidence: Optional[float] = None,
) -> PhaseWindow:
    return PhaseWindow(
        phase=phase,
        start_timestamp=round(start_timestamp, 4),
        end_timestamp=round(end_timestamp, 4),
        start_frame=start_frame,
        end_frame=end_frame,
        confidence=confidence
        if confidence is not None
        else _PHASE_CONFIDENCE.get(phase.value, 0.5),
        detected=True,
    )
