"""Service for cleaning up orphaned data from deleted users."""

import logging
from typing import Optional

from sqlalchemy import func, text
from sqlalchemy.orm import Session

from app.models.player import Player
from app.models.video import Video
from app.services import video_service

logger = logging.getLogger(__name__)


def find_orphaned_user_ids(db: Session) -> list[str]:
    """Find user_ids that exist in our tables but not in auth.users.

    Args:
        db: Database session

    Returns:
        List of orphaned user_id strings
    """
    # Check if auth.users table exists (Supabase only)
    result = db.execute(
        text("""
            SELECT EXISTS (
                SELECT FROM information_schema.tables
                WHERE table_schema = 'auth'
                AND table_name = 'users'
            )
        """)
    )
    auth_table_exists = result.scalar()

    if not auth_table_exists:
        logger.info("auth.users table not found - skipping orphan check (local dev)")
        return []

    # Find user_ids in videos/players that don't exist in auth.users
    result = db.execute(
        text("""
            SELECT DISTINCT user_id
            FROM (
                SELECT user_id FROM videos
                UNION
                SELECT user_id FROM players
            ) AS all_user_ids
            WHERE user_id NOT IN (SELECT id::text FROM auth.users)
        """)
    )
    orphaned_ids = [row[0] for row in result.fetchall()]
    logger.info("Found %s orphaned user_ids: %s", len(orphaned_ids), orphaned_ids)
    return orphaned_ids


def get_orphaned_data_details(
    db: Session,
    orphaned_user_ids: list[str],
) -> list[dict]:
    """Get details about orphaned data for specific user IDs.

    Args:
        db: Database session
        orphaned_user_ids: List of orphaned user IDs to get details for

    Returns:
        List of dicts with user_id, video_count, and player_count
    """
    if not orphaned_user_ids:
        return []

    video_counts = dict(
        db.query(Video.user_id, func.count(Video.id))
        .filter(Video.user_id.in_(orphaned_user_ids))
        .group_by(Video.user_id)
        .all()
    )
    player_counts = dict(
        db.query(Player.user_id, func.count(Player.id))
        .filter(Player.user_id.in_(orphaned_user_ids))
        .group_by(Player.user_id)
        .all()
    )

    return [
        {
            "user_id": user_id,
            "video_count": int(video_counts.get(user_id, 0)),
            "player_count": int(player_counts.get(user_id, 0)),
        }
        for user_id in orphaned_user_ids
    ]


def cleanup_orphaned_data(
    db: Session, dry_run: bool = True, limit: Optional[int] = None
) -> dict:
    """Clean up orphaned data from deleted users.

    Args:
        db: Database session
        dry_run: If True, only report what would be deleted without actually deleting
        limit: Optional limit on number of users to process (for safety)

    Returns:
        Dictionary with cleanup statistics
    """
    orphaned_user_ids = find_orphaned_user_ids(db)

    if limit:
        orphaned_user_ids = orphaned_user_ids[:limit]

    stats = {
        "orphaned_user_count": len(orphaned_user_ids),
        "videos_deleted": 0,
        "players_deleted": 0,
        "files_deleted": 0,
        "errors": [],
        "dry_run": dry_run,
    }

    if not orphaned_user_ids:
        logger.info("No orphaned data found")
        return stats

    logger.info(
        f"{'[DRY RUN] ' if dry_run else ''}Cleaning up {len(orphaned_user_ids)} orphaned users"
    )

    videos_by_user: dict[str, list[Video]] = {
        user_id: [] for user_id in orphaned_user_ids
    }
    players_by_user: dict[str, list[Player]] = {
        user_id: [] for user_id in orphaned_user_ids
    }
    for video in db.query(Video).filter(Video.user_id.in_(orphaned_user_ids)).all():
        videos_by_user.setdefault(video.user_id, []).append(video)
    for player in db.query(Player).filter(Player.user_id.in_(orphaned_user_ids)).all():
        players_by_user.setdefault(player.user_id, []).append(player)

    for user_id in orphaned_user_ids:
        try:
            # Find all videos for this user
            videos = videos_by_user.get(user_id, [])
            video_count = len(videos)

            # Find all players for this user
            players = players_by_user.get(user_id, [])
            player_count = len(players)

            logger.info(
                f"{'[DRY RUN] ' if dry_run else ''}User {user_id}: "
                f"{video_count} videos, {player_count} players"
            )

            if dry_run:
                stats["videos_deleted"] += video_count
                stats["players_deleted"] += player_count
                # In dry run, assume all videos have files
                stats["files_deleted"] += video_count
                continue

            # Actually delete videos (this cascades to related records)
            files_deleted = 0
            for video in videos:
                try:
                    # Delete video (includes file deletion)
                    success, filename, _ = video_service.delete_video_with_analyses(
                        db, video.id
                    )
                    if success:
                        files_deleted += 1
                        stats["videos_deleted"] += 1
                    else:
                        stats["errors"].append(
                            f"Failed to delete video {video.id} ({filename})"
                        )
                except (ValueError, RuntimeError, OSError) as e:
                    error_msg = f"Error deleting video {video.id}: {e!s}"
                    logger.error(error_msg)
                    stats["errors"].append(error_msg)

            # Delete players (cascades to serve_attempts)
            for player in players:
                try:
                    db.delete(player)
                    stats["players_deleted"] += 1
                except (ValueError, RuntimeError) as e:
                    error_msg = f"Error deleting player {player.id}: {e!s}"
                    logger.error(error_msg)
                    stats["errors"].append(error_msg)

            # Commit deletions for this user
            if not dry_run:
                db.commit()
                stats["files_deleted"] += files_deleted

        except (ValueError, RuntimeError, OSError) as e:
            error_msg = f"Error processing user {user_id}: {e!s}"
            logger.error(error_msg, exc_info=True)
            stats["errors"].append(error_msg)
            if not dry_run:
                db.rollback()

    logger.info(
        f"{'[DRY RUN] ' if dry_run else ''}Cleanup complete: "
        f"{stats['videos_deleted']} videos, {stats['players_deleted']} players, "
        f"{stats['files_deleted']} files deleted"
    )

    return stats
