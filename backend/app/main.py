"""Main FastAPI application."""

import logging
import os
import subprocess
import time
import uuid
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Callable, Optional

import uvicorn
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles
from starlette.responses import Response

from app.api.routes import (
    admin,
    analysis,
    config,
    overlay_data,
    players,
    progress,
    serve_attempts,
    serve_detection,
    video,
)
from app.core.config import settings
from app.core.database import create_tables_if_not_exists
from app.utils.error_handling import (
    APIError,
    api_error_handler,
    general_error_handler,
    validation_error_handler,
)
from app.utils.logging_context import ObservabilityLogFilter
from app.utils.metrics import setup_metrics
from app.utils.otel import setup_otel_tracing

logger = logging.getLogger(__name__)

_otel_enabled = setup_otel_tracing(default_service_name="tennis-coach-api")
# Initialize metrics (uses same OTLP endpoint as traces). Return value is unused.
setup_metrics(default_service_name="tennis-coach-api")

# Add observability filter to root logger (adds trace_id/span_id to all logs)
root_logger = logging.getLogger()
root_logger.addFilter(ObservabilityLogFilter())


def validate_redis_url(url: str) -> bool:
    """
    Validate Redis URL format and components to prevent command injection.

    Args:
        url: Redis connection URL to validate

    Returns:
        True if URL is valid, False otherwise
    """
    import urllib.parse

    try:
        parsed = urllib.parse.urlparse(url)
        # Check scheme
        if parsed.scheme not in ("redis", "rediss"):
            return False
        # Check hostname exists and is safe
        if not parsed.hostname:
            return False
        # Validate hostname contains only safe characters
        if not all(c.isalnum() or c in ".-_" for c in parsed.hostname):
            return False
        # Check port exists and is in valid range
        return bool(parsed.port and 1 <= parsed.port <= 65535)
    except (ValueError, AttributeError, TypeError):
        return False


def start_rq_worker() -> Optional[subprocess.Popen]:
    """
    Start RQ worker process with duplicate check.

    Returns:
        Popen process object if started, None if skipped
    """
    try:
        from redis.exceptions import ConnectionError as RedisConnectionError
        from redis.exceptions import ResponseError as RedisResponseError
        from redis.exceptions import TimeoutError as RedisTimeoutError
        from rq import Worker

        from app.core.redis_config import redis_conn

        # Check for existing workers to prevent duplicates
        # This should detect Fly.io worker if it's running
        existing_workers = Worker.all(connection=redis_conn)
        if existing_workers:
            worker_names = [w.name for w in existing_workers]
            logger.warning(
                "Found %s existing worker(s): %s. Skipping worker startup on API service.",
                len(existing_workers),
                worker_names,
            )
            return None
        else:
            logger.info("No existing workers found in Redis")
    except (
        RedisConnectionError,
        RedisTimeoutError,
        RedisResponseError,
        AttributeError,
    ) as e:
        logger.warning(
            "Could not check for existing workers: %s. "
            "This might mean Redis is unavailable, quota exceeded, or connection failed. "
            "Worker startup will be skipped to avoid duplicates.",
            e,
        )
        # Don't start worker if we can't check - safer to skip than risk duplicates
        return None

    redis_url = os.getenv("REDIS_URL")
    if not redis_url:
        logger.warning("REDIS_URL not set, skipping worker startup")
        return None

    logger.info("Starting RQ worker process")
    try:
        # Validate redis_url format and components (security: prevent command injection)
        if not validate_redis_url(redis_url):
            from app.core.redis_config import _mask_redis_url

            logger.error("Invalid REDIS_URL format: %s", _mask_redis_url(redis_url))
            return None

        return subprocess.Popen(  # noqa: S603 - rq command is trusted, redis_url validated above
            ["rq", "worker", "analysis", "default", "--url", redis_url],  # noqa: S607 - validated URL prevents injection
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
        )
    except (subprocess.SubprocessError, OSError, ValueError) as e:
        logger.error("Failed to start RQ worker: %s", e)
        return None


@asynccontextmanager
async def lifespan(app: FastAPI) -> None:
    """Application lifespan manager."""
    # Startup
    logger.info("=" * 60)
    logger.info("Tennis Coach API - Starting up")
    logger.info("=" * 60)
    logger.info("Profile: %s", settings.PROFILE)
    logger.info("Auth Required: %s", settings.auth_required)
    logger.info("Debug Mode: %s", settings.DEBUG)
    db_url_display = (
        settings.database_url.split("@")[-1]
        if "@" in settings.database_url
        else settings.database_url
    )
    logger.info("Database: %s", db_url_display)
    logger.info("Storage Type: %s", settings.STORAGE_TYPE)
    logger.info("CORS Origins: %s", settings.BACKEND_CORS_ORIGINS)
    logger.info("=" * 60)
    create_tables_if_not_exists()

    # Worker startup logic
    # Only start worker if this is the API service and no dedicated worker service exists
    worker_process = None
    service_type = os.getenv("SERVICE_TYPE", "api").lower()

    if service_type == "api":
        logger.info("Running as API service - checking if worker should start...")
        # The worker startup function checks for existing workers to prevent duplicates
        # If a dedicated worker service is running, this should return None
        worker_process = start_rq_worker()
        if worker_process:
            logger.warning(
                "Started RQ worker on API service. "
                "Consider using a dedicated worker service (SERVICE_TYPE=worker) for better separation."
            )
        else:
            logger.info(
                "Skipped starting worker on API service "
                "(existing worker detected, REDIS_URL not set, or check failed)"
            )
    elif service_type == "worker":
        logger.info("Running as worker service - skipping API worker startup")

    yield

    # Shutdown
    if worker_process:
        logger.info("Terminating RQ worker process")
        try:
            worker_process.terminate()
            worker_process.wait(timeout=10)
            logger.info("RQ worker terminated successfully")
        except subprocess.TimeoutExpired:
            logger.warning("RQ worker did not terminate gracefully, killing")
            worker_process.kill()
        except (subprocess.SubprocessError, OSError) as e:
            logger.error("Error terminating RQ worker: %s", e)

    logger.info("Tennis Coach API - Shutting down")


