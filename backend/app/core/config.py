"""Simplified application settings for hobby project."""

import logging
import os
from pathlib import Path
from typing import Optional

from pydantic_settings import BaseSettings, SettingsConfigDict

logger = logging.getLogger(__name__)


class Settings(BaseSettings):
    """Application settings - simplified for hobby project."""

    # ONE setting: local or production
    PROFILE: str = "local"

    # API
    API_HOST: str = "0.0.0.0"
    API_PORT: int = 8000
    DEBUG: bool = False

    # Database (auto-detected from PROFILE)
    DATABASE_URL: Optional[str] = None  # Override default PostgreSQL URL if needed
    SUPABASE_DB_URL: Optional[str] = None  # Required if PROFILE=production

    # Supabase (only needed if PROFILE=production)
    SUPABASE_URL: Optional[str] = None
    SUPABASE_SECRET_KEY: Optional[str] = None
    SUPABASE_STORAGE_BUCKET: Optional[str] = None
    SUPABASE_DEMO_BUCKET: Optional[str] = None

    # Storage (auto-detected: local → local, production → supabase)
    UPLOAD_DIR: str = "../data/videos/raw"
    PROCESSED_DIR: str = "../data/videos/processed"
    MAX_FILE_SIZE: int = 104857600  # 100MB
    SUPPORTED_FORMATS: list[str] = [".mp4", ".mov", ".avi", ".mkv", ".wmv"]

    # Redis (optional - defaults to localhost)
    REDIS_URL: Optional[str] = None
    SERVICE_TYPE: Optional[str] = None  # 'api' or 'worker'

    # Background job behavior
    AUTO_ENQUEUE_ON_UPLOAD: bool = False

    # ML Models
    ML_MODELS_DIR: str = "ml_models"

    # Pose Detection
    POSE_DETECTION_CONFIDENCE: float = 0.5
    POSE_TRACKING_CONFIDENCE: float = 0.5
    POSE_OVERALL_CONFIDENCE: float = 0.8

    # Serve Detection
    SERVE_DETECTION_LOW_CONFIDENCE_THRESHOLD: float = (
        0.6  # Proposals below this are "uncertain"
    )

    # Processing limits
    MAX_VIDEO_DURATION: int = 300  # 5 minutes
    FRAME_SKIP_RATIO: int = 1
    MAX_VIDEO_RESOLUTION: tuple[int, int] = (3840, 2160)  # 4K
    MAX_FPS: int = 60
    FPS_TOLERANCE: float = 0.5
    POSE_DETECTION_JOB_TIMEOUT_SECONDS: int = 1800

    # Scout mode settings
    SCOUT_FRAME_SKIP: int = (
        2  # Process every Nth frame in scout mode (2 = 15fps effective at 30fps)
    )

    # Transcoding settings
    TRANSCODE_ENABLED: bool = True
    TRANSCODE_THRESHOLD_BYTES: int = (
        20 * 1024 * 1024
    )  # 20MB - skip transcoding for smaller files
    TRANSCODE_RESOLUTION: int = 720  # height in pixels
    TRANSCODE_FPS: int = 30
    TRANSCODE_CRF: int = 23  # quality (lower = better, 18-28 typical)

    # Upload limits (primarily for production)
    # Note: enforced only when PROFILE != "local" and user is not admin.
    MAX_VIDEO_UPLOADS_PER_DAY: int = 20

    # CORS
    BACKEND_CORS_ORIGINS: list[str] = [
        "http://localhost:3000",
        "http://127.0.0.1:3000",
        "https://aseda-sam.github.io",
    ]

    # Admin access (comma-separated Supabase auth user UUIDs)
    # In PROFILE=local, the auth dependency returns the mock user id below, so local dev
    # can access admin-only endpoints by default.
    ADMIN_USER_IDS: str = "00000000-0000-0000-0000-000000000000"

    # Demo (for demo videos)
    DEMO_USER_ID: str = "00000000-0000-0000-0000-000000000001"

    model_config = SettingsConfigDict(
        env_file=".env",
        case_sensitive=True,
        extra="ignore",  # ignore unknown env vars (e.g. OTEL_* for OpenTelemetry)
    )

    @property
    def admin_user_ids(self) -> list[str]:
        """Admin allowlist parsed from ADMIN_USER_IDS env var."""
        return [uid.strip() for uid in self.ADMIN_USER_IDS.split(",") if uid.strip()]

    @property
    def database_url(self) -> str:
        """Get database URL - auto-detected from PROFILE."""
        if self.PROFILE == "local":
            # Use DATABASE_URL if provided, otherwise auto-detect Docker vs local
            if self.DATABASE_URL:
                return self.DATABASE_URL

            # Detect if running in Docker (check for /.dockerenv)
            # In Docker, use service name 'postgres'; locally use 'localhost'
            postgres_host = "postgres" if os.path.exists("/.dockerenv") else "localhost"
            return f"postgresql://tennis:tennis_dev@{postgres_host}:5432/tennis_coach"

        if not self.SUPABASE_DB_URL:
            raise ValueError("SUPABASE_DB_URL required when PROFILE=production")
        return self.SUPABASE_DB_URL

    @property
    def storage_type(self) -> str:
        """Get storage type - auto-detected from PROFILE."""
        return "local" if self.PROFILE == "local" else "supabase"

    @property
    def auth_required(self) -> bool:
        """Auth required? Only in production."""
        return self.PROFILE == "production"

    @property
    def redis_url(self) -> str:
        """Get Redis URL - defaults to localhost."""
        return self.REDIS_URL or "redis://localhost:6379/0"

    @property
    def STORAGE_TYPE(self) -> str:  # noqa: N802 - matches existing API
        """Storage type - auto-detected from PROFILE."""
        return self.storage_type

    @property
    def effective_max_file_size(self) -> int:
        """Max file size - smaller in production."""
        return (
            52428800 if self.PROFILE == "production" else self.MAX_FILE_SIZE
        )  # 50MB prod, 100MB local

    @property
    def effective_max_video_duration(self) -> int:
        """Max video duration - smaller in production."""
        return (
            60 if self.PROFILE == "production" else self.MAX_VIDEO_DURATION
        )  # 1min prod, 5min local

    @property
    def effective_frame_skip_ratio(self) -> int:
        """Frame skip ratio."""
        return self.FRAME_SKIP_RATIO


