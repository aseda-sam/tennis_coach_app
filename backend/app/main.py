"""Main FastAPI application."""

import time
import uuid
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Callable

import uvicorn
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

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
from app.core.database import create_tables
from app.utils.error_handling import (
    APIError,
    api_error_handler,
    general_error_handler,
    validation_error_handler,
)


@asynccontextmanager
async def lifespan(app: FastAPI) -> None:
    """Application lifespan manager."""
    # Startup
    create_tables()
    yield
    # Shutdown
    pass


# Create FastAPI app with lifespan
app = FastAPI(
    title="Tennis Coach API",
    description="AI-powered tennis video analysis API",
    version="0.1.0",
    lifespan=lifespan,
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.BACKEND_CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


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
    return {
        "message": "Tennis Coach API",
        "version": "0.1.0",
        "status": "alpha",
        "docs": "/docs",
        "redoc": "/redoc",
        "health": "/health",
    }


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