# Create FastAPI app with lifespan
# Disable docs in production to prevent public API discovery
app = FastAPI(
    title="Tennis Coach API",
    description="AI-powered tennis video analysis API",
    version="0.1.0",
    lifespan=lifespan,
    docs_url="/docs" if settings.PROFILE == "local" else None,
    redoc_url="/redoc" if settings.PROFILE == "local" else None,
    openapi_url="/openapi.json" if settings.PROFILE == "local" else None,
)

if _otel_enabled:
    from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor

    FastAPIInstrumentor().instrument_app(app)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.BACKEND_CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# Middleware to block docs endpoints in production (defense in depth)
@app.middleware("http")
async def block_docs_in_production(request: Request, call_next: Callable) -> Response:
    """Block access to docs endpoints in production."""
    docs_paths = ["/docs", "/redoc", "/openapi.json"]

    if settings.PROFILE != "local" and request.url.path in docs_paths:
        return JSONResponse(status_code=404, content={"detail": "Not found"})

    return await call_next(request)


# Request processing time middleware
@app.middleware("http")
async def add_process_time_header(request: Request, call_next: Callable) -> Request:
    """Add processing time and request ID headers."""
    start_time = time.time()
    request_id = str(uuid.uuid4())

    # Add request ID to request state
    request.state.request_id = request_id

    response = await call_next(request)

    process_time = time.time() - start_time
    response.headers["X-Processing-Time"] = f"{process_time:.4f}"
    response.headers["X-Request-ID"] = request_id

    return response


# Register exception handlers
app.add_exception_handler(APIError, api_error_handler)
app.add_exception_handler(ValueError, validation_error_handler)
app.add_exception_handler(Exception, general_error_handler)


# Include API routes with versioning
app.include_router(
    video.router,
    prefix="/v0/videos",
    tags=["videos"],
    responses={
        400: {"description": "Bad Request"},
        404: {"description": "Not Found"},
        500: {"description": "Internal Server Error"},
    },
)


app.include_router(
    players.router,
    prefix="/v0/players",
    tags=["players"],
    responses={
        400: {"description": "Bad Request"},
        404: {"description": "Not Found"},
        500: {"description": "Internal Server Error"},
    },
)


app.include_router(
    analysis.router,
    responses={
        400: {"description": "Bad Request"},
        404: {"description": "Not Found"},
        500: {"description": "Internal Server Error"},
    },
)

app.include_router(
    overlay_data.router,
    responses={
        400: {"description": "Bad Request"},
        404: {"description": "Not Found"},
        500: {"description": "Internal Error"},
    },
)

app.include_router(
    progress.router,
    prefix="/v0/progress",
    tags=["progress"],
    responses={
        400: {"description": "Bad Request"},
        500: {"description": "Internal Server Error"},
    },
)

app.include_router(
    serve_attempts.router,
    prefix="/v0/serve-attempts",
    tags=["serve-attempts"],
    responses={
        400: {"description": "Bad Request"},
        404: {"description": "Not Found"},
        500: {"description": "Internal Server Error"},
    },
)

app.include_router(
    serve_detection.router,
    prefix="/v0",
    tags=["serve-detection"],
    responses={
        400: {"description": "Bad Request"},
        404: {"description": "Not Found"},
        500: {"description": "Internal Server Error"},
    },
)

app.include_router(
    config.router,
    prefix="/v0",
    tags=["config"],
    responses={
        400: {"description": "Bad Request"},
        500: {"description": "Internal Server Error"},
    },
)

app.include_router(
    admin.router,
    prefix="/v0/admin",
    tags=["admin"],
    responses={
        400: {"description": "Bad Request"},
        403: {"description": "Forbidden - Admin access required"},
        500: {"description": "Internal Server Error"},
    },
)

# Mount static files for processed videos
processed_videos_dir = Path("data/videos/processed")
if processed_videos_dir.exists():
    app.mount(
        "/processed", StaticFiles(directory=str(processed_videos_dir)), name="processed"
    )


@app.get("/")
async def root() -> dict[str, str]:
    """Root endpoint with API information."""
    response = {
        "message": "Tennis Coach API",
        "version": "0.1.0",
        "status": "alpha",
        "health": "/health",
    }

    # Only include docs URLs in local development
    if settings.PROFILE == "local":
        response["docs"] = "/docs"
        response["redoc"] = "/redoc"

    return response


@app.get("/health")
async def health_check() -> dict[str, str]:
    """Health check endpoint."""
    return {
        "status": "healthy",
        "version": "0.1.0",
        "timestamp": str(int(time.time())),
    }


@app.get("/v0")
async def api_info() -> dict[str, str]:
    """API version information."""
    return {
        "version": "0.1.0",
        "status": "alpha",
        "warning": "This API is in alpha stage. Breaking changes may occur without notice.",
        "endpoints": "videos: /v0/videos, serve-attempts: /v0/serve-attempts, players: /v0/players, overlay-data: /v0/overlay-data, analysis: /v0/analysis",
    }


if __name__ == "__main__":
    uvicorn.run(
        app,
        host=settings.API_HOST,
        port=settings.API_PORT,
        reload=settings.DEBUG,
    )
