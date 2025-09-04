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
    logger.info(f"⏱️ {operation_name} completed in {elapsed_time:.3f}s")


def log_timing_error(operation_name: str, start_time: float, error: Exception) -> None:
    """
    Log timing information for a failed operation.

    Args:
        operation_name: Name of the operation being timed
        start_time: Start time from time.time()
        error: The exception that occurred
    """
    elapsed_time = time.time() - start_time
    logger.error(f"❌ {operation_name} failed after {elapsed_time:.3f}s: {error}")
