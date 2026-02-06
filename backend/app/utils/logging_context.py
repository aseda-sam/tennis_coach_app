"""Structured logging utilities for observability.

Adds canonical IDs (trace_id, span_id, request_id, job_id, video_id) to log records
so logs can be correlated with traces in Grafana.
"""

from __future__ import annotations

import logging
from typing import Any, Optional


class ObservabilityLogFilter(logging.Filter):
    """Log filter that adds OTel trace/span IDs and request/job IDs to log records."""

    def filter(self, record: logging.LogRecord) -> bool:
        """Add observability context to log record."""
        try:
            from opentelemetry import trace

            # Get current span context (if any)
            span = trace.get_current_span()
            if span:
                span_context = span.get_span_context()
                if span_context.is_valid:
                    # Add trace_id and span_id as hex strings (standard format)
                    record.trace_id = format(span_context.trace_id, "032x")
                    record.span_id = format(span_context.span_id, "016x")
                else:
                    record.trace_id = None
                    record.span_id = None
            else:
                record.trace_id = None
                record.span_id = None
        except Exception:  # noqa: BLE001 - OTel may not be available
            record.trace_id = None
            record.span_id = None

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
