"""Service for video streaming and URL generation."""

import logging
from typing import Optional

from fastapi import Response
from fastapi.responses import FileResponse, RedirectResponse, StreamingResponse
from sqlalchemy.orm import Session

from app.core.config import settings
from app.models.video import Video
from app.services import video_service
from app.services.storage_service import storage_service
from app.utils.file_validation import get_safe_filename, validate_file_exists

logger = logging.getLogger(__name__)


def get_video_stream_response(
    db_video: Video,
    current_user: Optional[dict] = None,
) -> Response:
    """Get streaming response for a video.

    The caller is responsible for fetching db_video and closing the DB session
    before calling this function — the session must not be held open while
    the response streams, or it will exhaust the connection pool.

    Args:
        db_video: Already-fetched Video ORM object
        current_user: Optional user dict (used for logging only)

    Returns:
        Response object (FileResponse, RedirectResponse, or StreamingResponse)

    Raises:
        RuntimeError: If storage operations fail
    """
    # Use storage service to get file
    if settings.STORAGE_TYPE == "supabase":
        # For active demo videos, use public demo bucket URL
        if db_video.is_active_demo and settings.SUPABASE_DEMO_BUCKET:
            try:
                # Demo videos should be stored with 'demo/' prefix in demo bucket
                demo_path = db_video.file_path
                if not demo_path.startswith("demo/"):
                    demo_path = f"demo/{db_video.id}_{db_video.filename}"
                demo_url = storage_service.get_demo_public_url(demo_path)
                logger.info(
                    "Redirecting to demo bucket URL for active demo video %s: %s",
                    db_video.id,
                    demo_url,
                )
                return RedirectResponse(url=demo_url)
            except (ValueError, RuntimeError) as e:
                logger.error(
                    "Failed to get demo bucket URL for video %s: %s", db_video.id, e
                )
                # Fallback to regular flow

        # For regular videos, use private bucket with signed URL or public URL
        storage_path = db_video.file_path
        try:
            file_url = storage_service.get_file_url(storage_path)
            logger.info(
                "Redirecting to Supabase URL for video %s: %s", db_video.id, file_url
            )
            return RedirectResponse(url=file_url)
        except (ValueError, RuntimeError, OSError) as e:
            logger.error(
                "Failed to get Supabase URL for video %s, storage_path=%s: %s",
                db_video.id,
                storage_path,
                e,
            )
            # Fallback: download and stream
            file_data = storage_service.download_file(storage_path)
            return StreamingResponse(
                iter([file_data]),
                media_type=db_video.content_type or "video/mp4",
                headers={
                    "Content-Disposition": f'inline; filename="{get_safe_filename(db_video.filename)}"'
                },
            )
    else:
        # For local storage, resolve the storage path to actual file system path
        resolved_path = storage_service.get_local_file_path(db_video.file_path)
        validate_file_exists(resolved_path, db_video.filename)

        return FileResponse(
            path=str(resolved_path),
            media_type=db_video.content_type or "video/mp4",
            filename=get_safe_filename(db_video.filename),
        )


def get_video_url(
    db: Session,
    video_id: int,
    current_user: Optional[dict] = None,
) -> str:
    """Get a signed/public URL for a video.

    Args:
        db: Database session
        video_id: Video ID
        current_user: Optional user dict for authorization

    Returns:
        URL string

    Raises:
        ValueError: If video not found or URL generation fails
        RuntimeError: If storage operations fail
    """
    db_video = video_service.get_video_by_id(db, video_id)
    if not db_video:
        raise ValueError(f"Video with ID {video_id} not found")

    if settings.STORAGE_TYPE == "supabase":
        # For active demo videos, use public demo bucket URL
        if db_video.is_active_demo and settings.SUPABASE_DEMO_BUCKET:
            demo_path = db_video.file_path
            if not demo_path.startswith("demo/"):
                demo_path = f"demo/{db_video.id}_{db_video.filename}"
            return storage_service.get_demo_public_url(demo_path)

        # For regular videos, get signed URL or public URL
        return storage_service.get_file_url(db_video.file_path)
    else:
        # For local storage, return a relative path or construct a URL
        # This would typically be handled by the frontend constructing the URL
        # based on the API base URL
        raise ValueError("URL generation not supported for local storage")
