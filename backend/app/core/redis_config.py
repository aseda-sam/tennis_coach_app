"""
Redis configuration for RQ
"""

import logging
import multiprocessing
import os

from redis import Redis
from rq import Queue

logger = logging.getLogger(__name__)

# Get Redis URL from environment or use default
REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379/0")

# Create Redis connection
try:
    redis_conn = Redis.from_url(REDIS_URL)
    # Test connection
    redis_conn.ping()
    logger.info(f"Successfully connected to Redis at {REDIS_URL}")
except Exception as e:
    logger.error(f"Failed to connect to Redis: {e}")
    raise

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
    Get recommended worker count based on environment.

    Local development: Use 2-4 workers (M1 MacBook has 8 cores)
    Production (free tier): Use 1 worker (limited resources)
    """
    env = os.getenv("ENVIRONMENT", "development").lower()

    if env == "production":
        # Free tier: very limited resources
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
        "environment": os.getenv("ENVIRONMENT", "development"),
        "redis_url": REDIS_URL,
    }
