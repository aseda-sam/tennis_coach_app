"""OpenTelemetry helpers (small, optional, safe to import).

This module exists so API + worker can share the same tracing setup.
If OTEL_EXPORTER_OTLP_ENDPOINT is not set, tracing is disabled (no-op).
"""

from __future__ import annotations

import atexit
import logging
import os

logger = logging.getLogger(__name__)

_tracer_provider = None


def setup_otel_tracing(*, default_service_name: str) -> bool:
    """
    Configure OpenTelemetry tracing using OTLP HTTP exporter and env vars.

    Reads (standard OTel env vars):
    - OTEL_EXPORTER_OTLP_ENDPOINT (required to enable)
    - OTEL_EXPORTER_OTLP_HEADERS (auth, etc.)
    - OTEL_EXPORTER_OTLP_PROTOCOL (e.g. http/protobuf)
    - OTEL_SERVICE_NAME (optional override)

    Returns True if configured, False if disabled or setup failed.
    """
    global _tracer_provider

    endpoint = os.getenv("OTEL_EXPORTER_OTLP_ENDPOINT")
    if not endpoint:
        return False

    try:
        from opentelemetry import trace
        from opentelemetry.exporter.otlp.proto.http.trace_exporter import (
            OTLPSpanExporter,
        )
        from opentelemetry.sdk.resources import Resource
        from opentelemetry.sdk.trace import TracerProvider
        from opentelemetry.sdk.trace.export import BatchSpanProcessor

        service_name = os.getenv("OTEL_SERVICE_NAME", default_service_name)

        # Let the SDK read OTEL_EXPORTER_OTLP_* env vars automatically.
        exporter = OTLPSpanExporter()

        resource = Resource.create({"service.name": service_name})
        _tracer_provider = TracerProvider(resource=resource)
        _tracer_provider.add_span_processor(BatchSpanProcessor(exporter))
        trace.set_tracer_provider(_tracer_provider)

        # Flush spans on exit so they aren't lost when the process terminates
        atexit.register(_flush_traces)

        logger.info(
            "OpenTelemetry tracer configured (service=%s, endpoint=%s)",
            service_name,
            endpoint.split("//")[-1].split("/")[0] + "/...",
        )
        return True
    except Exception as e:  # noqa: BLE001
        logger.warning("OpenTelemetry setup failed: %s", e)
        return False


def _flush_traces() -> None:
    """Force-flush pending spans (called at exit)."""
    if _tracer_provider is not None:
        try:
            _tracer_provider.force_flush(timeout_millis=5000)
            logger.debug("OTel traces flushed on exit")
        except Exception as e:  # noqa: BLE001
            logger.warning("OTel flush failed: %s", e)
