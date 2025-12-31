"""Supabase authentication utilities for token verification."""

import logging
from typing import Optional

from supabase import Client, create_client

from app.core.config import settings

logger = logging.getLogger(__name__)

# Try to import specific Supabase exceptions if available
try:
    from gotrue.errors import AuthError
except ImportError:
    # Fallback if gotrue.errors is not directly importable
    AuthError = None

try:
    from httpx import HTTPError, RequestError
except ImportError:
    HTTPError = None
    RequestError = None


def get_supabase_client() -> Client:
    """Get Supabase client for auth verification.

    Returns a Supabase client configured with the secret key for server-side operations.

    Raises:
        ValueError: If Supabase configuration is missing or invalid
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

    Raises:
        ValueError: If Supabase configuration is invalid (should not happen in normal flow)
    """
    try:
        client = get_supabase_client()
        # Set the session with the token, then get user
        # This verifies the token and returns user info
        response = client.auth.get_user(token)

        # Check if response has an error (Supabase client pattern)
        if hasattr(response, "error") and response.error:
            error_msg = (
                response.error.message
                if hasattr(response.error, "message")
                else str(response.error)
            )
            logger.warning(f"Supabase auth error: {error_msg}")
            return None

        if response and hasattr(response, "user") and response.user:
            user = response.user
            return {
                "id": user.id,
                "email": user.email,
                "user_metadata": user.user_metadata or {},
            }
        return None
    except ValueError as e:
        # Configuration errors - re-raise as they indicate programming/configuration issues
        logger.error(f"Supabase configuration error: {e}", exc_info=True)
        raise
    except AttributeError as e:
        # Response structure issues - log and return None (auth failure)
        logger.warning(
            f"Unexpected Supabase response structure: {e}",
            exc_info=True,
        )
        return None
    except Exception as e:
        # Check for specific exception types if available
        error_type = type(e).__name__

        # Handle specific Supabase auth errors if AuthError is available
        if AuthError and isinstance(e, AuthError):
            logger.warning(f"Supabase authentication error: {e}")
            return None

        # Handle network/connection errors if available
        if (HTTPError and isinstance(e, HTTPError)) or (
            RequestError and isinstance(e, RequestError)
        ):
            logger.warning(f"Network error during Supabase auth: {e}")
            return None

        # For other exceptions, check if they're likely auth-related
        # (e.g., JWT decode errors, validation errors)
        if any(
            keyword in error_type.lower()
            for keyword in ["auth", "token", "jwt", "validation", "decode"]
        ):
            logger.warning(
                f"Authentication-related error: {error_type}: {e}",
                exc_info=True,
            )
            return None

        # Unexpected errors - log with full context and re-raise
        # This ensures programming errors and unexpected issues are not silently ignored
        logger.error(
            f"Unexpected error during Supabase token verification: {error_type}: {e}",
            exc_info=True,
        )
        raise
