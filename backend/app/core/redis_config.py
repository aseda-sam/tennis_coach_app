"""
Redis configuration for RQ
"""

import logging
import multiprocessing
import os
import time
from collections import defaultdict
from urllib.parse import urlparse, urlunparse

from redis import Redis
from redis.exceptions import ConnectionError as RedisConnectionError
from redis.exceptions import ResponseError as RedisResponseError
from redis.exceptions import TimeoutError as RedisTimeoutError
from rq import Queue

logger = logging.getLogger(__name__)


def _mask_redis_url(url: str) -> str:
    """
    Mask password in Redis URL for safe logging.

    Args:
        url: Redis URL that may contain credentials

    Returns:
        Redis URL with password masked as ****
    """
    try:
        parsed = urlparse(url)
        if parsed.password:
            # Mask password while preserving other parts
            masked_netloc = f"{parsed.username or ''}:****@{parsed.hostname}"
            if parsed.port:
                masked_netloc += f":{parsed.port}"
            masked = parsed._replace(netloc=masked_netloc)
            return urlunparse(masked)
        return url
    except (ValueError, AttributeError):
        # If parsing fails, return a safe default
        return "redis://****@****"


# Get Redis URL from environment or use default
REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379/0")

# Create Redis connection (lazy - only connects when used)
# This allows the module to load even if Redis isn't available (e.g., in CI tests)
# Increased timeouts for production stability (was 1s, now 5s connect, 10s socket)


class InstrumentedRedis(Redis):
    """Redis client with lightweight command metrics logging."""

    def __init__(self, *args: object, **kwargs: object) -> None:
        super().__init__(*args, **kwargs)
        self._metrics_enabled = os.getenv("REDIS_COMMAND_METRICS", "").lower() in (
            "1",
            "true",
            "yes",
        )
        self._log_every = _safe_int(os.getenv("REDIS_COMMAND_LOG_EVERY", "100"), 100)
        self._log_interval = _safe_int(
            os.getenv("REDIS_COMMAND_LOG_INTERVAL", "60"), 60
        )
        self._last_log_time = time.monotonic()
        self._total_commands = 0
        self._command_counts = defaultdict(int)

    def execute_command(self, *args: object, **options: object) -> object:
        if self._metrics_enabled and args:
            command = str(args[0]).upper()
            self._command_counts[command] += 1
            self._total_commands += 1
            now = time.monotonic()
            if (
                self._total_commands % self._log_every == 0
                or now - self._last_log_time >= self._log_interval
            ):
                top_commands = sorted(
                    self._command_counts.items(),
                    key=lambda item: item[1],
                    reverse=True,
                )[:5]
                logger.info(
                    "Redis command stats: total=%s top=%s",
                    self._total_commands,
                    top_commands,
                )
                self._last_log_time = now
                self._command_counts.clear()
        return super().execute_command(*args, **options)


def _safe_int(value: str, default: int) -> int:
    try:
        return int(value)
    except (TypeError, ValueError):
        return default


redis_conn = InstrumentedRedis.from_url(
    REDIS_URL,
    socket_connect_timeout=5,  # 5 seconds to establish connection
    socket_timeout=10,  # 10 seconds for socket operations
    retry_on_timeout=True,  # Retry on timeout errors
    health_check_interval=30,  # Check connection health every 30s
)

# Test connection lazily - only log, don't raise
# This allows tests to run without Redis
try:
    redis_conn.ping()
    logger.info(f"Successfully connected to Redis at {_mask_redis_url(REDIS_URL)}")
except (RedisConnectionError, RedisTimeoutError, OSError) as e:
    logger.warning(
        f"Redis not available at {_mask_redis_url(REDIS_URL)}: {e}. "
        "Some features (background tasks) will not work until Redis is available."
    )
    # Don't raise - allow module to load for testing
except RedisResponseError as e:
    # Catch Redis response errors (e.g., quota exceeded on Upstash free tier)
    logger.warning(
        f"Redis error at {_mask_redis_url(REDIS_URL)}: {e}. "
        "Some features (background tasks) may not work."
    )
    # Don't raise - allow module to load

# Create default queue
default_queue = Queue("default", connection=redis_conn)

# Create analysis queue (for future use)
analysis_queue = Queue("analysis", connection=redis_conn)


# Worker configuration helpers
def get_cpu_count() -> int:
    """Get number of CPU cores."""
    return multiprocessing.cpu_count()


def get_recommended_worker_count() -> int:
    """
    Get recommended worker count based on profile.

    Local development: Use 2-4 workers (M1 MacBook has 8 cores)
    Production: Use 1 worker (conservative for managed services)
    """
    profile = os.getenv("PROFILE", "local").lower()

    if profile == "production":
        # Production: conservative worker count for managed services
        return 1

    # Local development: M1 MacBook Pro considerations
    cpu_count = get_cpu_count()

    # For video analysis (CPU + memory intensive), use fewer workers
    # M1 MacBook: 8 cores, but video analysis is heavy
    # Recommended: 2-4 workers
    if cpu_count >= 8:
        return min(4, cpu_count // 2)  # Use half the cores, max 4
    elif cpu_count >= 4:
        return 2
    else:
        return 1


def get_worker_info() -> dict:
    """Get information about worker configuration."""
    return {
        "cpu_count": get_cpu_count(),
        "recommended_workers": get_recommended_worker_count(),
        "profile": os.getenv("PROFILE", "local"),
        "redis_url": _mask_redis_url(REDIS_URL),  # Mask credentials in response
    }
