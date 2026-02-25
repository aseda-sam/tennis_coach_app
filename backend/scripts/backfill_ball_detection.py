#!/usr/bin/env python
"""Backfill ball detection for videos with serve windows.

Queries videos that have accepted serve windows, then enqueues
run_ball_detection_rq jobs for each. The RQ task deletes previous
BallDetection records before re-running, so --force is safe.

Usage:
    # Dry run — show what would be queued
    cd backend && python scripts/backfill_ball_detection.py --dry-run

    # Enqueue only videos missing ball detection
    cd backend && python scripts/backfill_ball_detection.py

    # Re-run ball detection on ALL videos (even ones that already have it)
    cd backend && python scripts/backfill_ball_detection.py --force

    # Force Apple Metal (MPS) when running workers locally on macOS
    cd backend && python scripts/backfill_ball_detection.py --device mps

    # Exclude specific video IDs (e.g. one that's already running)
    cd backend && python scripts/backfill_ball_detection.py --force --exclude 12
    cd backend && python scripts/backfill_ball_detection.py --force --exclude 12 5 9

Environment variables (same as host worker):
    REDIS_URL=redis://localhost:6379/0
    DATABASE_URL=postgresql://tennis:tennis_dev@localhost:5432/tennis_coach
"""

import argparse
import sys
import time
from pathlib import Path

# Add backend to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from rq import Retry

from app.core.config import settings
from app.core.database import SessionLocal
from app.core.redis_config import analysis_queue
from app.models.ball_detection import BallDetection
from app.models.serve_window import ServeWindow
from app.models.video import Video
from app.services.rq_tasks import run_ball_detection_rq


def find_videos_with_serve_windows(
    force: bool = False,
    exclude_ids: list[int] | None = None,
) -> list[dict]:
    """Find videos with accepted serve windows.

    Args:
        force: If True, include all videos. If False, skip videos that
               already have a completed BallDetection record.
        exclude_ids: Video IDs to skip.
    """
    with SessionLocal() as db:
        query = (
            db.query(Video)
            .join(ServeWindow, ServeWindow.video_id == Video.id)
            .filter(ServeWindow.status == "accepted")
        )

        if exclude_ids:
            query = query.filter(~Video.id.in_(exclude_ids))

        if not force:
            completed_ball_video_ids = (
                db.query(BallDetection.video_id)
                .filter(BallDetection.status == "completed")
                .subquery()
            )
            query = query.filter(~Video.id.in_(db.query(completed_ball_video_ids)))

        videos = query.distinct().all()

        results = []
        for v in videos:
            window_count = (
                db.query(ServeWindow)
                .filter(
                    ServeWindow.video_id == v.id,
                    ServeWindow.status == "accepted",
                )
                .count()
            )
            results.append(
                {
                    "video_id": v.id,
                    "filename": v.filename,
                    "user_id": v.user_id,
                    "window_count": window_count,
                }
            )

        return results


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Backfill ball detection for existing videos"
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Show what would be queued without actually enqueuing",
    )
    parser.add_argument(
        "--force",
        action="store_true",
        help="Re-run ball detection on all videos, even those with existing results",
    )
    parser.add_argument(
        "--exclude",
        type=int,
        nargs="+",
        metavar="ID",
        help="Video IDs to skip (e.g. --exclude 12 or --exclude 12 5 9)",
    )
    parser.add_argument(
        "--device",
        choices=["auto", "cpu", "mps", "cuda"],
        default="auto",
        help="YOLO inference device for queued jobs (default: auto)",
    )
    args = parser.parse_args()

    mode = "all videos (--force)" if args.force else "videos missing ball detection"
    print(f"Searching for {mode}...")
    if args.exclude:
        print(f"Excluding video IDs: {args.exclude}")
    videos = find_videos_with_serve_windows(force=args.force, exclude_ids=args.exclude)

    if not videos:
        print("No videos found.")
        return

    print(f"\nFound {len(videos)} video(s):\n")
    for v in videos:
        print(
            f"  Video {v['video_id']}: {v['filename']} "
            f"({v['window_count']} serve window(s))"
        )

    if args.dry_run:
        print("\n[DRY RUN] No jobs enqueued.")
        return

    device_label = args.device
    print(
        f"\nEnqueuing {len(videos)} ball detection job(s) with device={device_label}..."
    )
    enqueued = 0
    for v in videos:
        try:
            job = analysis_queue.enqueue(
                run_ball_detection_rq,
                video_id=v["video_id"],
                user_id=v["user_id"],
                ball_device=None if args.device == "auto" else args.device,
                retry=Retry(max=2, interval=0),
                job_timeout=settings.POSE_DETECTION_JOB_TIMEOUT_SECONDS,
                result_ttl=3600,
                meta={
                    "enqueued_at": time.time(),
                    "backfill": True,
                    "ball_device": args.device,
                },
            )
            enqueued += 1
            print(f"  Enqueued job {job.id} for video {v['video_id']}")
        except Exception as e:  # noqa: BLE001 - best-effort enqueue per video
            print(f"  FAILED to enqueue for video {v['video_id']}: {e}")

    print(f"\nDone. Enqueued {enqueued}/{len(videos)} jobs.")


if __name__ == "__main__":
    main()
