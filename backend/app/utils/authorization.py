"""Authorization utilities for checking user permissions."""

from datetime import datetime, timedelta
from typing import TYPE_CHECKING

from fastapi import HTTPException, status
from sqlalchemy.orm import Session

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
    # Check user_metadata for admin flag
    # For now, no specific admin emails - can be added later
    # Example: return user.get("email") == "admin@example.com"
    return user.get("user_metadata", {}).get("is_admin", False)


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


def can_create_ball_contact_for_video(video: "Video", user: dict) -> bool:
    """Check if user can create ball contacts for a video.

    Only video owner can create ball contacts.

    Args:
        video: Video model instance
        user: User dict with id, email, user_metadata, etc.

    Returns:
        True if user can create ball contacts, False otherwise
    """
    # Admins can create ball contacts for any video
    if is_admin(user):
        return True

    # Only video owner can create ball contacts
    return video.user_id == user["id"]


def require_ball_contact_permission(video: "Video", user: dict) -> None:
    """Raise exception if user can't create ball contacts for video.

    Args:
        video: Video model instance
        user: User dict with id, email, user_metadata, etc.

    Raises:
        HTTPException: 403 if user can't create ball contacts
    """
    if not can_create_ball_contact_for_video(video, user):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You don't have permission to create ball contacts for this video",
        )


def can_tag_player_to_video(video: "Video", player: "Player", user: dict) -> bool:
    """Check if user can tag a player to a video.

    User must own both the video and the player to tag it.
    This ensures users can only tag players they created themselves.

    Args:
        video: Video model instance
        player: Player model instance
        user: User dict with id, email, user_metadata, etc.

    Returns:
        True if user can tag player to video, False otherwise
    """
    # Admins can tag any player to any video
    if is_admin(user):
        return True

    # User must own both the video and the player
    # (they can only tag players they created to their videos)
    return video.user_id == user["id"] and player.user_id == user["id"]


def require_player_tag_permission(video: "Video", player: "Player", user: dict) -> None:
    """Raise exception if user can't tag player to video.

    Args:
        video: Video model instance
        player: Player model instance
        user: User dict with id, email, user_metadata, etc.

    Raises:
        HTTPException: 403 if user can't tag player to video
    """
    if not can_tag_player_to_video(video, player, user):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You can only tag players you created to your videos",
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


def is_demo_video(video: "Video") -> bool:
    """Check if video is a demo video.

    Args:
        video: Video model instance

    Returns:
        True if video is a demo video, False otherwise
    """
    return video.is_demo


def require_video_not_demo(video: "Video") -> None:
    """Raise exception if video is a demo (prevents modifications).

    Args:
        video: Video model instance

    Raises:
        HTTPException: 403 if video is a demo
    """
    if video.is_demo:
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