# Create settings
settings = Settings()

# Validate production config
if settings.PROFILE == "production":
    required = {
        "SUPABASE_DB_URL": settings.SUPABASE_DB_URL,
        "SUPABASE_URL": settings.SUPABASE_URL,
        "SUPABASE_SECRET_KEY": settings.SUPABASE_SECRET_KEY,
        "SUPABASE_STORAGE_BUCKET": settings.SUPABASE_STORAGE_BUCKET,
    }
    missing = [k for k, v in required.items() if not v]
    if missing:
        raise ValueError(
            f"Missing required vars for PROFILE=production: {', '.join(missing)}"
        )

# Setup logging
# Observability fields (trace_id, span_id, request_id, job_id, video_id) are added
# by ObservabilityLogFilter and can be included in format if needed
logging.basicConfig(
    level=logging.DEBUG if settings.DEBUG else logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)

# Create directories (resolve relative paths from backend/ directory)
_backend_dir = Path(__file__).parent.parent.parent  # backend/
for d in [settings.UPLOAD_DIR, settings.PROCESSED_DIR, "../data/database"]:
    dir_path = (_backend_dir / d).resolve() if d.startswith("../") else Path(d)
    dir_path.mkdir(parents=True, exist_ok=True)


# Environment limits (for video validation)
def get_environment_limits() -> dict:
    """Get video processing limits - same for Docker and local."""
    return {
        "max_resolution": settings.MAX_VIDEO_RESOLUTION,
        "max_fps": settings.MAX_FPS,
        "frame_skip_ratio": settings.effective_frame_skip_ratio,
        "environment": "docker" if os.path.exists("/.dockerenv") else "local",
    }


env_limits = get_environment_limits()

logger.info(
    f"Profile: {settings.PROFILE}, Storage: {settings.storage_type}, Auth: {settings.auth_required}"
)
