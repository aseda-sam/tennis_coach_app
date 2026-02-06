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
            logger.warning("Supabase auth error: %s", error_msg)
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
        logger.error("Supabase configuration error: %s", e, exc_info=True)
        raise
    except AttributeError as e:
        # Response structure issues - log and return None (auth failure)
        logger.warning(
            f"Unexpected Supabase response structure: {e}",
            exc_info=True,
        )
        return None
    except Exception as e:  # noqa: BLE001 - Intentional: fail closed for auth, catch all exceptions
        # Check for specific exception types if available
        error_type = type(e).__name__

        # Handle specific Supabase auth errors if AuthError is available
        if AuthError and isinstance(e, AuthError):
            logger.warning("Supabase authentication error: %s", e)
            return None

        # Handle network/connection errors if available
        if (HTTPError and isinstance(e, HTTPError)) or (
            RequestError and isinstance(e, RequestError)
        ):
            logger.warning("Network error during Supabase auth: %s", e)
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

        # For authentication, we want to fail closed - any unexpected error
        # during token verification should be treated as auth failure
        # This prevents leaking information about internal errors
        logger.warning(
            f"Unexpected error during Supabase token verification (treated as auth failure): {error_type}: {e}",
            exc_info=True,
        )
        return None


def get_user_by_id(user_id: str) -> Optional[dict]:
    """Fetch user by ID using Supabase admin API.

    Args:
        user_id: Supabase auth user UUID

    Returns:
        User dict with id and email if user exists, None otherwise

    Raises:
        ValueError: If Supabase configuration is invalid
    """
    # Skip validation in local profile (no Supabase available)
    if settings.PROFILE == "local":
        # Basic UUID format check
        import re

        uuid_pattern = re.compile(
            r"^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$",
            re.IGNORECASE,
        )
        if not uuid_pattern.match(user_id):
            logger.warning("Invalid UUID format in local profile: %s", user_id)
            return None
        # In local, assume valid UUIDs are acceptable
        return {"id": user_id, "email": None}

    try:
        client = get_supabase_client()
        # Use admin API to get user by ID
        response = client.auth.admin.get_user_by_id(user_id)

        if response and hasattr(response, "user") and response.user:
            return {
                "id": response.user.id,
                "email": response.user.email,
            }
        return None
    except ValueError as e:
        # Configuration errors - re-raise
        logger.error(
            "Supabase configuration error in get_user_by_id: %s", e, exc_info=True
        )
        raise
    except Exception as e:  # noqa: BLE001 - Catch all for admin API calls
        error_type = type(e).__name__
        logger.warning(
            "Error fetching user by ID from Supabase: %s: %s",
            error_type,
            e,
            exc_info=True,
        )
        return None
