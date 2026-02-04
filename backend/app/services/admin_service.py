"""Service for admin-specific operations."""

from app.utils.supabase_auth import get_user_by_id


def validate_target_user_exists(target_user_id: str) -> dict:
    """Validate that a target user exists in Supabase.

    Args:
        target_user_id: Supabase auth user UUID

    Returns:
        User dict with id and email

    Raises:
        ValueError: If user not found in Supabase
    """
    target_user = get_user_by_id(target_user_id)
    if not target_user:
        raise ValueError(f"Target user {target_user_id} not found in Supabase")
    return target_user
