"""
Timing utilities for performance monitoring and logging.
"""

import logging
import time

logger = logging.getLogger(__name__)


def log_timing(operation_name: str, start_time: float) -> None:
    """
    Log timing information for an operation.

    Args:
        operation_name: Name of the operation being timed
        start_time: Start time from time.time()
    """
    elapsed_time = time.time() - start_time
    logger.info("⏱️ %s completed in %.3fs", operation_name, elapsed_time)


def log_timing_error(operation_name: str, start_time: float, error: Exception) -> None:
    """
    Log timing information for a failed operation.

    Args:
        operation_name: Name of the operation being timed
        start_time: Start time from time.time()
        error: The exception that occurred
    """
    elapsed_time = time.time() - start_time
    logger.error("❌ %s failed after %.3fs: %s", operation_name, elapsed_time, error)
