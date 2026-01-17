#!/usr/bin/env python3
"""
Script to set the active demo video.

This script allows admins to rotate between demo videos by setting one as active.
Only videos with file_path starting with 'demo/' are eligible to be active demos.

Usage:
    python backend/scripts/set_active_demo.py --video-id <id>
    python backend/scripts/set_active_demo.py --list
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
from app.services.storage_service import storage_service  # noqa: E402


def list_demo_videos() -> None:
    """List all demo videos and show which one is active."""
    db = SessionLocal()
    try:
        demo_videos = db.query(Video).filter(Video.is_demo).order_by(Video.id).all()

        if not demo_videos:
            print("No demo videos found.")
            return

        print(f"\nFound {len(demo_videos)} demo video(s):\n")
        for video in demo_videos:
            active_marker = "⭐ ACTIVE" if video.is_active_demo else ""
            print(
                f"  ID: {video.id:4d} | {video.filename:30s} | "
                f"Path: {video.file_path:30s} {active_marker}"
            )
        print()
    finally:
        db.close()


def set_active_demo(video_id: int) -> None:
    """Set a video as the active demo.

    Args:
        video_id: ID of the video to set as active demo

    Raises:
        ValueError: If video not found, not eligible, or validation fails
    """
    db = SessionLocal()
    try:
        # 1. Get video and validate it exists
        video = db.query(Video).filter(Video.id == video_id).first()
        if not video:
            raise ValueError(f"Video {video_id} not found")

        # 2. Verify video is marked as demo
        if not video.is_demo:
            raise ValueError(
                f"Video {video_id} is not marked as demo (is_demo=False). "
                f"Only demo videos can be set as active."
            )

        # 3. Verify eligibility: file_path should start with 'demo/'
        if not video.file_path.startswith("demo/"):
            raise ValueError(
                f"Video {video_id} is not eligible to be active demo. "
                f"File path '{video.file_path}' does not start with 'demo/'. "
                f"Only videos in the demo folder can be active demos."
            )

        # 4. Ensure file exists in demo bucket (if using Supabase)
        if settings.STORAGE_TYPE == "supabase" and settings.SUPABASE_DEMO_BUCKET:
            demo_path = video.file_path
            if not storage_service.demo_object_exists(demo_path):
                print(f"⚠️  Demo file not found in bucket: {demo_path}")
                print("   Attempting to copy from private bucket...")

                # Try to download from private bucket and upload to demo bucket
                try:
                    file_content = storage_service.download_file(video.file_path)
                    storage_service.upload_demo_object(
                        demo_path, file_content, video.content_type
                    )
                    print(f"✅ Copied video to demo bucket: {demo_path}")
                except Exception as e:
                    raise ValueError(
                        f"Failed to copy video to demo bucket: {e}. "
                        f"Please ensure the video exists in the private bucket first."
                    ) from e
            else:
                print(f"✅ Demo file exists in bucket: {demo_path}")

        # 5. Unset any existing active demo
        old_active = db.query(Video).filter(Video.is_active_demo).first()
        if old_active:
            if old_active.id == video_id:
                print(f"Info: Video {video_id} is already the active demo.")
                return
            print(f"🔄 Unsetting previous active demo (video {old_active.id})...")
            old_active.is_active_demo = False
            db.commit()

        # 6. Set new active demo
        print(f"🎯 Setting video {video_id} as active demo...")
        video.is_active_demo = True
        db.commit()

        print(f"✅ Video {video_id} ({video.filename}) is now the active demo")
        print(f"   File path: {video.file_path}")

    except Exception:
        db.rollback()
        raise
    finally:
        db.close()


def main() -> None:
    """Main entry point for the script."""
    parser = argparse.ArgumentParser(
        description="Set the active demo video or list all demo videos"
    )
    parser.add_argument(
        "--video-id",
        type=int,
        help="ID of the video to set as active demo",
    )
    parser.add_argument(
        "--list",
        action="store_true",
        help="List all demo videos",
    )

    args = parser.parse_args()

    if args.list:
        list_demo_videos()
    elif args.video_id:
        try:
            set_active_demo(args.video_id)
        except ValueError as e:
            print(f"Error: {e}", file=sys.stderr)
            sys.exit(1)
        except (RuntimeError, OSError) as e:
            print(f"Unexpected error: {e}", file=sys.stderr)
            import traceback

            traceback.print_exc()
            sys.exit(1)
    else:
        parser.print_help()
        sys.exit(1)


if __name__ == "__main__":
    main()
