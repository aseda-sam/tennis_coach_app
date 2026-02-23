#!/usr/bin/env python
"""Backfill biomechanics reports for existing serve windows.

Recomputes phase segmentation and metrics for all videos with accepted
serve windows. Runs synchronously (no RQ) since biomechanics computation
is fast (~100ms per serve window).

Usage:
    # Dry run — show what would be recomputed
    cd backend && python scripts/backfill_biomechanics.py --dry-run

    # Recompute only stale reports (version < current)
    cd backend && python scripts/backfill_biomechanics.py

    # Force recompute ALL reports (even current-version ones)
    cd backend && python scripts/backfill_biomechanics.py --force

    # Exclude specific video IDs
    cd backend && python scripts/backfill_biomechanics.py --exclude 12 5

Environment variables:
    DATABASE_URL=postgresql://tennis:tennis_dev@localhost:5432/tennis_coach
"""

import argparse
import sys
import time
from pathlib import Path

# Add backend to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from app.core.database import SessionLocal
from app.models.serve_biomechanics_report import ServeBiomechanicsReport
from app.models.serve_window import ServeWindow
from app.models.video import Video
from app.services.biomechanics.serve_biomechanics_service import (
    ANALYSIS_VERSION,
    compute_biomechanics_batch,
)


def find_videos_to_recompute(
    force: bool = False,
    exclude_ids: list[int] | None = None,
) -> list[dict]:
    """Find videos with accepted serve windows that need biomechanics recomputation.

    Args:
        force: If True, include all videos. If False, only include videos where
               at least one serve window has a stale or missing report.
        exclude_ids: Video IDs to skip.
    """
    with SessionLocal() as db:
        query = (
            db.query(Video)
            .join(ServeWindow, ServeWindow.video_id == Video.id)
            .filter(ServeWindow.status.in_(["accepted", "edited"]))
        )

        if exclude_ids:
            query = query.filter(~Video.id.in_(exclude_ids))

        videos = query.distinct().all()

        results = []
        for v in videos:
            windows = (
                db.query(ServeWindow)
                .filter(
                    ServeWindow.video_id == v.id,
                    ServeWindow.status.in_(["accepted", "edited"]),
                )
                .all()
            )

            if not force:
                # Check if any window has a stale or missing report
                has_stale = False
                for w in windows:
                    latest_report = (
                        db.query(ServeBiomechanicsReport)
                        .filter(
                            ServeBiomechanicsReport.serve_window_id == w.id,
                            ServeBiomechanicsReport.user_id == v.user_id,
                        )
                        .order_by(ServeBiomechanicsReport.created_at.desc())
                        .first()
                    )
                    if (
                        latest_report is None
                        or latest_report.analysis_version != ANALYSIS_VERSION
                    ):
                        has_stale = True
                        break

                if not has_stale:
                    continue

            results.append(
                {
                    "video_id": v.id,
                    "filename": v.filename,
                    "user_id": v.user_id,
                    "window_count": len(windows),
                }
            )

        return results


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Backfill biomechanics reports for existing serve windows"
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Show what would be recomputed without running",
    )
    parser.add_argument(
        "--force",
        action="store_true",
        help="Recompute all reports, even those at current version",
    )
    parser.add_argument(
        "--exclude",
        type=int,
        nargs="+",
        metavar="ID",
        help="Video IDs to skip (e.g. --exclude 12 or --exclude 12 5)",
    )
    args = parser.parse_args()

    mode = (
        "all videos (--force)"
        if args.force
        else f"videos with stale reports (< {ANALYSIS_VERSION})"
    )
    print(f"Searching for {mode}...")
    if args.exclude:
        print(f"Excluding video IDs: {args.exclude}")
    videos = find_videos_to_recompute(force=args.force, exclude_ids=args.exclude)

    if not videos:
        print("No videos need recomputation.")
        return

    total_windows = sum(v["window_count"] for v in videos)
    print(f"\nFound {len(videos)} video(s) with {total_windows} serve window(s):\n")
    for v in videos:
        print(
            f"  Video {v['video_id']}: {v['filename']} "
            f"({v['window_count']} serve window(s))"
        )

    if args.dry_run:
        print("\n[DRY RUN] No reports recomputed.")
        return

    print(f"\nRecomputing biomechanics for {len(videos)} video(s)...")
    total_reports = 0
    total_errors = 0
    start = time.time()

    for v in videos:
        try:
            with SessionLocal() as db:
                reports = compute_biomechanics_batch(
                    db=db,
                    video_id=v["video_id"],
                    user_id=v["user_id"],
                )
                total_reports += len(reports)
                print(
                    f"  Video {v['video_id']}: {len(reports)}/{v['window_count']} "
                    f"reports computed"
                )
        except Exception as e:  # noqa: BLE001 - best-effort per video
            total_errors += 1
            print(f"  Video {v['video_id']}: FAILED — {e}")

    elapsed = time.time() - start
    print(
        f"\nDone in {elapsed:.1f}s. "
        f"Computed {total_reports} reports across {len(videos)} videos. "
        f"Errors: {total_errors}."
    )


if __name__ == "__main__":
    main()
