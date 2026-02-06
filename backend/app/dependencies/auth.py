"""Authentication dependencies for protected routes."""

import logging
from typing import Optional

from fastapi import Depends, HTTPException, Request, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from app.core.config import settings
from app.utils.supabase_auth import verify_supabase_token

logger = logging.getLogger(__name__)

# Set auto_error=False to allow optional credentials when PROFILE=local
# This allows the dependency to receive None credentials, which we handle in get_current_user
security = HTTPBearer(auto_error=False)


async def get_current_user(
    request: Request,
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(security),
) -> dict:
    """Dependency to get current authenticated user from Supabase.

    Args:
        request: FastAPI request object
        credentials: HTTP Bearer token from request header

    Returns:
        User dict with id, email, user_metadata, etc.

    Raises:
        HTTPException: 401 if authentication fails
    """
    # Log profile and auth status for debugging
    logger.debug(
        f"Auth check: PROFILE={settings.PROFILE}, "
        f"credentials_present={credentials is not None}, "
        f"auth_required={settings.auth_required}"
    )

    # Skip auth when PROFILE=local
    if settings.PROFILE == "local":
        logger.debug("Profile is 'local': Returning mock user (auth disabled)")
        # Return mock user for local testing
        return {
            "id": "00000000-0000-0000-0000-000000000000",
            "email": "dev@localhost",
            "user_metadata": {},
        }

    # Auth is required - check for credentials
    if not credentials:
        logger.warning(
            f"Authentication required but no credentials provided. "
            f"PROFILE={settings.PROFILE}, auth_required={settings.auth_required}"
        )
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication required",
        )

    token = credentials.credentials
    logger.debug("Verifying token for PROFILE=%s", settings.PROFILE)
    user = verify_supabase_token(token)

    if user is None:
        logger.warning(
            f"Token verification failed. PROFILE={settings.PROFILE}, "
            f"token_present={bool(token)}"
        )
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid authentication credentials",
        )

    logger.debug("Authentication successful for user: %s", user.get("email", "unknown"))
    return user


async def get_optional_user(
    request: Request,
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(security),
) -> Optional[dict]:
    """Optional authentication dependency for public endpoints.

    Returns user dict if authenticated, None if not authenticated.
    Does not raise exceptions for missing credentials.

    Args:
        request: FastAPI request object
        credentials: HTTP Bearer token from request header (optional)

    Returns:
        User dict if authenticated, None if not authenticated
    """
    # Skip auth when PROFILE=local - return mock user
    if settings.PROFILE == "local":
        return {
            "id": "00000000-0000-0000-0000-000000000000",
            "email": "dev@localhost",
            "user_metadata": {},
        }

    # No credentials provided - return None (public access allowed)
    if not credentials:
        return None

    # Try to verify token
    token = credentials.credentials
    user = verify_supabase_token(token)

    # Return None if token invalid (allows public access)
    return user
