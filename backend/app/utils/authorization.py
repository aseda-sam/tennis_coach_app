"""Authorization utilities for checking user permissions."""

from datetime import datetime, timedelta
from typing import TYPE_CHECKING, Optional

from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app.core.config import settings

if TYPE_CHECKING:
    from app.models.player import Player
    from app.models.video import Video


def is_admin(user: dict) -> bool:
    """Check if user is admin.

    Args:
        user: User dict with id, email, user_metadata, etc.

    Returns:
        True if user is admin, False otherwise
    """
    user_id = user.get("id")
    if not user_id:
        return False
    return user_id in settings.admin_user_ids


def can_access_video(video: "Video", user: dict) -> bool:
    """Check if user can access video.

    Args:
        video: Video model instance
        user: User dict with id, email, user_metadata, etc.

    Returns:
        True if user can access video, False otherwise
    """
    # Demo videos readable by all authenticated users
    if video.is_demo:
        return True

    # Admins can access everything
    if is_admin(user):
        return True

    # Only owner and admin can access (no sharing implemented yet)
    return video.user_id == user["id"]


def require_video_access(video: "Video", user: dict) -> None:
    """Raise exception if user can't access video.

    Args:
        video: Video model instance
        user: User dict with id, email, user_metadata, etc.

    Raises:
        HTTPException: 403 if user can't access video
    """
    if not can_access_video(video, user):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You don't have permission to access this video",
        )


def require_video_access_or_public_demo(
    video: "Video", current_user: Optional[dict]
) -> None:
    """Raise exception if user can't access video, allowing public demo access.

    Allows unauthenticated access to demo videos. For non-demo videos or
    authenticated users, requires proper video access.

    Args:
        video: Video model instance
        current_user: User dict (may be None for unauthenticated requests)

    Raises:
        HTTPException: 401 if unauthenticated and video is not demo
        HTTPException: 403 if user can't access video
    """
    # Allow public access for demo videos
    if current_user is None and not video.is_demo:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication required",
        )
    # For authenticated users, check normal access permissions
    if current_user is not None:
        require_video_access(video, current_user)


def can_manage_player(player: "Player", user: dict) -> bool:
    """Check if user can manage player.

    Args:
        player: Player model instance
        user: User dict with id, email, user_metadata, etc.

    Returns:
        True if user can manage player, False otherwise
    """
    # Admins can manage everything
    if is_admin(user):
        return True

    # Player owner can manage
    return player.user_id == user["id"]


def require_player_access(player: "Player", user: dict) -> None:
    """Raise exception if user can't access player.

    Args:
        player: Player model instance
        user: User dict with id, email, user_metadata, etc.

    Raises:
        HTTPException: 403 if user can't access player
    """
    if not can_manage_player(player, user):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You don't have permission to access this player",
        )


def check_daily_upload_limit(
    db: Session, user_id: str, max_uploads: int
) -> tuple[bool, int]:
    """Check if user has exceeded daily upload limit.

    Args:
        db: Database session
        user_id: User ID to check
        max_uploads: Maximum uploads allowed per day

    Returns:
        Tuple of (is_within_limit, current_count)
    """
    from app.models.video import Video

    yesterday = datetime.utcnow() - timedelta(days=1)
    count = (
        db.query(Video)
        .filter(Video.user_id == user_id, Video.created_at >= yesterday)
        .count()
    )
    return count < max_uploads, count


def require_upload_limit(db: Session, user: dict, max_uploads: int) -> None:
    """Raise exception if user has exceeded daily upload limit.

    Args:
        db: Database session
        user: User dict with id, email, user_metadata, etc.
        max_uploads: Maximum uploads allowed per day

    Raises:
        HTTPException: 429 if upload limit exceeded
    """
    is_within_limit, current_count = check_daily_upload_limit(
        db, user["id"], max_uploads
    )
    if not is_within_limit:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail=f"You've reached your daily upload limit of {max_uploads} videos ({current_count} uploaded today). Please try again tomorrow.",
        )


def require_video_not_demo(video: "Video", user: Optional[dict] = None) -> None:
    """Raise exception if video is a demo (prevents modifications).

    Args:
        video: Video model instance
        user: User dict to allow admin bypass

    Raises:
        HTTPException: 403 if video is a demo
    """
    if video.is_demo and (user is None or not is_admin(user)):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Cannot modify demo video. Changes are not saved.",
        )


def require_video_deletable(video: "Video") -> None:
    """Raise exception if video is a demo (prevents deletion).

    Args:
        video: Video model instance

    Raises:
        HTTPException: 403 if video is a demo
    """
    if video.is_demo:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Cannot delete demo video. Use promotion script with --unpromote flag first.",
        )


def require_admin(user: dict) -> None:
    """Raise exception if user is not admin.

    Args:
        user: User dict with id, email, user_metadata, etc.

    Raises:
        HTTPException: 403 if user is not admin
    """
    if not is_admin(user):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin access required",
        )
