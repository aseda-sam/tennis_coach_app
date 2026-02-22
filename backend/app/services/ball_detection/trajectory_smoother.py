"""Post-processing for ball detections (spline interpolation).

Cubic spline interpolation fills short gaps in the trajectory where the detector
missed the ball. Static-object separation is handled upstream by ByteTrack
(objects are assigned persistent track IDs; only the ball's track is kept).
"""

from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)

# Maximum contiguous gap (frames) we will interpolate across
MAX_GAP_FRAMES: int = 8
# Minimum number of anchor detections on *each* side of a gap before interpolating
MIN_ANCHORS: int = 4


def _cubic_spline_interpolate(
    detections: List[Dict[str, Any]],
    max_gap_frames: int = MAX_GAP_FRAMES,
    min_anchors: int = MIN_ANCHORS,
) -> List[Dict[str, Any]]:
    """Stage B: fill short gaps with cubic spline interpolation.

    Identifies contiguous None-runs in ball_x/y. If the gap is short enough
    (≤ max_gap_frames) and there are sufficient anchors on both sides (≥ min_anchors),
    fits a CubicSpline on (timestamp_ms, ball_x) and (timestamp_ms, ball_y) and fills
    in the missing frames. Interpolated frames are marked with "interpolated": True.

    Args:
        detections: List of per-frame dicts (may include frames already suppressed by
                    velocity filter, i.e., ball_x = None).
        max_gap_frames: Gaps longer than this are left as None (likely real occlusion).
        min_anchors: Minimum detected frames required on each side of a gap.

    Returns:
        New list with interpolated frames filled in.
    """
    try:
        from scipy.interpolate import CubicSpline
    except ImportError as exc:
        logger.warning("scipy not available; skipping interpolation: %s", exc)
        return detections

    import numpy as np

    result = [dict(d) for d in detections]
    n = len(result)

    # Mark all existing frames as not-interpolated if not already set
    for d in result:
        if "interpolated" not in d:
            d["interpolated"] = False

    def _detected(i: int) -> bool:
        return result[i].get("ball_x") is not None

    i = 0
    while i < n:
        if not _detected(i):
            # Find end of gap
            gap_start = i
            gap_end = i
            while gap_end < n and not _detected(gap_end):
                gap_end += 1
            # gap_end is first detected frame after gap (or n if gap reaches end)
            gap_length = gap_end - gap_start

            if gap_length <= max_gap_frames and gap_start > 0 and gap_end < n:
                # Count anchors before gap
                before_anchors = [j for j in range(gap_start) if _detected(j)]
                # Count anchors after gap
                after_anchors = [j for j in range(gap_end, n) if _detected(j)]

                if (
                    len(before_anchors) >= min_anchors
                    and len(after_anchors) >= min_anchors
                ):
                    # Collect anchor points: take up to 2*min_anchors on each side
                    anchor_indices = (
                        before_anchors[-min_anchors * 2 :]
                        + after_anchors[: min_anchors * 2]
                    )
                    ts_arr = np.array(
                        [result[j]["timestamp_ms"] for j in anchor_indices], dtype=float
                    )
                    bx_arr = np.array(
                        [result[j]["ball_x"] for j in anchor_indices], dtype=float
                    )
                    by_arr = np.array(
                        [result[j]["ball_y"] for j in anchor_indices], dtype=float
                    )

                    # Fit splines
                    try:
                        cs_x = CubicSpline(ts_arr, bx_arr)
                        cs_y = CubicSpline(ts_arr, by_arr)

                        for g in range(gap_start, gap_end):
                            ts_g = result[g]["timestamp_ms"]
                            result[g]["ball_x"] = float(cs_x(ts_g))
                            result[g]["ball_y"] = float(cs_y(ts_g))
                            result[g]["confidence"] = 0.0
                            result[g]["interpolated"] = True

                        logger.debug(
                            "Interpolated gap of %d frames at indices %d-%d",
                            gap_length,
                            gap_start,
                            gap_end - 1,
                        )
                    except Exception as exc:  # noqa: BLE001
                        logger.debug(
                            "Spline fit failed for gap %d-%d: %s",
                            gap_start,
                            gap_end,
                            exc,
                        )

            i = gap_end
        else:
            i += 1

    return result


class TrajectorySmoother:
    """Apply cubic spline interpolation to fill short gaps in ball detections."""

    def __init__(
        self,
        max_gap_frames: int = MAX_GAP_FRAMES,
        min_anchors: int = MIN_ANCHORS,
    ) -> None:
        self.max_gap_frames = max_gap_frames
        self.min_anchors = min_anchors

    def smooth(self, detections: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Fill short gaps with cubic spline interpolation.

        Each entry in the returned list has the same keys as the input plus:
            "interpolated": bool  — True if this frame was filled by spline.

        Args:
            detections: Raw per-frame detection dicts from YoloBallDetectionService.

        Returns:
            List with short gaps filled by spline interpolation.
        """
        tagged = [
            dict(d, interpolated=d.get("interpolated", False)) for d in detections
        ]
        return _cubic_spline_interpolate(
            tagged,
            max_gap_frames=self.max_gap_frames,
            min_anchors=self.min_anchors,
        )

    # Convenience alias
    def __call__(self, detections: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        return self.smooth(detections)


def smooth_trajectory(
    detections: List[Dict[str, Any]],
    *,
    max_gap_frames: int = MAX_GAP_FRAMES,
    min_anchors: int = MIN_ANCHORS,
) -> List[Dict[str, Any]]:
    """Module-level convenience wrapper around TrajectorySmoother.smooth()."""
    smoother = TrajectorySmoother(
        max_gap_frames=max_gap_frames,
        min_anchors=min_anchors,
    )
    return smoother.smooth(detections)


def get_interpolated_confidence(
    det: Dict[str, Any],
    *,
    non_interpolated_confidence: Optional[float],
) -> Optional[float]:
    """Return the effective confidence to use for contact gating.

    For interpolated frames: always returns 1.0 so the gate does not block
    spline-filled data.
    For non-interpolated frames: returns the stored confidence value (may be None).
    """
    if det.get("interpolated", False):
        return 1.0
    return non_interpolated_confidence
