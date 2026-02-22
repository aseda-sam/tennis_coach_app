#!/usr/bin/env python
"""Backfill ball detection for videos with serve windows but no ball data.

Queries videos that have accepted serve windows but no completed BallDetection
record, then enqueues run_ball_detection_rq jobs for each.

Usage:
    # Dry run — show what would be queued
    cd backend && python scripts/backfill_ball_detection.py --dry-run

    # Enqueue jobs
    cd backend && python scripts/backfill_ball_detection.py

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


def find_videos_needing_ball_detection() -> list[dict]:
    """Find videos with accepted serve windows but no completed BallDetection."""
    with SessionLocal() as db:
        # Subquery: video IDs that already have completed ball detection
        completed_ball_video_ids = (
            db.query(BallDetection.video_id)
            .filter(BallDetection.status == "completed")
            .subquery()
        )

        # Videos with accepted serve windows but no completed ball detection
        videos = (
            db.query(Video)
            .join(ServeWindow, ServeWindow.video_id == Video.id)
            .filter(
                ServeWindow.status == "accepted",
                ~Video.id.in_(db.query(completed_ball_video_ids)),
            )
            .distinct()
            .all()
        )

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
    args = parser.parse_args()

    print("Searching for videos needing ball detection...")
    videos = find_videos_needing_ball_detection()

    if not videos:
        print("No videos need ball detection backfill.")
        return

    print(f"\nFound {len(videos)} video(s) needing ball detection:\n")
    for v in videos:
        print(
            f"  Video {v['video_id']}: {v['filename']} "
            f"({v['window_count']} serve window(s))"
        )

    if args.dry_run:
        print("\n[DRY RUN] No jobs enqueued.")
        return

    print(f"\nEnqueuing {len(videos)} ball detection job(s)...")
    enqueued = 0
    for v in videos:
        try:
            job = analysis_queue.enqueue(
                run_ball_detection_rq,
                video_id=v["video_id"],
                user_id=v["user_id"],
                retry=Retry(max=2, interval=0),
                job_timeout=settings.POSE_DETECTION_JOB_TIMEOUT_SECONDS,
                result_ttl=3600,
                meta={"enqueued_at": time.time(), "backfill": True},
            )
            enqueued += 1
            print(f"  Enqueued job {job.id} for video {v['video_id']}")
        except Exception as e:  # noqa: BLE001 - best-effort enqueue per video
            print(f"  FAILED to enqueue for video {v['video_id']}: {e}")

    print(f"\nDone. Enqueued {enqueued}/{len(videos)} jobs.")


if __name__ == "__main__":
    main()
