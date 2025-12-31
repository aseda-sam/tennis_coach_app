"""Authentication dependencies for protected routes."""

import logging
from typing import Optional

from fastapi import Depends, HTTPException, Request, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from slowapi import Limiter
from slowapi.errors import RateLimitExceeded

from app.core.config import settings
from app.utils.supabase_auth import verify_supabase_token

logger = logging.getLogger(__name__)

# Set auto_error=False to allow optional credentials when PROFILE=local
# This allows the dependency to receive None credentials, which we handle in get_current_user
security = HTTPBearer(auto_error=False)


def _check_auth_rate_limit(request: Request, limiter: Limiter, rate_limit: str) -> None:
    """Check rate limit for authentication attempts.

    Args:
        request: FastAPI request object
        limiter: SlowAPI limiter instance
        rate_limit: Rate limit string (e.g., "5/minute")

    Raises:
        RateLimitExceeded: If rate limit is exceeded
    """

    # Apply rate limit decorator dynamically
    @limiter.limit(rate_limit)
    def _rate_limited_check(req: Request) -> None:
        """Rate-limited helper function."""
        pass

    _rate_limited_check(request)


async def get_current_user(
    request: Request,
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(security),
) -> dict:
    """Dependency to get current authenticated user from Supabase.

    Args:
        request: FastAPI request object (for rate limiting)
        credentials: HTTP Bearer token from request header

    Returns:
        User dict with id, email, user_metadata, etc.

    Raises:
        HTTPException: 401 if authentication fails, 429 if rate limit exceeded
    """
    # Apply rate limiting for authentication attempts
    # Skip rate limiting for local profile
    if settings.PROFILE != "local":
        # Check if limiter is available (may not be in tests)
        limiter = getattr(request.app.state, "limiter", None)
        if limiter is not None:
            # Rate limit from config: production vs other profiles
            rate_limit = (
                settings.RATE_LIMIT_AUTH_PRODUCTION
                if settings.PROFILE == "production"
                else settings.RATE_LIMIT_AUTH_OTHER
            )
            # Check rate limit - this will raise RateLimitExceeded if exceeded
            try:
                _check_auth_rate_limit(request, limiter, rate_limit)
            except RateLimitExceeded:
                client_host = request.client.host if request.client else "unknown"
                logger.warning(
                    f"Rate limit exceeded for authentication attempt from {client_host}"
                )
                raise

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
