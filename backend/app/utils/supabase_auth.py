"""Supabase authentication utilities for token verification."""

from typing import Optional

from supabase import Client, create_client

from app.core.config import settings


def get_supabase_client() -> Client:
    """Get Supabase client for auth verification.

    Returns a Supabase client configured with the secret key for server-side operations.
    """
    supabase_url = settings.SUPABASE_URL
    if not supabase_url:
        raise ValueError("SUPABASE_URL not configured")

    if not supabase_url.endswith("/"):
        supabase_url = supabase_url + "/"

    if not settings.SUPABASE_SECRET_KEY:
        raise ValueError("SUPABASE_SECRET_KEY not configured")

    return create_client(supabase_url, settings.SUPABASE_SECRET_KEY)


def verify_supabase_token(token: str) -> Optional[dict]:
    """Verify Supabase JWT token and return user info.

    Args:
        token: JWT token from Supabase

    Returns:
        User dict with id, email, user_metadata, etc. if token is valid, None otherwise
    """
    try:
        client = get_supabase_client()
        # Set the session with the token, then get user
        # This verifies the token and returns user info
        response = client.auth.get_user(token)
        if response and hasattr(response, "user"):
            user = response.user
            return {
                "id": user.id,
                "email": user.email,
                "user_metadata": user.user_metadata or {},
            }
        return None
    except Exception:  # noqa: BLE001 - Catch all Supabase auth errors
        return None
