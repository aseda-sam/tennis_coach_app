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
    analysis,
    ball_contacts,
    ball_detection,
    players,
    pose_detection,
    video,
    video_annotation,
    video_players,
    video_quality,
)
from app.core.config import settings
from app.core.database import create_tables_if_not_exists
from app.utils.error_handling import (
    APIError,
    api_error_handler,
    general_error_handler,
    validation_error_handler,
)

logger = logging.getLogger(__name__)


def start_rq_worker() -> Optional[subprocess.Popen]:
    """
    Start RQ worker process with duplicate check.

    Returns:
        Popen process object if started, None if skipped
    """
    try:
        from redis.exceptions import ConnectionError as RedisConnectionError
        from redis.exceptions import TimeoutError as RedisTimeoutError
        from rq import Worker

        from app.core.redis_config import redis_conn

        # Check for existing workers to prevent duplicates
        existing_workers = Worker.all(connection=redis_conn)
        if existing_workers:
            logger.warning(
                f"Found {len(existing_workers)} existing workers, skipping startup"
            )
            return None
    except (RedisConnectionError, RedisTimeoutError, AttributeError) as e:
        logger.warning(f"Could not check for existing workers: {e}")

    redis_url = os.getenv("REDIS_URL")
    if not redis_url:
        logger.warning("REDIS_URL not set, skipping worker startup")
        return None

    logger.info("Starting RQ worker process")
    try:
        # Validate redis_url format (basic check)
        if not redis_url.startswith(("redis://", "rediss://")):
            from app.core.redis_config import _mask_redis_url

            logger.error(f"Invalid REDIS_URL format: {_mask_redis_url(redis_url)}")
            return None

        return subprocess.Popen(  # noqa: S603 - rq command is trusted, redis_url validated above
            ["rq", "worker", "analysis", "default", "--url", redis_url],  # noqa: S607 - rq is trusted executable
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
        )
    except (subprocess.SubprocessError, OSError, ValueError) as e:
        logger.error(f"Failed to start RQ worker: {e}")
        return None


@asynccontextmanager
async def lifespan(app: FastAPI) -> None:
    """Application lifespan manager."""
    # Startup
    logger.info("=" * 60)
    logger.info("Tennis Coach API - Starting up")
    logger.info("=" * 60)
    logger.info(f"Profile: {settings.PROFILE}")
    logger.info(f"Auth Required: {settings.auth_required}")
    logger.info(f"Debug Mode: {settings.DEBUG}")
    logger.info(
        f"Database: {settings.database_url.split('@')[-1] if '@' in settings.database_url else settings.database_url}"
    )
    logger.info(f"Storage Type: {settings.STORAGE_TYPE}")
    logger.info(f"CORS Origins: {settings.BACKEND_CORS_ORIGINS}")
    logger.info("=" * 60)
    create_tables_if_not_exists()

    # Start RQ worker in production
    worker_process = None
    if os.getenv("ENVIRONMENT") == "production":
        worker_process = start_rq_worker()

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
            logger.error(f"Error terminating RQ worker: {e}")

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
    ball_contacts.router,
    prefix="/v0/ball-contacts",
    tags=["ball-contacts"],
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
    video_players.router,
    tags=["video-players"],
    responses={
        400: {"description": "Bad Request"},
        404: {"description": "Not Found"},
        500: {"description": "Internal Server Error"},
    },
)

app.include_router(
    video_quality.router,
    responses={
        400: {"description": "Bad Request"},
        404: {"description": "Not Found"},
        500: {"description": "Internal Server Error"},
    },
)

app.include_router(
    ball_detection.router,
    responses={
        400: {"description": "Bad Request"},
        404: {"description": "Not Found"},
        500: {"description": "Internal Server Error"},
    },
)

app.include_router(
    pose_detection.router,
    responses={
        400: {"description": "Bad Request"},
        404: {"description": "Not Found"},
        500: {"description": "Internal Server Error"},
    },
)

app.include_router(
    video_annotation.router,
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
        "endpoints": "videos: /v0/videos, ball-contacts: /v0/ball-contacts, players: /v0/players, video-quality: /v0/video-quality, ball-detection: /v0/ball-detection, pose-detection: /v0/pose-detection, analysis: /v0/analysis",
    }


if __name__ == "__main__":
    uvicorn.run(
        app,
        host=settings.API_HOST,
        port=settings.API_PORT,
        reload=settings.DEBUG,
    )
