"""Rate limiting configuration (shared across routes)."""

from slowapi import Limiter
from slowapi.util import get_remote_address

from app.core.config import settings

# Disable rate limiting in local/test environments
limiter = Limiter(
    key_func=get_remote_address,
    default_limits=["60/minute"],
    enabled=settings.PROFILE not in ("local", "test"),
)
