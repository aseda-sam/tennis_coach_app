#!/usr/bin/env python3
"""Fix all videos that were incorrectly marked as demo.

This script sets is_demo=False for all videos except the one that should be demo.
"""

import sys
from pathlib import Path

# Add the backend directory to the Python path
backend_dir = Path(__file__).parent.parent
sys.path.insert(0, str(backend_dir))

from app.core.database import SessionLocal  # noqa: E402
from app.models.video import Video  # noqa: E402


def fix_demo_flags(demo_video_id: int | None = None) -> None:
    """Set is_demo=False for all videos except the specified demo video.

    Args:
        demo_video_id: ID of the video that should remain as demo (optional)
    """
    db = SessionLocal()
    try:
        # Get all videos
        videos = db.query(Video).all()

        if not videos:
            print("No videos found in database.")
            return

        print(f"Found {len(videos)} video(s)\n")

        # Set all videos to is_demo=False
        updated_count = 0
        for video in videos:
            if demo_video_id and video.id == demo_video_id:
                # Keep this one as demo
                if not video.is_demo:
                    video.is_demo = True
                    print(f"✓ Video {video.id} ({video.filename}) - Set to DEMO")
                else:
                    print(f"  Video {video.id} ({video.filename}) - Already DEMO (keeping)")
            else:
                # Set to non-demo
                if video.is_demo:
                    video.is_demo = False
                    if video.original_user_id:
                        video.user_id = video.original_user_id
                        video.original_user_id = None
                    updated_count += 1
                    print(f"✓ Video {video.id} ({video.filename}) - Set to non-demo")

        db.commit()
        print(f"\n✅ Fixed {updated_count} video(s)")
        if demo_video_id:
            print(f"✓ Video {demo_video_id} remains as demo")

    except (RuntimeError, OSError, ValueError) as e:
        db.rollback()
        print(f"❌ Error: {e}", file=sys.stderr)
        import traceback

        traceback.print_exc()
        sys.exit(1)
    finally:
        db.close()


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(
        description="Fix all videos that were incorrectly marked as demo"
    )
    parser.add_argument(
        "--keep-demo",
        type=int,
        help="Video ID to keep as demo (all others will be set to non-demo)",
    )

    args = parser.parse_args()
    fix_demo_flags(demo_video_id=args.keep_demo)
