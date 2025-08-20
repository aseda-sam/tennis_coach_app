#!/usr/bin/env python3
"""
Script to regenerate missing annotated videos for existing analyses.

This script finds analyses that have database records but missing annotated video files
and regenerates them.
"""

import logging
import sys
from pathlib import Path
from typing import TYPE_CHECKING, List, Tuple

if TYPE_CHECKING:
    from app.models.analysis import Analysis
    from app.models.video import Video

# Add the app directory to the path so we can import from it
sys.path.insert(0, str(Path(__file__).parent.parent))

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def get_analyses_with_missing_videos() -> List[Tuple]:
    """Get analyses that have database records but missing annotated video files."""
    try:
        from app.core.database import get_db
        from app.models.analysis import Analysis
        from app.models.video import Video

        db = next(get_db())
        analyses = db.query(Analysis).filter(Analysis.status == "completed").all()

        missing_videos = []

        for analysis in analyses:
            # Get the video record
            video = db.query(Video).filter(Video.id == analysis.video_id).first()
            if not video:
                logger.warning(
                    f"Analysis {analysis.id} references non-existent video {analysis.video_id}"
                )
                continue

            # Check if annotated video file exists
            annotated_path = None
            if analysis.annotated_video_path:
                annotated_path = Path(analysis.annotated_video_path)

            if not annotated_path or not annotated_path.exists():
                missing_videos.append((analysis, video))

        return missing_videos

    except (ImportError, RuntimeError, OSError) as e:
        logger.error(f"Failed to get analyses: {e}")
        return []


def regenerate_annotated_video(analysis: "Analysis", video: "Video") -> bool:
    """Regenerate annotated video for a specific analysis."""
    try:
        from app.core.config import settings
        from app.core.database import get_db
        from app.models.analysis import Analysis

        logger.info(
            f"Regenerating annotated video for analysis {analysis.id} (video: {video.filename})"
        )

        # Check if original video exists
        upload_dir = Path(settings.UPLOAD_DIR)
        original_video_path = upload_dir / video.filename

        if not original_video_path.exists():
            logger.error(f"Original video not found: {original_video_path}")
            return False

        # Get database session and re-query the analysis in this session
        db = next(get_db())
        analysis_in_session = (
            db.query(Analysis).filter(Analysis.id == analysis.id).first()
        )

        if not analysis_in_session:
            logger.error(f"Analysis {analysis.id} not found in database session")
            return False

        # Delete existing analysis to force regeneration
        logger.info(
            f"Deleting existing analysis {analysis_in_session.id} to force regeneration"
        )
        db.delete(analysis_in_session)
        db.commit()

        # Run analysis to regenerate annotated video
        logger.info(f"Running analysis for video: {video.filename}")

        # Import the analysis function
        from app.services.analysis_service import analyze_video

        result = analyze_video(
            db=db,  # Pass the database session
            video_id=video.id,  # Use video ID instead of filename
            analysis_type="ball_tracking",
            confidence_threshold=0.7,  # Use default confidence threshold
            include_pose_detection=True,  # Include pose detection for annotated video
        )

        if "error" in result:
            logger.error(f"Analysis failed: {result['error']}")
            return False

        # Check if annotated video was created
        if result.get("annotated_video_path"):
            annotated_path = Path(result["annotated_video_path"])
            if annotated_path.exists():
                file_size = annotated_path.stat().st_size
                logger.info(
                    f"Successfully regenerated annotated video: {annotated_path} ({file_size} bytes)"
                )
                return True
            else:
                logger.error(
                    f"Annotated video path returned but file doesn't exist: {annotated_path}"
                )
                return False
        else:
            logger.warning("No annotated video path in analysis result")
            return False

    except (ImportError, RuntimeError, OSError) as e:
        logger.error(f"Error regenerating annotated video: {e}")
        return False


def main() -> None:
    """Main function."""
    import argparse

    parser = argparse.ArgumentParser(description="Regenerate missing annotated videos")
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Show what would be regenerated without actually doing it",
    )
    parser.add_argument(
        "--force", action="store_true", help="Force regeneration even if files exist"
    )

    args = parser.parse_args()

    logger.info("Tennis Coach - Annotated Video Regeneration Tool")
    logger.info("=" * 60)

    # Get analyses with missing videos
    missing_videos = get_analyses_with_missing_videos()

    if not missing_videos:
        logger.info("No missing annotated videos found!")
        return

    logger.info(f"Found {len(missing_videos)} analyses with missing annotated videos:")

    for analysis, video in missing_videos:
        logger.info(f"  - Analysis {analysis.id}: {video.filename}")
        if analysis.annotated_video_path:
            logger.info(f"    Expected path: {analysis.annotated_video_path}")

    if args.dry_run:
        logger.info("\nThis was a dry run. No videos were regenerated.")
        return

    # Regenerate videos
    logger.info("\nStarting regeneration...")
    success_count = 0
    failure_count = 0

    for analysis, video in missing_videos:
        if regenerate_annotated_video(analysis, video):
            success_count += 1
        else:
            failure_count += 1

    logger.info("\nRegeneration complete:")
    logger.info(f"  Success: {success_count}")
    logger.info(f"  Failed: {failure_count}")


if __name__ == "__main__":
    main()
