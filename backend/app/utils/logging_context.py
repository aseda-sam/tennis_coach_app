"""Structured logging utilities.

Adds canonical IDs (request_id, job_id, video_id, rq_job_id) to log records
for correlation and debugging.
"""

from __future__ import annotations

import logging
from typing import Any, Optional


class StructuredLogFilter(logging.Filter):
    """Log filter that adds request/job IDs to log records for structured logging."""

    def filter(self, record: logging.LogRecord) -> bool:
        """Add structured context fields to log record."""
        # Ensure optional fields exist (set via extra={} or default to None)
        if not hasattr(record, "request_id"):
            record.request_id = None
        if not hasattr(record, "job_id"):
            record.job_id = None
        if not hasattr(record, "video_id"):
            record.video_id = None
        if not hasattr(record, "rq_job_id"):
            record.rq_job_id = None

        return True


def get_log_extra(
    *,
    request_id: Optional[str] = None,
    job_id: Optional[str] = None,
    video_id: Optional[int] = None,
    rq_job_id: Optional[str] = None,
) -> dict[str, Any]:
    """
    Build extra dict for structured logging with canonical IDs.

    Usage:
        logger.info("Processing video", extra=get_log_extra(video_id=123, job_id="abc"))

    Returns dict with keys: request_id, job_id, video_id, rq_job_id (only non-None values).
    """
    extra: dict[str, Any] = {}
    if request_id:
        extra["request_id"] = request_id
    if job_id:
        extra["job_id"] = job_id
    if video_id is not None:
        extra["video_id"] = video_id
    if rq_job_id:
        extra["rq_job_id"] = rq_job_id
    return extra
