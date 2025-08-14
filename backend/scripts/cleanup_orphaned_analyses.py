#!/usr/bin/env python3
"""
Script to clean up orphaned analysis records.

This script removes analysis records that reference non-existent videos,
which can happen when videos are deleted but analyses are not properly
cleaned up due to missing cascade deletion.
"""

import sys
from pathlib import Path

# Add the backend directory to the Python path
backend_dir = Path(__file__).parent.parent
sys.path.insert(0, str(backend_dir))

try:
    from app.core.database import get_db
    from app.models.analysis import Analysis
    from app.models.video import Video
except ImportError:
    print(
        "Error: Could not import required modules. Make sure you're running from the backend directory."
    )
    sys.exit(1)


def cleanup_orphaned_analyses() -> None:
    """Remove analysis records that reference non-existent videos."""
    db = next(get_db())

    try:
        print("Starting cleanup of orphaned analysis records...")

        # Get all analysis records
        analyses = db.query(Analysis).all()
        print(f"Found {len(analyses)} total analysis records")

        # Get all video IDs
        video_ids = {video.id for video in db.query(Video).all()}
        print(f"Found {len(video_ids)} videos: {sorted(video_ids)}")

        # Find orphaned analyses
        orphaned_count = 0
        for analysis in analyses:
            if analysis.video_id is not None and analysis.video_id not in video_ids:
                print(
                    f"Found orphaned analysis ID {analysis.id} for video_id {analysis.video_id}"
                )
                db.delete(analysis)
                orphaned_count += 1

        if orphaned_count > 0:
            db.commit()
            print(f"Successfully removed {orphaned_count} orphaned analysis records")
        else:
            print("No orphaned analysis records found")

    except Exception as e:
        print(f"Error during cleanup: {e}")
        db.rollback()
        raise
    finally:
        db.close()


if __name__ == "__main__":
    cleanup_orphaned_analyses()
