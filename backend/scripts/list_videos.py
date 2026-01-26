#!/usr/bin/env python3
"""Quick script to list all videos in the database with their IDs."""

import sys
from pathlib import Path

# Add the backend directory to the Python path
backend_dir = Path(__file__).parent.parent
sys.path.insert(0, str(backend_dir))

from app.core.database import SessionLocal  # noqa: E402
from app.models.video import Video  # noqa: E402


def list_videos() -> None:
    """List all videos in the database."""
    db = SessionLocal()
    try:
        videos = db.query(Video).order_by(Video.id).all()

        if not videos:
            print("No videos found in database.")
            return

        print(f"\nFound {len(videos)} video(s):\n")
        print(
            f"{'ID':<6} {'Filename':<40} {'Status':<12} {'Is Demo':<10} {'User ID':<40}"
        )
        print("-" * 120)

        for video in videos:
            demo_status = "Yes" if video.is_demo else "No"
            user_id_short = (
                video.user_id[:8] + "..." if len(video.user_id) > 8 else video.user_id
            )
            print(
                f"{video.id:<6} {video.filename[:38]:<40} {video.status:<12} {demo_status:<10} {user_id_short:<40}"
            )

        print("\nTo set the active demo video, use:")
        print("  python scripts/set_active_demo.py --video-id <ID>")

    finally:
        db.close()


if __name__ == "__main__":
    list_videos()
