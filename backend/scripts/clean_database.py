#!/usr/bin/env python3
"""
Script to clean all records from the database tables.
Use this to start fresh with testing.

WARNING: This will delete ALL data from the database!
"""

import sys
from pathlib import Path

# Add the backend directory to the Python path
backend_dir = Path(__file__).parent.parent
sys.path.insert(0, str(backend_dir))

from app.core.database import get_db  # noqa: E402
from app.models.pose_detection import PoseDetection  # noqa: E402
from app.models.serve_attempt import ServeAttempt  # noqa: E402
from app.models.video import Video  # noqa: E402


def clean_database() -> None:
    """Delete all records from all tables."""
    print("🧹 Starting database cleanup...")

    # Get database session
    db = next(get_db())

    try:
        # Count records before deletion
        video_count = db.query(Video).count()
        pose_count = db.query(PoseDetection).count()
        serve_attempt_count = db.query(ServeAttempt).count()
        print("📊 Current record counts:")
        print(f"   Videos: {video_count}")
        print(f"   Pose Detections: {pose_count}")
        print(f"   Serve Attempts: {serve_attempt_count}")

        if video_count == 0 and pose_count == 0 and serve_attempt_count == 0:
            print("✅ Database is already clean!")
            return

        # Delete records in reverse dependency order to avoid foreign key issues
        print("\n🗑️  Deleting records...")

        # Delete dependent records first
        deleted_serve_attempts = db.query(ServeAttempt).delete()
        print(f"   Deleted {deleted_serve_attempts} serve attempts")

        deleted_poses = db.query(PoseDetection).delete()
        print(f"   Deleted {deleted_poses} pose detections")

        # Delete videos last
        deleted_videos = db.query(Video).delete()
        print(f"   Deleted {deleted_videos} videos")

        # Commit the changes
        db.commit()

        print("\n✅ Database cleanup completed successfully!")
        print("🎯 You can now start fresh with your frontend testing.")

    except Exception as e:
        print(f"❌ Error during database cleanup: {e}")
        db.rollback()
        raise
    finally:
        db.close()


if __name__ == "__main__":
    print("⚠️  WARNING: This will delete ALL data from the database!")
    response = input("Are you sure you want to continue? (yes/no): ")

    if response.lower() in ["yes", "y"]:
        clean_database()
    else:
        print("❌ Database cleanup cancelled.")
