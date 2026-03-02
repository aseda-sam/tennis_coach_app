"""Serve phase segmentation using KTP-based detection from pose keypoints.

Segments a serve into 4 phases (Toss, Trophy & Load, Acceleration,
Follow-Through) by detecting 4 Key Time Points (KTPs) and deriving
phase intervals from them.  Every serve always produces exactly 4 phases;
missing KTPs trigger fallback boundaries with lower confidence.

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

ANALYSIS_VERSION = "phase-seg-v4"

# Default confidence scores per phase (when KTP boundary is detected)
_PHASE_CONFIDENCE: Dict[str, float] = {
    "toss": 0.8,
    "trophy_load": 0.7,
    "acceleration": 0.7,
    "follow_through": 0.7,
}

# Confidence assigned when using a fallback boundary
_FALLBACK_CONFIDENCE = 0.4

# Trophy position detection constants
_TROPHY_SEARCH_START = 0.15  # 15% of frames (skip pure-setup frames)
_TROPHY_SEARCH_END = 0.50  # 50% of frames (was 70%)
_TOSS_PHASE_MIN_PCT = 0.10  # toss must be >= 10% of total frames
_TOSS_PHASE_MAX_PCT = 0.55  # toss must be <= 55% of total frames


class ServePhase(str, Enum):
    TOSS = "toss"
    TROPHY_LOAD = "trophy_load"
    ACCELERATION = "acceleration"
    FOLLOW_THROUGH = "follow_through"


class ServeMoment(str, Enum):
    BALL_RELEASE = "ball_release"
    TROPHY_POSITION = "trophy_position"
    RACKET_LOW_POINT = "racket_low_point"
    BALL_IMPACT = "ball_impact"


# Ordered list of phases (kept for downstream consumers)
PHASE_ORDER = [
    ServePhase.TOSS,
    ServePhase.TROPHY_LOAD,
    ServePhase.ACCELERATION,
    ServePhase.FOLLOW_THROUGH,
]


class PhaseWindow(BaseModel):
    phase: ServePhase
    start_timestamp: float
    end_timestamp: float
    start_frame: int
    end_frame: int
    confidence: float
    detected: bool


class MomentMarker(BaseModel):
    moment: ServeMoment
    timestamp: Optional[float] = None
    frame: Optional[int] = None
    confidence: float
    detected: bool
    method: Optional[str] = None


class PhaseSegmentationResult(BaseModel):
    phases: List[PhaseWindow]
    moments: List[MomentMarker] = []
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
    """Segment a serve into 4 phases using KTP-based detection.

    Detects 4 Key Time Points (Ball Release, Trophy Position, Racket Low Point,
    Ball Impact) sequentially, then derives 4 phase intervals with fallback
    boundaries when KTPs are missing.

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
        PhaseSegmentationResult with exactly 4 phases and moment markers.
    """
    if fps <= 0:
        fps = 30.0

    frame_shape = (video_height, video_width, 3)
    total_frames = len(pose_frames)

    if total_frames == 0:
        phases, moments = _build_fallback_phases(
            total_frames=0,
            fps=fps,
            serve_start=serve_start,
            serve_end=serve_end,
        )
        return PhaseSegmentationResult(
            phases=phases,
            moments=moments,
            analysis_version=ANALYSIS_VERSION,
            total_phases_detected=4,
            total_phases_possible=4,
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

    # KTP 2: Trophy Position (search within 15-50% of total frames)
    br_frame = ball_release if ball_release is not None else 0
    search_start_tp = max(br_frame, int(total_frames * _TROPHY_SEARCH_START))
    search_end_tp = min(
        total_frames, max(search_start_tp + 1, int(total_frames * _TROPHY_SEARCH_END))
    )
    trophy_position, tp_meta = _detect_trophy_position(
        features, search_start_tp, search_end_tp
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

    # --- Derive 4 phases + moments from KTPs ---
    phases, moments = _derive_phases_from_ktps(
        total_frames=total_frames,
        fps=fps,
        serve_start=serve_start,
        serve_end=serve_end,
        ball_release=ball_release,
        trophy_position=trophy_position,
        racket_low_point=racket_low_point,
        ball_impact=ball_impact,
    )

    return PhaseSegmentationResult(
        phases=phases,
        moments=moments,
        analysis_version=ANALYSIS_VERSION,
        total_phases_detected=4,
        total_phases_possible=4,
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
    """Detect trophy position: peak wrist height within the search window.

    Tiered detector (arm position only — knee bend removed as unreliable):
    Tier 1: both_arms_raised → pick frame with peak max_wrist_height (0.8)
    Tier 2: any_wrist_above_shoulder → pick frame with peak max_wrist_height (0.6)
    Tier 3: peak max_wrist_height in window → low confidence (0.4)

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

    # --- Tier 1: both_arms_raised → peak wrist height (high confidence) ---
    tier1_candidates = [
        (i, features[i].get("max_wrist_height", 0.0))
        for i in range(search_start, search_end)
        if features[i].get("both_arms_raised", False)
    ]
    if tier1_candidates:
        best_idx, best_height = max(tier1_candidates, key=lambda x: x[1])
        return best_idx, {
            "frame": best_idx,
            "method": "both_arms_raised",
            "search_window": search_window,
            "wrist_height": round(best_height, 4),
            "confidence": 0.8,
        }

    # --- Tier 2: any_wrist_above_shoulder → peak wrist height (medium confidence) ---
    tier2_candidates = [
        (i, features[i].get("max_wrist_height", 0.0))
        for i in range(search_start, search_end)
        if features[i].get("any_wrist_above_shoulder", False)
    ]
    if tier2_candidates:
        best_idx, best_height = max(tier2_candidates, key=lambda x: x[1])
        return best_idx, {
            "frame": best_idx,
            "method": "any_wrist_above_shoulder_fallback",
            "search_window": search_window,
            "wrist_height": round(best_height, 4),
            "confidence": 0.6,
        }

    # --- Tier 3: peak max_wrist_height (low confidence) ---
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
        "confidence": _FALLBACK_CONFIDENCE,
    }


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


