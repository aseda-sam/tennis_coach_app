"""Admin-only API routes for maintenance and cleanup."""

import logging
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.dependencies.auth import get_current_user
from app.services.cleanup_service import cleanup_orphaned_data, find_orphaned_user_ids
from app.utils.authorization import require_admin
from app.utils.error_handling import log_and_raise_error

logger = logging.getLogger(__name__)

router = APIRouter(tags=["admin"])


class CleanupResponse(BaseModel):
    """Response model for cleanup operations."""

    orphaned_user_count: int
    videos_deleted: int
    players_deleted: int
    files_deleted: int
    errors: list[str]
    dry_run: bool
    message: str


@router.post("/cleanup/orphaned-data", response_model=CleanupResponse)
def cleanup_orphaned_user_data(
    dry_run: bool = Query(
        True, description="If True, only report what would be deleted"
    ),
    limit: Optional[int] = Query(
        None, description="Limit number of users to process (for safety)"
    ),
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> CleanupResponse:
    """Clean up orphaned data from deleted users (admin only).

    This endpoint finds and deletes videos and players belonging to users
    that no longer exist in Supabase auth.users table.

    Args:
        dry_run: If True, only report what would be deleted
        limit: Optional limit on number of users to process
        current_user: Current authenticated user (must be admin)
        db: Database session

    Returns:
        Cleanup statistics and results
    """
    require_admin(current_user)

    logger.info(
        "Admin cleanup requested by %s (dry_run=%s, limit=%s)",
        current_user.get("email"),
        dry_run,
        limit,
    )

    try:
        stats = cleanup_orphaned_data(db, dry_run=dry_run, limit=limit)

        message = (
            f"{'Would delete' if dry_run else 'Deleted'} "
            f"{stats['videos_deleted']} videos, {stats['players_deleted']} players, "
            f"{stats['files_deleted']} files for {stats['orphaned_user_count']} orphaned users"
        )

        if stats["errors"]:
            message += f" ({len(stats['errors'])} errors occurred)"

        return CleanupResponse(
            orphaned_user_count=stats["orphaned_user_count"],
            videos_deleted=stats["videos_deleted"],
            players_deleted=stats["players_deleted"],
            files_deleted=stats["files_deleted"],
            errors=stats["errors"],
            dry_run=dry_run,
            message=message,
        )
    except HTTPException:
        raise
    except Exception as e:  # noqa: BLE001 - Catch all unexpected errors for admin endpoint
        log_and_raise_error(
            e, "cleanup_orphaned_user_data", {"dry_run": dry_run, "limit": limit}
        )


@router.get("/cleanup/orphaned-data/check", response_model=dict)
def check_orphaned_data(
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> dict:
    """Check for orphaned data without deleting (admin only).

    Args:
        current_user: Current authenticated user (must be admin)
        db: Database session

    Returns:
        Dictionary with orphaned user IDs and counts
    """
    require_admin(current_user)

    try:
        orphaned_ids = find_orphaned_user_ids(db)

        # Count records for each orphaned user
        from app.models.player import Player
        from app.models.video import Video

        details = []
        for user_id in orphaned_ids:
            video_count = db.query(Video).filter(Video.user_id == user_id).count()
            player_count = db.query(Player).filter(Player.user_id == user_id).count()
            details.append(
                {
                    "user_id": user_id,
                    "video_count": video_count,
                    "player_count": player_count,
                }
            )

        return {
            "orphaned_user_count": len(orphaned_ids),
            "orphaned_users": details,
        }
    except HTTPException:
        raise
    except Exception as e:  # noqa: BLE001 - Catch all unexpected errors for admin endpoint
        log_and_raise_error(e, "check_orphaned_data", {})
