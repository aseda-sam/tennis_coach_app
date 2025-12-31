"""Authentication dependencies for protected routes."""

from typing import Optional

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from app.core.config import settings
from app.utils.supabase_auth import verify_supabase_token

security = HTTPBearer()


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
    # Skip auth when PROFILE=local
    if settings.PROFILE == "local":
        # Return mock user for local testing
        return {
            "id": "00000000-0000-0000-0000-000000000000",
            "email": "dev@localhost",
            "user_metadata": {},
        }

    if not credentials:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication required",
        )

    token = credentials.credentials
    user = verify_supabase_token(token)

    if user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid authentication credentials",
        )

    return user