# --- Velocity smoothing (kept for future use) ---


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


# --- Phase derivation ---


def _build_moment_markers(
    fps: float,
    serve_start: float,
    ball_release: Optional[int],
    trophy_position: Optional[int],
    racket_low_point: Optional[int],
    ball_impact: Optional[int],
    ktp_meta: Optional[Dict[str, Any]] = None,
) -> List[MomentMarker]:
    """Convert detected KTPs into MomentMarker objects."""
    markers = []
    ktp_map = [
        (ServeMoment.BALL_RELEASE, ball_release, "ball_release"),
        (ServeMoment.TROPHY_POSITION, trophy_position, "trophy_position"),
        (ServeMoment.RACKET_LOW_POINT, racket_low_point, "racket_low_point"),
        (ServeMoment.BALL_IMPACT, ball_impact, "ball_impact"),
    ]
    for moment_enum, frame, meta_key in ktp_map:
        method = None
        if ktp_meta and meta_key in ktp_meta:
            method = ktp_meta[meta_key].get("method")
        if frame is not None:
            markers.append(
                MomentMarker(
                    moment=moment_enum,
                    timestamp=round(serve_start + frame / fps, 4),
                    frame=frame,
                    confidence=0.7,
                    detected=True,
                    method=method,
                )
            )
        else:
            markers.append(
                MomentMarker(
                    moment=moment_enum,
                    confidence=0.0,
                    detected=False,
                    method=method,
                )
            )
    return markers


