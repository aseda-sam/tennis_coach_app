#!/usr/bin/env python3
"""
Script to promote an existing video to demo status.

This script allows developers/admins to convert an analyzed video into a demo video
that all authenticated users can view. The script includes privacy protection to
prevent accidentally using real user content as marketing material.

Usage:
    python backend/scripts/promote_video_to_demo.py --video-id <id>
    python backend/scripts/promote_video_to_demo.py --video-id <id> --unpromote
"""

import argparse
import sys
from pathlib import Path

# Add the backend directory to the Python path
backend_dir = Path(__file__).parent.parent
sys.path.insert(0, str(backend_dir))

from app.core.config import settings  # noqa: E402
from app.core.database import SessionLocal  # noqa: E402
from app.models.video import Video  # noqa: E402


def promote_video(video_id: int, unpromote: bool = False) -> None:
    """Promote or unpromote a video to/from demo status.

    Args:
        video_id: ID of the video to promote/unpromote
        unpromote: If True, unpromote the video (restore original user_id)

    Raises:
        ValueError: If video not found, privacy violation, or validation fails
    """
    db = SessionLocal()
    try:
        # 1. Get video and validate it exists
        video = db.query(Video).filter(Video.id == video_id).first()
        if not video:
            raise ValueError(f"Video {video_id} not found")

        if unpromote:
            # Unpromote: Restore original user_id and set is_demo=False
            if not video.is_demo:
                print(f"⚠️  Video {video_id} is not a demo video. Nothing to unpromote.")
                return

            print(f"🔄 Unpromoting video {video_id} from demo status...")

            # Restore original user_id if available
            if video.original_user_id:
                video.user_id = video.original_user_id
                video.original_user_id = None
                print(f"   Restored user_id to: {video.user_id}")
            else:
                print(f"   ⚠️  No original_user_id found, keeping current user_id: {video.user_id}")

            video.is_demo = False
            db.commit()
            print(f"✅ Video {video_id} unpromoted successfully")
            return

        # 2. Privacy Protection: Only allow promoting videos from admin/test accounts
        # CRITICAL: This prevents accidentally using real user content as marketing material
        if video.user_id not in settings.ALLOWED_DEMO_SOURCE_USERS:
            raise ValueError(
                f"PRIVACY VIOLATION: Cannot promote user content as demo.\n"
                f"Video owner '{video.user_id}' is not in ALLOWED_DEMO_SOURCE_USERS.\n"
                f"Only admin/test account videos can be promoted.\n"
                f"Allowed users: {settings.ALLOWED_DEMO_SOURCE_USERS}\n"
                f"To add your admin user ID, update ALLOWED_DEMO_SOURCE_USERS in config.py"
            )

        # 3. Find existing demo (if any) for auto-replace
        old_demo = db.query(Video).filter(Video.is_demo == True).first()

        # 4. Unpromote old demo (restore original user_id)
        if old_demo and old_demo.id != video_id:
            print(f"🔄 Auto-replacing existing demo video {old_demo.id}...")
            old_demo.is_demo = False
            if old_demo.original_user_id:
                old_demo.user_id = old_demo.original_user_id
                old_demo.original_user_id = None
                print(f"   Restored old demo user_id to: {old_demo.user_id}")
            db.commit()

        # 5. Promote new video
        if video.is_demo:
            print(f"ℹ️  Video {video_id} is already a demo video. Confirming status...")
        else:
            print(f"🎯 Promoting video {video_id} to demo status...")
            # Backup original user_id before promotion
            video.original_user_id = video.user_id
            print(f"   Backed up original user_id: {video.original_user_id}")

        video.is_demo = True
        video.user_id = settings.DEMO_USER_ID
        db.commit()

        print(f"✅ Video {video_id} promoted successfully")
        print(f"   Demo user_id: {video.user_id}")
        print(f"   Original user_id (backed up): {video.original_user_id}")

    except Exception as e:
        db.rollback()
        raise
    finally:
        db.close()


def main() -> None:
    """Main entry point for the script."""
    parser = argparse.ArgumentParser(
        description="Promote or unpromote a video to/from demo status"
    )
    parser.add_argument(
        "--video-id",
        type=int,
        required=True,
        help="ID of the video to promote/unpromote",
    )
    parser.add_argument(
        "--unpromote",
        action="store_true",
        help="Unpromote the video (restore original user_id and set is_demo=False)",
    )

    args = parser.parse_args()

    try:
        promote_video(args.video_id, unpromote=args.unpromote)
    except ValueError as e:
        print(f"❌ Error: {e}", file=sys.stderr)
        sys.exit(1)
    except Exception as e:
        print(f"❌ Unexpected error: {e}", file=sys.stderr)
        import traceback

        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
