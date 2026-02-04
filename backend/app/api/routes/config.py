"""Config API routes."""

from fastapi import APIRouter

from app.api.schemas.config import AppConfigResponse, UploadLimits
from app.core.config import settings

router = APIRouter(tags=["config"])


@router.get("/config", response_model=AppConfigResponse)
async def get_app_config() -> AppConfigResponse:
    """Get public app configuration for clients."""
    return AppConfigResponse(
        upload_limits=UploadLimits(
            max_file_size_bytes=settings.effective_max_file_size,
            max_video_duration_seconds=settings.effective_max_video_duration,
            supported_formats=settings.SUPPORTED_FORMATS,
        )
    )
