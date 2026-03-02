"""Export the trophy position frame for every serve window to a single directory.

Usage:
    python scripts/export_trophy_frames.py [--out-dir PATH]

Defaults to data/trophy_frames/ (relative to project root).
Each image is named: <video_filename>__sw<serve_window_id>__f<frame>.jpg
"""

import argparse
import json
import os
import sys

import cv2

# Allow running from repo root or from backend/
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from app.core.database import SessionLocal
from app.models.serve_biomechanics_report import ServeBiomechanicsReport
from app.models.serve_window import ServeWindow
from app.models.video import Video


def main(out_dir: str) -> None:
    os.makedirs(out_dir, exist_ok=True)

    db = SessionLocal()
    try:
        from sqlalchemy import func

        # Latest report per serve window
        latest = (
            db.query(
                ServeBiomechanicsReport.serve_window_id,
                func.max(ServeBiomechanicsReport.id).label("max_id"),
            )
            .group_by(ServeBiomechanicsReport.serve_window_id)
            .subquery()
        )
        rows = (
            db.query(ServeBiomechanicsReport, ServeWindow, Video)
            .join(latest, ServeBiomechanicsReport.id == latest.c.max_id)
            .join(
                ServeWindow, ServeBiomechanicsReport.serve_window_id == ServeWindow.id
            )
            .join(Video, ServeWindow.video_id == Video.id)
            .order_by(Video.id, ServeWindow.id)
            .all()
        )
    finally:
        db.close()

    if not rows:
        print("No biomechanics reports found.")
        return

    print(f"Found {len(rows)} report(s). Exporting trophy frames to: {out_dir}\n")

    ok = 0
    skipped = 0
    for report, sw, video in rows:
        seg = report.phase_segmentation_json or {}
        if isinstance(seg, str):
            seg = json.loads(seg)

        meta = seg.get("detection_meta", {})
        tp = meta.get("ktps", {}).get("trophy_position", {})
        trophy_frame = tp.get("frame")
        method = tp.get("method", "unknown")
        confidence = tp.get("confidence", 0.0)

        video_path = video.file_path
        label = f"{video.filename} / sw{sw.id}"

        if trophy_frame is None:
            print(f"  SKIP  {label} — no trophy frame detected")
            skipped += 1
            continue

        if not os.path.exists(video_path):
            print(f"  SKIP  {label} — video file not found: {video_path}")
            skipped += 1
            continue

        fps = meta.get("fps") or video.fps or 30.0
        start_frame = int(sw.start_timestamp * fps)

        cap = cv2.VideoCapture(video_path)
        cap.set(cv2.CAP_PROP_POS_FRAMES, start_frame + trophy_frame)
        ret, frame = cap.read()
        cap.release()

        if not ret or frame is None:
            print(f"  SKIP  {label} — could not read frame {trophy_frame}")
            skipped += 1
            continue

        # Overlay label
        overlay = f"sw{sw.id} | frame {trophy_frame} | {method} | conf {confidence:.2f}"
        cv2.putText(
            frame,
            overlay,
            (10, 30),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.7,
            (0, 255, 0),
            2,
            cv2.LINE_AA,
        )

        safe_name = video.filename.replace(" ", "_").replace("/", "_")
        out_path = os.path.join(out_dir, f"{safe_name}__sw{sw.id}__f{trophy_frame}.jpg")
        cv2.imwrite(out_path, frame)
        print(
            f"  OK    {label} → frame {trophy_frame} ({method}, conf {confidence:.2f})"
        )
        ok += 1

    print(f"\nDone. {ok} exported, {skipped} skipped.")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Export trophy position frames for all serve windows."
    )
    parser.add_argument(
        "--out-dir",
        default="/app/data/trophy_frames",
        help="Output directory for exported frames (default: /app/data/trophy_frames)",
    )
    args = parser.parse_args()
    main(args.out_dir)
