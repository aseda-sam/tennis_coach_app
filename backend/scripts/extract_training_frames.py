"""Extract training frames for ball-detection fine-tuning.

Selects frames from your own serve videos where ball detection failed (or
succeeded with low confidence), targeted at the apex region where canopy
backgrounds dominate. Also pulls a handful of clean-detection "easy" frames
per video so the model retains general competence.

Output is ready for drag-and-drop upload to Roboflow.

Usage (run inside backend container):
    docker compose exec backend python scripts/extract_training_frames.py \
        --camera-angle profile \
        --player-id 1 \
        --max-fail-per-serve 5 \
        --easy-per-video 3 \
        --out-dir /app/data/training_frames

The script also writes a manifest.csv next to the frames recording which
video/serve/frame each image came from and its detection status.
"""

import argparse
import csv
import json
import os
import sys
from collections import defaultdict
from typing import Optional

import cv2

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from sqlalchemy import desc

from app.core.database import SessionLocal
from app.models.ball_detection import BallDetection
from app.models.serve_window import ServeWindow
from app.models.video import Video


def _consecutive_runs(frames: list[int]) -> list[tuple[int, int]]:
    """Return (start, end_inclusive) ranges of consecutive integers."""
    if not frames:
        return []
    frames = sorted(frames)
    runs: list[tuple[int, int]] = []
    run_start = frames[0]
    prev = frames[0]
    for f in frames[1:]:
        if f == prev + 1:
            prev = f
            continue
        runs.append((run_start, prev))
        run_start = f
        prev = f
    runs.append((run_start, prev))
    return runs


def _evenly_sample(values: list[int], count: int) -> list[int]:
    """Pick `count` items spread evenly across `values`."""
    if not values or count <= 0:
        return []
    if len(values) <= count:
        return values
    step = (len(values) - 1) / (count - 1) if count > 1 else 0
    return [values[round(i * step)] for i in range(count)]


