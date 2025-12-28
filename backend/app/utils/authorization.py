"""Authorization utilities for checking user permissions."""

from typing import TYPE_CHECKING

from fastapi import HTTPException, status

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
    if user.get("user_metadata", {}).get("is_admin", False):
        return True

    # Check email (can be configured for specific admin emails)
    email = user.get("email", "")
    # For now, no specific admin emails - can be added later
    # Example: return email == "admin@example.com"
    return False


def can_access_video(video: "Video", user: dict) -> bool:
    """Check if user can access video.

    Args:
        video: Video model instance
        user: User dict with id, email, user_metadata, etc.

    Returns:
        True if user can access video, False otherwise
    """
    # Admins can access everything
    if is_admin(user):
        return True

    # Video owner can access
    if video.user_id == user["id"]:
        return True

    # Future: Check video_shares table for shared videos
    # For now, only owner and admin can access
    return False


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
    if player.user_id == user["id"]:
        return True

    return False


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
