#!/usr/bin/env python3
"""
Script to identify and optionally delete orphaned video files.

This script finds video files in the raw directory that don't have
corresponding database records, and optionally deletes them.
"""

import logging
import sys
from pathlib import Path
from typing import List, Tuple

# Add the app directory to the path so we can import from it
sys.path.insert(0, str(Path(__file__).parent.parent))

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def get_database_videos() -> List[str]:
    """Get list of video filenames from database."""
    try:
        from app.core.database import get_db
        from app.models.video import Video

        db = next(get_db())
        videos = db.query(Video).all()
        return [video.filename for video in videos]
    except (ImportError, RuntimeError, OSError) as e:
        logger.error(f"Failed to get database videos: {e}")
        return []


def get_filesystem_videos(raw_dir: Path) -> List[Path]:
    """Get list of video files from filesystem."""
    video_extensions = {".mp4", ".mov", ".avi", ".MP4", ".MOV", ".AVI"}
    video_files = []

    if raw_dir.exists():
        for file_path in raw_dir.iterdir():
            if file_path.is_file() and file_path.suffix in video_extensions:
                video_files.append(file_path)

    return video_files


def find_orphaned_videos(raw_dir: Path) -> List[Tuple[Path, str]]:
    """
    Find orphaned video files (exist in filesystem but not in database).

    Returns:
        List of tuples: (file_path, reason)
    """
    db_videos = set(get_database_videos())
    fs_videos = get_filesystem_videos(raw_dir)

    orphaned = []

    for file_path in fs_videos:
        if file_path.name not in db_videos:
            # Determine reason for orphaned status
            if file_path.name.startswith("test_"):
                reason = "test file"
            elif (
                file_path.name.startswith("aseda")
                or file_path.name.startswith("alc")
                or file_path.name.startswith("jannik")
            ):
                reason = "user upload (no DB record)"
            else:
                reason = "unknown origin"

            orphaned.append((file_path, reason))

    return orphaned


def calculate_disk_usage(files: List[Path]) -> int:
    """Calculate total disk usage of files in bytes."""
    total_size = 0
    for file_path in files:
        if file_path.exists():
            total_size += file_path.stat().st_size
    return total_size


def format_size(size_bytes: int) -> str:
    """Format bytes to human readable size."""
    for unit in ["B", "KB", "MB", "GB"]:
        if size_bytes < 1024.0:
            return f"{size_bytes:.1f} {unit}"
        size_bytes /= 1024.0
    return f"{size_bytes:.1f} TB"


def purge_orphaned_videos(dry_run: bool = True, include_tests: bool = False) -> None:
    """
    Identify and optionally delete orphaned video files.

    Args:
        dry_run: If True, only show what would be deleted without actually deleting
        include_tests: If True, include test files in the purge
    """
    try:
        from app.core.config import settings

        raw_dir = Path(settings.UPLOAD_DIR)
        logger.info(f"Scanning for orphaned videos in: {raw_dir.absolute()}")

        # Get orphaned videos
        orphaned = find_orphaned_videos(raw_dir)

        if not orphaned:
            logger.info("No orphaned videos found!")
            return

        # Filter based on include_tests flag
        if not include_tests:
            orphaned = [
                (path, reason)
                for path, reason in orphaned
                if not reason.startswith("test")
            ]

        if not orphaned:
            logger.info("No orphaned videos found (excluding test files)!")
            return

        # Group by reason
        by_reason = {}
        for file_path, reason in orphaned:
            if reason not in by_reason:
                by_reason[reason] = []
            by_reason[reason].append(file_path)

        # Display summary
        logger.info(f"\n{'=' * 60}")
        logger.info(
            f"ORPHANED VIDEOS SUMMARY ({'DRY RUN' if dry_run else 'ACTUAL DELETION'})"
        )
        logger.info(f"{'=' * 60}")

        total_files = 0
        total_size = 0

        for reason, files in by_reason.items():
            size = calculate_disk_usage(files)
            total_files += len(files)
            total_size += size

            logger.info(
                f"\n{reason.upper()} ({len(files)} files, {format_size(size)}):"
            )
            for file_path in sorted(files):
                file_size = file_path.stat().st_size if file_path.exists() else 0
                logger.info(f"  - {file_path.name} ({format_size(file_size)})")

        logger.info(f"\n{'=' * 60}")
        logger.info(f"TOTAL: {total_files} files, {format_size(total_size)}")
        logger.info(f"{'=' * 60}")

        if dry_run:
            logger.info("\nThis was a dry run. No files were deleted.")
            logger.info("To actually delete files, run with --delete flag")
            logger.info("To include test files, run with --include-tests flag")
        else:
            # Actually delete files
            deleted_count = 0
            deleted_size = 0

            for file_path, _ in orphaned:
                try:
                    file_size = file_path.stat().st_size if file_path.exists() else 0
                    file_path.unlink()
                    deleted_count += 1
                    deleted_size += file_size
                    logger.info(f"Deleted: {file_path.name}")
                except OSError as e:
                    logger.error(f"Failed to delete {file_path.name}: {e}")

            logger.info(
                f"\nSuccessfully deleted {deleted_count} files ({format_size(deleted_size)})"
            )

    except (ImportError, RuntimeError, OSError) as e:
        logger.error(f"Error during purge: {e}")
        sys.exit(1)


def main() -> None:
    """Main function."""
    import argparse

    parser = argparse.ArgumentParser(description="Purge orphaned video files")
    parser.add_argument(
        "--delete",
        action="store_true",
        help="Actually delete files (default is dry run)",
    )
    parser.add_argument(
        "--include-tests", action="store_true", help="Include test files in the purge"
    )

    args = parser.parse_args()

    logger.info("Tennis Coach - Orphaned Video Purge Tool")
    logger.info("=" * 50)

    purge_orphaned_videos(dry_run=not args.delete, include_tests=args.include_tests)


if __name__ == "__main__":
    main()