def main(
    out_dir: str,
    player_id: int,
    camera_angle: Optional[str],
    video_id: Optional[int],
    max_fail_per_serve: int,
    easy_per_video: int,
    min_gap_len: int,
    apex_low: float,
    apex_high: float,
    min_easy_conf: float,
) -> None:
    os.makedirs(out_dir, exist_ok=True)

    db = SessionLocal()
    try:
        q = db.query(Video).filter(Video.primary_player_id == player_id)
        if camera_angle:
            q = q.filter(Video.camera_angle == camera_angle)
        if video_id is not None:
            q = q.filter(Video.id == video_id)
        videos = q.order_by(Video.recorded_at.nulls_last(), Video.id).all()
    finally:
        # Keep session open for the rest of the work
        pass

    if not videos:
        print("No matching videos.")
        db.close()
        return

    print(f"Matched {len(videos)} video(s).")
    print(f"Output → {out_dir}\n")

    manifest_path = os.path.join(out_dir, "manifest.csv")
    manifest_file = open(manifest_path, "w", newline="")  # noqa: SIM115
    manifest = csv.writer(manifest_file)
    manifest.writerow(
        [
            "filename",
            "video_id",
            "video_filename",
            "serve_window_id",
            "frame",
            "tag",
            "ball_x",
            "ball_y",
            "confidence",
        ]
    )

    totals: dict[str, int] = defaultdict(int)

    for video in videos:
        bd = (
            db.query(BallDetection)
            .filter(BallDetection.video_id == video.id)
            .order_by(desc(BallDetection.id))
            .first()
        )
        if not bd or not bd.ball_data:
            print(f"  SKIP V#{video.id} {video.filename}: no ball detection")
            continue

        try:
            ball_data = json.loads(bd.ball_data)
        except (TypeError, ValueError):
            print(f"  SKIP V#{video.id} {video.filename}: ball_data unreadable")
            continue
        ball_by_frame = {
            int(d["frame_index"]): d for d in ball_data if "frame_index" in d
        }

        sws = (
            db.query(ServeWindow)
            .filter(ServeWindow.video_id == video.id, ServeWindow.is_active.is_(True))
            .order_by(ServeWindow.start_timestamp)
            .all()
        )
        if not sws:
            print(f"  SKIP V#{video.id} {video.filename}: no active serve windows")
            continue

        if not os.path.exists(video.file_path):
            print(f"  SKIP V#{video.id} {video.filename}: missing file")
            continue

        cap = cv2.VideoCapture(video.file_path)
        if not cap.isOpened():
            print(f"  SKIP V#{video.id} {video.filename}: cv2 cannot open")
            continue

        fps = video.fps or 30.0
        safe_stem = os.path.splitext(video.filename)[0].replace(" ", "_")

        v_fail = 0
        v_easy = 0

        for sw in sws:
            sf = int(sw.start_timestamp * fps)
            ef = int(sw.end_timestamp * fps)
            length = ef - sf
            if length <= 0:
                continue

            apex_lo = sf + int(length * apex_low)
            apex_hi = sf + int(length * apex_high)

            apex_frames = list(range(apex_lo, apex_hi + 1))
            missing_in_apex = [
                f for f in apex_frames if ball_by_frame.get(f, {}).get("ball_x") is None
            ]
            runs = _consecutive_runs(missing_in_apex)
            long_runs = [(s, e) for s, e in runs if (e - s + 1) >= min_gap_len]
            run_frames: list[int] = []
            for s, e in long_runs:
                run_frames.extend(range(s, e + 1))
            sampled_fail = _evenly_sample(run_frames, max_fail_per_serve)

            for f in sampled_fail:
                cap.set(cv2.CAP_PROP_POS_FRAMES, f)
                ok, frame = cap.read()
                if not ok or frame is None:
                    continue
                fname = f"v{video.id:03d}_{safe_stem}_sw{sw.id}_f{f:05d}_fail.jpg"
                cv2.imwrite(os.path.join(out_dir, fname), frame)
                manifest.writerow(
                    [fname, video.id, video.filename, sw.id, f, "fail", "", "", ""]
                )
                v_fail += 1

        # Easy frames per video — high-conf raw detections, evenly spread across all serves
        easy_candidates: list[tuple[int, dict]] = []
        for sw in sws:
            sf = int(sw.start_timestamp * fps)
            ef = int(sw.end_timestamp * fps)
            for f in range(sf, ef + 1):
                d = ball_by_frame.get(f)
                if (
                    d
                    and d.get("ball_x") is not None
                    and not d.get("interpolated")
                    and (d.get("confidence") or 0) >= min_easy_conf
                ):
                    easy_candidates.append((f, d))
        if easy_candidates and easy_per_video > 0:
            sampled_easy_idx = _evenly_sample(
                list(range(len(easy_candidates))), easy_per_video
            )
            for idx in sampled_easy_idx:
                f, d = easy_candidates[idx]
                cap.set(cv2.CAP_PROP_POS_FRAMES, f)
                ok, frame = cap.read()
                if not ok or frame is None:
                    continue
                fname = f"v{video.id:03d}_{safe_stem}_f{f:05d}_easy.jpg"
                cv2.imwrite(os.path.join(out_dir, fname), frame)
                manifest.writerow(
                    [
                        fname,
                        video.id,
                        video.filename,
                        "",
                        f,
                        "easy",
                        f"{d['ball_x']:.1f}",
                        f"{d['ball_y']:.1f}",
                        f"{d.get('confidence') or 0:.2f}",
                    ]
                )
                v_easy += 1

        cap.release()

        totals["fail"] += v_fail
        totals["easy"] += v_easy
        print(
            f"  V#{video.id:>3} {video.filename:40s}  fail={v_fail:>3}  easy={v_easy:>3}"
        )

    manifest_file.close()
    db.close()

    print(
        f"\nDone. fail={totals['fail']} easy={totals['easy']} "
        f"total={totals['fail'] + totals['easy']}"
    )
    print(f"Manifest: {manifest_path}")
    print(
        "\nNext: drag-and-drop the .jpg files into your Roboflow project, then label."
    )


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Extract failure-mode frames for ball-detection fine-tuning."
    )
    parser.add_argument("--out-dir", default="/app/data/training_frames")
    parser.add_argument("--player-id", type=int, default=1, help="Player#1 = 'Me'")
    parser.add_argument(
        "--camera-angle",
        default=None,
        help="Filter videos by camera_angle (e.g. 'profile' or 'behind')",
    )
    parser.add_argument(
        "--video-id", type=int, default=None, help="Restrict to a single video"
    )
    parser.add_argument(
        "--max-fail-per-serve",
        type=int,
        default=5,
        help="Max failure frames sampled per serve window",
    )
    parser.add_argument(
        "--easy-per-video",
        type=int,
        default=3,
        help="Successful-detection anchor frames per video (avoids forgetting)",
    )
    parser.add_argument(
        "--min-gap-len",
        type=int,
        default=3,
        help="Only sample from missing-frame runs of at least this length",
    )
    parser.add_argument(
        "--apex-low",
        type=float,
        default=0.15,
        help="Lower bound of apex region (fraction of serve window)",
    )
    parser.add_argument(
        "--apex-high",
        type=float,
        default=0.80,
        help="Upper bound of apex region (fraction of serve window)",
    )
    parser.add_argument(
        "--min-easy-conf",
        type=float,
        default=0.5,
        help="Minimum YOLO confidence for an easy anchor frame",
    )
    args = parser.parse_args()
    main(
        args.out_dir,
        args.player_id,
        args.camera_angle,
        args.video_id,
        args.max_fail_per_serve,
        args.easy_per_video,
        args.min_gap_len,
        args.apex_low,
        args.apex_high,
        args.min_easy_conf,
    )
