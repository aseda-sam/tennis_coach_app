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

    This function manually checks rate limits using slowapi's storage API
    instead of the decorator pattern, which only works on route handlers.

    Args:
        request: FastAPI request object
        limiter: SlowAPI limiter instance
        rate_limit: Rate limit string (e.g., "5/minute")

    Raises:
        RateLimitExceeded: If rate limit is exceeded
    """
    import re

    from slowapi.util import get_remote_address

    # Get the IP address for rate limiting
    key = get_remote_address(request)

    # Create a unique endpoint identifier for auth checks
    endpoint = "__auth_check__"

    # Parse the rate limit string (e.g., "5/minute" -> count=5, period="minute")
    match = re.match(r"(\d+)/(\w+)", rate_limit)
    if not match:
        logger.warning(
            f"Invalid rate limit format: {rate_limit}, skipping rate limit check"
        )
        return

    limit_count = int(match.group(1))  # The "5" in "5/minute"
    period_str = match.group(2).lower()  # The "minute" in "5/minute"

    # Convert period to seconds
    period_map = {
        "second": 1,
        "seconds": 1,
        "minute": 60,
        "minutes": 60,
        "hour": 3600,
        "hours": 3600,
        "day": 86400,
        "days": 86400,
    }
    period_seconds = period_map.get(period_str, 60)  # Default to 60 seconds if unknown

    # Create storage key using the same format as slowapi
    key_prefix = getattr(limiter, "key_prefix", "LIMITER")
    storage_key = f"{key_prefix}{endpoint}:{key}"

    # Get the limiter's storage backend
    storage = limiter.storage

    # Check current count
    current_count = storage.get(storage_key, 0)

    # Check if limit exceeded
    if current_count >= limit_count:
        raise RateLimitExceeded(rate_limit, endpoint)

    # Increment the count with expiration
    # Use the storage's incr method if available, otherwise set with expiration
    try:
        if hasattr(storage, "incr"):
            storage.incr(storage_key, period_seconds)
        else:
            # Fallback: manually increment with expiration
            storage.set(storage_key, current_count + 1, period_seconds)
    except (RuntimeError, OSError, AttributeError) as e:
        # If storage operations fail, log but don't block the request
        # Fail open: better to allow requests than break the app if rate limiting fails
        # These exceptions cover storage backend errors, file system errors, and missing methods
        logger.warning(f"Failed to record rate limit: {e}, allowing request")


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