def _build_fallback_phases(
    total_frames: int,
    fps: float,
    serve_start: float,
    serve_end: float,
) -> Tuple[List[PhaseWindow], List[MomentMarker]]:
    """Build 4 fallback phases (all percentage-based) + empty moments."""
    if total_frames <= 0:
        # Degenerate case: zero-length serve
        phases = [
            _make_phase_window(
                p, 0, 0, serve_start, serve_start, _FALLBACK_CONFIDENCE, detected=False
            )
            for p in PHASE_ORDER
        ]
        moments = [
            MomentMarker(moment=m, confidence=0.0, detected=False) for m in ServeMoment
        ]
        return phases, moments

    last_frame = total_frames - 1
    boundaries = [
        0,
        max(1, int(total_frames * 0.3)),
        max(2, int(total_frames * 0.6)),
        max(3, int(total_frames * 0.85)),
    ]
    # Enforce monotonic
    for i in range(1, len(boundaries)):
        boundaries[i] = max(boundaries[i], boundaries[i - 1] + 1)

    phases = []
    for i, phase in enumerate(PHASE_ORDER):
        start_f = boundaries[i]
        end_f = boundaries[i + 1] if i + 1 < len(boundaries) else last_frame
        phases.append(
            _make_phase_window(
                phase,
                start_f,
                end_f,
                serve_start + start_f / fps,
                serve_start + end_f / fps,
                _FALLBACK_CONFIDENCE,
                detected=False,
            )
        )

    moments = [
        MomentMarker(moment=m, confidence=0.0, detected=False) for m in ServeMoment
    ]
    return phases, moments


def _derive_phases_from_ktps(
    total_frames: int,
    fps: float,
    serve_start: float,
    serve_end: float,
    ball_release: Optional[int],
    trophy_position: Optional[int],
    racket_low_point: Optional[int],
    ball_impact: Optional[int],
) -> Tuple[List[PhaseWindow], List[MomentMarker]]:
    """Derive 4 phases + moment markers from 4 Key Time Points.

    Always returns exactly 4 phases. When a KTP boundary is missing,
    a percentage-based fallback is used with lower confidence.
    """
    last_frame = max(total_frames - 1, 0)

    # --- Resolve boundaries with fallbacks ---
    # trophy_load start = trophy_position, fallback to ball_release, fallback to 30%
    trophy_load_start = trophy_position
    trophy_load_detected = trophy_position is not None
    if trophy_load_start is None:
        trophy_load_start = (
            ball_release if ball_release is not None else int(total_frames * 0.3)
        )
        trophy_load_detected = False

    # Percentage guardrails: toss phase must be 10-55% of total frames
    min_frame = int(total_frames * _TOSS_PHASE_MIN_PCT)
    max_frame = int(total_frames * _TOSS_PHASE_MAX_PCT)
    if trophy_load_start < min_frame or trophy_load_start > max_frame:
        trophy_load_start = max(min_frame, min(trophy_load_start, max_frame))
        trophy_load_detected = False

    # acceleration start = racket_low_point, fallback to trophy_position, fallback to 60%
    accel_start = racket_low_point
    accel_detected = racket_low_point is not None
    if accel_start is None:
        accel_start = (
            trophy_position if trophy_position is not None else int(total_frames * 0.6)
        )
        accel_detected = False

    # follow_through start = ball_impact, fallback to 85%
    ft_start = ball_impact
    ft_detected = ball_impact is not None
    if ft_start is None:
        ft_start = int(total_frames * 0.85)
        ft_detected = False

    # Enforce strict monotonic ordering: each boundary > previous
    boundaries = [0, trophy_load_start, accel_start, ft_start]
    for i in range(1, len(boundaries)):
        boundaries[i] = max(boundaries[i], boundaries[i - 1] + 1)
    # Clamp to valid frame range
    boundaries = [min(b, last_frame) for b in boundaries]

    detected_flags = [True, trophy_load_detected, accel_detected, ft_detected]

    phases = []
    for i, phase in enumerate(PHASE_ORDER):
        start_f = boundaries[i]
        end_f = boundaries[i + 1] if i + 1 < len(boundaries) else last_frame
        det = detected_flags[i]
        conf = _PHASE_CONFIDENCE[phase.value] if det else _FALLBACK_CONFIDENCE
        phases.append(
            _make_phase_window(
                phase,
                start_f,
                end_f,
                serve_start + start_f / fps,
                serve_start + end_f / fps,
                conf,
                detected=det,
            )
        )

    moments = _build_moment_markers(
        fps, serve_start, ball_release, trophy_position, racket_low_point, ball_impact
    )

    return phases, moments


def _make_phase_window(
    phase: ServePhase,
    start_frame: int,
    end_frame: int,
    start_timestamp: float,
    end_timestamp: float,
    confidence: Optional[float] = None,
    detected: bool = True,
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
        detected=detected,
    )
