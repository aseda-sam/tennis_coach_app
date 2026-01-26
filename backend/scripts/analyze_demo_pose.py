#!/usr/bin/env python3
"""
Script to run pose analysis for the active demo video.

This script runs pose analysis for the active demo video, similar to what a user
would do for a regular video. It bypasses the API restrictions on demo videos
and directly calls the analysis task.

Usage:
    python backend/scripts/analyze_demo_pose.py [--video-id <id>] [--confidence <threshold>]
    python backend/scripts/analyze_demo_pose.py --list
"""

import argparse
import sys
from pathlib import Path

# Add the backend directory to the Python path
backend_dir = Path(__file__).parent.parent
sys.path.insert(0, str(backend_dir))

from rq import Retry  # noqa: E402

from app.core.config import settings  # noqa: E402
from app.core.database import SessionLocal  # noqa: E402
from app.core.redis_config import analysis_queue  # noqa: E402
from app.models.video import Video  # noqa: E402
from app.services.pose_detection import PoseDetectionService  # noqa: E402
from app.services.rq_tasks import analyze_pose_detection_rq  # noqa: E402


def get_demo_video_path(video: Video) -> str:
    """Get the storage path for a demo video, handling demo bucket if needed.

    Args:
        video: Video model instance

    Returns:
        Storage path string that can be used for analysis
    """
    # For local storage, return the file_path as-is
    if settings.STORAGE_TYPE == "local":
        return video.file_path

    # For Supabase, if it's an active demo and in demo bucket, use the demo path
    if (
        video.is_active_demo
        and settings.SUPABASE_DEMO_BUCKET
        and video.file_path.startswith("demo/")
    ):
        # The file_path already points to the demo bucket
        return video.file_path

    # For regular Supabase videos, return file_path as-is
    return video.file_path


def list_demo_videos() -> None:
    """List all demo videos and show their pose analysis status."""
    db = SessionLocal()
    try:
        demo_videos = db.query(Video).filter(Video.is_demo).order_by(Video.id).all()

        if not demo_videos:
            print("No demo videos found.")
            return

        pose_service = PoseDetectionService()

        print(f"\nFound {len(demo_videos)} demo video(s):\n")
        for video in demo_videos:
            active_marker = "⭐ ACTIVE" if video.is_active_demo else ""
            pose_detection = pose_service.get_detection_by_video_id(db, video.id)
            pose_status = (
                f"✅ Analyzed (ID: {pose_detection.id})"
                if pose_detection and pose_detection.status == "completed"
                else "❌ Not analyzed"
            )
            print(
                f"  ID: {video.id:4d} | {video.filename:30s} | "
                f"Path: {video.file_path:30s} | {pose_status} {active_marker}"
            )
        print()
    finally:
        db.close()


def run_pose_analysis(video_id: int, confidence_threshold: float = 0.7) -> None:
    """Run pose analysis for a demo video.

    Args:
        video_id: ID of the demo video to analyze
        confidence_threshold: Confidence threshold for pose detection

    Raises:
        ValueError: If video not found, not a demo, or validation fails
        RuntimeError: If analysis fails
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
                f"Only demo videos can be analyzed with this script."
            )

        # 3. Check if already analyzed
        pose_service = PoseDetectionService()
        existing_detection = pose_service.get_detection_by_video_id(db, video_id)
        if existing_detection and existing_detection.status == "completed":
            print(
                f"✅ Video {video_id} already has completed pose analysis "
                f"(ID: {existing_detection.id})"
            )
            return

        # 4. Get video path (storage service now handles demo bucket downloads automatically)
        video_path = get_demo_video_path(video)
        print(f"📹 Video path: {video_path}")

        # 5. Use existing RQ task directly (same as API endpoint does)
        # This reuses 100% of existing functionality - just bypasses the demo restriction
        print(f"🚀 Enqueueing pose analysis job for video {video_id}...")
        try:
            job = analysis_queue.enqueue(
                analyze_pose_detection_rq,  # Existing RQ task - no new code
                video_id=video_id,
                video_path=video_path,
                confidence_threshold=confidence_threshold,
                retry=Retry(max=2, interval=60),
                job_timeout=900,  # 15 minutes (increased from 5 min to handle longer videos)
                result_ttl=3600,  # Keep results for 1 hour
            )
            print("✅ Job enqueued successfully!")
            print(f"   Job ID: {job.id}")
            print(f"   Video ID: {video_id}")
            print(f"   Confidence threshold: {confidence_threshold}")
            print("\n💡 Monitor progress with:")
            print("   python -m rq info")
        except Exception as e:
            raise RuntimeError(f"Failed to enqueue job: {e}") from e

    except Exception:
        db.rollback()
        raise
    finally:
        db.close()


def main() -> None:
    """Main entry point for the script."""
    parser = argparse.ArgumentParser(description="Run pose analysis for demo videos")
    parser.add_argument(
        "--video-id",
        type=int,
        help="ID of the demo video to analyze (defaults to active demo)",
    )
    parser.add_argument(
        "--confidence",
        type=float,
        default=0.7,
        help="Confidence threshold for pose detection (default: 0.7)",
    )
    parser.add_argument(
        "--list",
        action="store_true",
        help="List all demo videos and their analysis status",
    )
    args = parser.parse_args()

    if args.list:
        list_demo_videos()
    elif args.video_id:
        try:
            run_pose_analysis(
                video_id=args.video_id,
                confidence_threshold=args.confidence,
            )
        except (ValueError, RuntimeError) as e:
            print(f"Error: {e}", file=sys.stderr)
            sys.exit(1)
        except (OSError, ConnectionError, AttributeError, KeyError) as e:
            print(f"Unexpected error: {e}", file=sys.stderr)
            import traceback

            traceback.print_exc()
            sys.exit(1)
    else:
        # Default: analyze active demo
        db = SessionLocal()
        try:
            active_demo = db.query(Video).filter(Video.is_active_demo).first()
            if not active_demo:
                print("Error: No active demo video found.", file=sys.stderr)
                print("Use --list to see available demo videos.", file=sys.stderr)
                sys.exit(1)

            print(f"🎯 Analyzing active demo video (ID: {active_demo.id})...")
            run_pose_analysis(
                video_id=active_demo.id,
                confidence_threshold=args.confidence,
            )
        except (ValueError, RuntimeError) as e:
            print(f"Error: {e}", file=sys.stderr)
            sys.exit(1)
        except (OSError, ConnectionError, AttributeError, KeyError) as e:
            print(f"Unexpected error: {e}", file=sys.stderr)
            import traceback

            traceback.print_exc()
            sys.exit(1)
        finally:
            db.close()


if __name__ == "__main__":
    main()
