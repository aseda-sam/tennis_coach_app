"""OpenTelemetry metrics helpers for job tracking.

Provides counters, histograms, and gauges for observability.
"""

from __future__ import annotations

import logging
from typing import Optional

logger = logging.getLogger(__name__)

_metrics_enabled = False
_meter = None
_jobs_started_counter = None
_jobs_succeeded_counter = None
_jobs_failed_counter = None
_job_duration_histogram = None


def setup_metrics() -> bool:
    """
    Initialize OTel metrics (counters, histograms).

    Returns True if metrics are enabled, False otherwise.
    """
    global _metrics_enabled, _meter, _jobs_started_counter, _jobs_succeeded_counter
    global _jobs_failed_counter, _job_duration_histogram

    try:
        from opentelemetry import metrics

        _meter = metrics.get_meter(__name__, "0.1.0")

        # Counters: job lifecycle events
        _jobs_started_counter = _meter.create_counter(
            name="jobs_started_total",
            description="Total number of jobs started",
            unit="1",
        )
        _jobs_succeeded_counter = _meter.create_counter(
            name="jobs_succeeded_total",
            description="Total number of jobs that completed successfully",
            unit="1",
        )
        _jobs_failed_counter = _meter.create_counter(
            name="jobs_failed_total",
            description="Total number of jobs that failed",
            unit="1",
        )

        # Histogram: job duration
        _job_duration_histogram = _meter.create_histogram(
            name="job_duration_seconds",
            description="Job execution duration in seconds",
            unit="s",
        )

        _metrics_enabled = True
        logger.debug("OTel metrics initialized")
        return True
    except Exception as e:  # noqa: BLE001
        logger.debug("OTel metrics not available: %s", e)
        return False


def record_job_started(job_type: str, video_id: Optional[int] = None) -> None:
    """Record that a job has started."""
    if not _metrics_enabled or _jobs_started_counter is None:
        return
    try:
        attributes = {"job_type": job_type}
        if video_id is not None:
            attributes["video_id"] = str(video_id)
        _jobs_started_counter.add(1, attributes=attributes)
    except Exception:  # noqa: BLE001, S110 - Metrics may fail silently
        pass


def record_job_succeeded(
    job_type: str, duration_seconds: float, video_id: Optional[int] = None
) -> None:
    """Record that a job completed successfully."""
    if not _metrics_enabled:
        return
    try:
        attributes = {"job_type": job_type}
        if video_id is not None:
            attributes["video_id"] = str(video_id)

        if _jobs_succeeded_counter:
            _jobs_succeeded_counter.add(1, attributes=attributes)

        if _job_duration_histogram:
            _job_duration_histogram.record(duration_seconds, attributes=attributes)
    except Exception:  # noqa: BLE001, S110 - Metrics may fail silently
        pass


def record_job_failed(
    job_type: str,
    duration_seconds: Optional[float] = None,
    video_id: Optional[int] = None,
) -> None:
    """Record that a job failed."""
    if not _metrics_enabled or _jobs_failed_counter is None:
        return
    try:
        attributes = {"job_type": job_type}
        if video_id is not None:
            attributes["video_id"] = str(video_id)

        _jobs_failed_counter.add(1, attributes=attributes)

        if duration_seconds is not None and _job_duration_histogram:
            _job_duration_histogram.record(duration_seconds, attributes=attributes)
    except Exception:  # noqa: BLE001, S110 - Metrics may fail silently
        pass


# Initialize metrics on import (if OTel is configured)
setup_metrics()
