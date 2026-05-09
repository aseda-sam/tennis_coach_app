"""Measure ball-detection rates per serve window across one or more videos.

Used to baseline + tune the YOLO confidence threshold and spline smoother
parameters after the static-distractor / displacement-gate fix (ADR 005).
The numbers in `backend/docs/ball-detection-fine-tuning.md` were measured
under the old pipeline and don't reflect post-fix behavior.

Per serve window we report three numbers:
  - raw:    frames where YOLO+ByteTrack picked up the moving-ball track
            (interpolated == False, ball_x not None)
  - spline: frames filled by cubic spline interpolation
  - empty:  1 if the window has zero positions (real or splined), else 0

Usage:
    docker compose exec backend python scripts/measure_ball_detection.py \
        --video-ids 29 37 38 39

    # Override pipeline parameters for tuning experiments:
    docker compose exec backend python scripts/measure_ball_detection.py \
        --video-ids 39 \
        --confidence 0.4 \
        --max-gap 8 \
        --min-anchors 4
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path
from typing import Any

# Ensure backend app is importable
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from sqlalchemy.orm import Session

from app.core.database import SessionLocal
from app.models.serve_window import ServeWindow
from app.models.video import Video
from app.services.storage_service import storage_service


def _classify_frame(d: dict[str, Any]) -> str:
    """Returns 'raw', 'spline', or 'empty' for a single per-frame detection dict."""
    if d.get("ball_x") is None:
        return "empty"
    return "spline" if d.get("interpolated") else "raw"


def _windows_for_video(db: Session, video_id: int) -> list[dict[str, float]]:
    accepted = (
        db.query(ServeWindow)
        .filter(ServeWindow.video_id == video_id, ServeWindow.status == "accepted")
        .order_by(ServeWindow.start_timestamp)
        .all()
    )
    return [
        {
            "start_ms": sw.start_timestamp * 1000.0,
            "end_ms": sw.end_timestamp * 1000.0,
        }
        for sw in accepted
    ]


def _bucket_per_window(
    detections: list[dict[str, Any]],
    windows: list[dict[str, float]],
    padding_ms: float,
) -> list[list[dict[str, Any]]]:
    """Group per-frame detection dicts back into per-window buckets."""
    buckets: list[list[dict[str, Any]]] = [[] for _ in windows]
    for d in detections:
        ts = d.get("timestamp_ms", 0.0)
        for i, w in enumerate(windows):
            if w["start_ms"] - padding_ms <= ts <= w["end_ms"] + padding_ms:
                buckets[i].append(d)
                break
    return buckets


def measure_video(
    video_id: int,
    *,
    confidence: float,
    max_gap_frames: int,
    min_anchors: int,
    padding_ms: float = 300.0,
) -> dict[str, Any]:
    """Run analyze_serve_windows on one video with the given parameters.

    Returns a result dict with per-window and per-video aggregates.
    """
    # Lazy-import the service so the script can be loaded without ML deps
    from app.services.ball_detection import YoloBallDetectionService
    from app.services.ball_detection import trajectory_smoother as ts_module
    from app.services.ball_detection import yolo_detection_service as yds

    # Apply parameter overrides. The smoother is constructed inside
    # analyze_serve_windows with hard-coded params; patch the module
    # constants so the next construction picks them up.
    original_max_gap = ts_module.MAX_GAP_FRAMES
    original_min_anchors = ts_module.MIN_ANCHORS
    ts_module.MAX_GAP_FRAMES = max_gap_frames
    ts_module.MIN_ANCHORS = min_anchors

    # The service constructs TrajectorySmoother(max_gap_frames=15, min_anchors=2)
    # explicitly with literals. To force our values we replace the symbol with
    # a wrapper that ignores any args the caller passes in and uses the
    # closure-captured experiment params.
    original_smoother_cls = yds.TrajectorySmoother
    forced_max_gap = max_gap_frames
    forced_min_anchors = min_anchors

    def _smoother_factory(*_args, **_kwargs):  # noqa: ANN002, ANN003, ANN202
        return original_smoother_cls(
            max_gap_frames=forced_max_gap, min_anchors=forced_min_anchors
        )

    yds.TrajectorySmoother = _smoother_factory  # type: ignore[assignment]

    try:
        with SessionLocal() as db:
            video = db.query(Video).filter(Video.id == video_id).first()
            if not video:
                raise RuntimeError(f"video {video_id} not found")
            # Use storage_service to resolve DB paths (handles both Docker
            # /app/data/... and host /Users/.../data/... absolute paths).
            video_path = storage_service.get_local_file_path(video.file_path)
            filename = video.filename
            windows = _windows_for_video(db, video_id)

        if not windows:
            return {
                "video_id": video_id,
                "filename": filename,
                "windows": [],
                "totals": {"raw": 0, "spline": 0, "empty": 0, "total_frames": 0},
                "warning": "no accepted serve windows",
            }

        svc = YoloBallDetectionService()
        result = svc.analyze_serve_windows(
            video_path=video_path,
            windows=windows,
            padding_ms=padding_ms,
            confidence=confidence,
        )
        if "error" in result:
            return {
                "video_id": video_id,
                "filename": filename,
                "error": result["error"],
            }

        buckets = _bucket_per_window(
            result["ball_detections"], windows, padding_ms=padding_ms
        )

        per_window = []
        agg_raw = agg_spline = agg_empty = agg_total = 0
        for i, bucket in enumerate(buckets):
            counts = {"raw": 0, "spline": 0, "empty_frames": 0}
            for d in bucket:
                kind = _classify_frame(d)
                if kind == "raw":
                    counts["raw"] += 1
                elif kind == "spline":
                    counts["spline"] += 1
                else:
                    counts["empty_frames"] += 1
            total = len(bucket)
            window_empty = (counts["raw"] + counts["spline"]) == 0
            per_window.append(
                {
                    "index": i + 1,
                    "start_ms": windows[i]["start_ms"],
                    "end_ms": windows[i]["end_ms"],
                    "frames": total,
                    "raw": counts["raw"],
                    "spline": counts["spline"],
                    "empty_frames": counts["empty_frames"],
                    "empty_window": window_empty,
                }
            )
            agg_raw += counts["raw"]
            agg_spline += counts["spline"]
            agg_empty += 1 if window_empty else 0
            agg_total += total

        return {
            "video_id": video_id,
            "filename": filename,
            "windows": per_window,
            "totals": {
                "raw": agg_raw,
                "spline": agg_spline,
                "empty_windows": agg_empty,
                "total_frames": agg_total,
                "n_windows": len(windows),
            },
        }
    finally:
        # Restore module state so subsequent runs / processes are clean.
        yds.TrajectorySmoother = original_smoother_cls  # type: ignore[assignment]
        ts_module.MAX_GAP_FRAMES = original_max_gap
        ts_module.MIN_ANCHORS = original_min_anchors


def _print_report(
    results: list[dict[str, Any]],
    *,
    confidence: float,
    max_gap_frames: int,
    min_anchors: int,
) -> None:
    print()
    print(
        f"== ball-detection measurement (conf={confidence}, "
        f"max_gap={max_gap_frames}, min_anchors={min_anchors}) =="
    )
    print()
    grand_raw = grand_spline = grand_empty = grand_total = grand_windows = 0
    for r in results:
        if "error" in r:
            print(f"video {r['video_id']} ({r['filename']}): ERROR — {r['error']}")
            continue
        if r.get("warning"):
            print(f"video {r['video_id']} ({r['filename']}): {r['warning']}")
            continue
        t = r["totals"]
        print(f"video {r['video_id']} — {r['filename']}")
        for w in r["windows"]:
            rate_raw = (w["raw"] / w["frames"] * 100) if w["frames"] else 0
            rate_total = (
                ((w["raw"] + w["spline"]) / w["frames"] * 100) if w["frames"] else 0
            )
            tag = " EMPTY" if w["empty_window"] else ""
            print(
                f"  serve {w['index']}: frames={w['frames']:3d}  "
                f"raw={w['raw']:3d} ({rate_raw:5.1f}%)  "
                f"spline={w['spline']:3d}  "
                f"after={rate_total:5.1f}%{tag}"
            )
        print(
            f"  TOTAL: raw={t['raw']}/{t['total_frames']} "
            f"({t['raw'] / t['total_frames'] * 100:.1f}%)  "
            f"spline={t['spline']}  "
            f"after={(t['raw'] + t['spline']) / t['total_frames'] * 100:.1f}%  "
            f"empty_windows={t['empty_windows']}/{t['n_windows']}"
        )
        print()
        grand_raw += t["raw"]
        grand_spline += t["spline"]
        grand_empty += t["empty_windows"]
        grand_total += t["total_frames"]
        grand_windows += t["n_windows"]

    if grand_total:
        print(
            f"GRAND TOTAL: raw={grand_raw}/{grand_total} "
            f"({grand_raw / grand_total * 100:.1f}%)  "
            f"after={(grand_raw + grand_spline) / grand_total * 100:.1f}%  "
            f"empty_windows={grand_empty}/{grand_windows}"
        )


def main() -> None:
    p = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawTextHelpFormatter
    )
    p.add_argument(
        "--video-ids", type=int, nargs="+", required=True, help="Video IDs to measure"
    )
    p.add_argument(
        "--confidence",
        type=float,
        default=0.25,
        help="YOLO confidence threshold (default 0.25)",
    )
    p.add_argument(
        "--max-gap", type=int, default=15, help="Spline max gap in frames (default 15)"
    )
    p.add_argument(
        "--min-anchors",
        type=int,
        default=2,
        help="Spline min anchors per side (default 2)",
    )
    p.add_argument(
        "--padding-ms",
        type=float,
        default=300.0,
        help="Per-window padding in ms (default 300)",
    )
    args = p.parse_args()

    results: list[dict[str, Any]] = []
    for video_id in args.video_ids:
        print(f"--- measuring video {video_id} ---")
        try:
            r = measure_video(
                video_id,
                confidence=args.confidence,
                max_gap_frames=args.max_gap,
                min_anchors=args.min_anchors,
                padding_ms=args.padding_ms,
            )
        except Exception as exc:  # noqa: BLE001
            r = {"video_id": video_id, "filename": "?", "error": str(exc)}
        results.append(r)

    _print_report(
        results,
        confidence=args.confidence,
        max_gap_frames=args.max_gap,
        min_anchors=args.min_anchors,
    )


if __name__ == "__main__":
    main()
