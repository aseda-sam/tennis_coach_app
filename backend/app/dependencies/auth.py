"""Authentication dependencies for protected routes."""

import logging
from typing import Optional

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from app.core.config import settings
from app.utils.supabase_auth import verify_supabase_token

logger = logging.getLogger(__name__)

# Set auto_error=False to allow optional credentials when PROFILE=local
# This allows the dependency to receive None credentials, which we handle in get_current_user
security = HTTPBearer(auto_error=False)


async def get_current_user(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(security),
) -> dict:
    """Dependency to get current authenticated user from Supabase.

    Args:
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
    logger.debug(f"Verifying token for PROFILE={settings.PROFILE}")
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

    logger.debug(f"Authentication successful for user: {user.get('email', 'unknown')}")
    return user
