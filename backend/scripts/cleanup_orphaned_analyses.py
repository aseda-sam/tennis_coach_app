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

from app.core.database import get_db
from app.models.analysis import Analysis
from app.models.video import Video


def cleanup_orphaned_analyses() -> None:
    """Remove analysis records that reference non-existent videos."""
    db = next(get_db())

    try:
        print("Starting cleanup of orphaned analysis records...")

        # Find all analysis records
        analyses = db.query(Analysis).all()
        orphaned_count = 0

        for analysis in analyses:
            if analysis.video_id:
                # Check if the referenced video exists
                video = db.query(Video).filter(Video.id == analysis.video_id).first()
                if not video:
                    print(
                        f"Deleting orphaned analysis {analysis.id} for video_id {analysis.video_id} "
                        f"(filename: {analysis.video_filename})"
                    )
                    db.delete(analysis)
                    orphaned_count += 1

        db.commit()
        print(f"✅ Cleaned up {orphaned_count} orphaned analysis records")

        if orphaned_count == 0:
            print("✅ No orphaned analysis records found")

    except (OSError, ValueError, RuntimeError) as e:
        print(f"❌ Error during cleanup: {e}")
        db.rollback()
        sys.exit(1)
    finally:
        db.close()


def main() -> None:
    """Main function to run the cleanup."""
    print("🧹 Analysis Records Cleanup Script")
    print("=" * 40)

    try:
        cleanup_orphaned_analyses()
        print("\n✅ Cleanup completed successfully!")
    except KeyboardInterrupt:
        print("\n⚠️  Cleanup interrupted by user")
        sys.exit(1)
    except (OSError, ValueError, RuntimeError) as e:
        print(f"\n❌ Unexpected error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
