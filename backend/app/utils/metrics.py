"""OpenTelemetry metrics helpers for job tracking.

Provides counters, histograms, and gauges for observability.
Metrics are exported to the same OTLP endpoint as traces (Grafana Cloud).
"""

from __future__ import annotations

import atexit
import logging
import os
from typing import Optional

logger = logging.getLogger(__name__)

_metrics_enabled = False
_meter = None
_meter_provider = None
_jobs_started_counter = None
_jobs_succeeded_counter = None
_jobs_failed_counter = None
_job_duration_histogram = None
_queue_wait_histogram = None


def setup_metrics(*, default_service_name: str = "tennis-coach-api") -> bool:
    """
    Initialize OTel metrics (counters, histograms) with OTLP exporter.

    Uses the same OTLP endpoint as tracing (OTEL_EXPORTER_OTLP_ENDPOINT).
    Returns True if metrics are enabled, False otherwise.
    """
    global _metrics_enabled, _meter, _meter_provider
    global _jobs_started_counter, _jobs_succeeded_counter
    global _jobs_failed_counter, _job_duration_histogram, _queue_wait_histogram

    endpoint = os.getenv("OTEL_EXPORTER_OTLP_ENDPOINT")
    if not endpoint:
        return False

    try:
        from opentelemetry import metrics
        from opentelemetry.exporter.otlp.proto.http.metric_exporter import (
            OTLPMetricExporter,
        )
        from opentelemetry.sdk.metrics import MeterProvider
        from opentelemetry.sdk.metrics.export import PeriodicExportingMetricReader
        from opentelemetry.sdk.resources import Resource

        service_name = os.getenv("OTEL_SERVICE_NAME", default_service_name)

        # Let the SDK read OTEL_EXPORTER_OTLP_* env vars automatically
        exporter = OTLPMetricExporter()

        resource = Resource.create({"service.name": service_name})
        # Export metrics every 30 seconds
        reader = PeriodicExportingMetricReader(exporter, export_interval_millis=30000)
        _meter_provider = MeterProvider(resource=resource, metric_readers=[reader])
        metrics.set_meter_provider(_meter_provider)

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

        # Histogram: queue wait time (enqueue → worker pickup)
        _queue_wait_histogram = _meter.create_histogram(
            name="queue_wait_seconds",
            description="Time job spent waiting in queue before worker picked it up",
            unit="s",
        )

        # Flush metrics on exit
        atexit.register(_flush_metrics)

        _metrics_enabled = True
        logger.debug("OTel metrics initialized (service=%s)", service_name)
        return True
    except Exception as e:  # noqa: BLE001
        logger.debug("OTel metrics not available: %s", e)
        return False


def _flush_metrics() -> None:
    """Force-flush pending metrics (called at exit)."""
    if _meter_provider is not None:
        try:
            _meter_provider.force_flush(timeout_millis=5000)
            logger.debug("OTel metrics flushed on exit")
        except Exception as e:  # noqa: BLE001
            logger.warning("OTel metrics flush failed: %s", e)


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


def record_queue_wait(
    job_type: str, wait_seconds: float, video_id: Optional[int] = None
) -> None:
    """Record how long a job waited in queue before worker picked it up."""
    if not _metrics_enabled or _queue_wait_histogram is None:
        return
    try:
        attributes = {"job_type": job_type}
        if video_id is not None:
            attributes["video_id"] = str(video_id)
        _queue_wait_histogram.record(wait_seconds, attributes=attributes)
    except Exception:  # noqa: BLE001, S110 - Metrics may fail silently
        pass


# Metrics are initialized explicitly in main.py and start_rq_worker.py
# (not on import, to ensure proper service name and OTLP endpoint)
