import logging
from pathlib import Path
from typing import Optional

from pydantic_settings import BaseSettings

logger = logging.getLogger(__name__)


class Settings(BaseSettings):
    """Application settings."""

    # Profile-based configuration
    PROFILE: str = "local"  # local or production

    # API Configuration
    API_HOST: str = "0.0.0.0"
    API_PORT: int = 8000
    DEBUG: bool = False  # If True: enables auto-reload and DEBUG logging

    # Database - Environment-based configuration
    # DATABASE_URL: str = "sqlite:///../data/database/tennis_coach.db"
    DATABASE_URL: Optional[str] = None

    # Supabase - Production database
    SUPABASE_SECRET_KEY: Optional[str] = None
    SUPABASE_DB_URL: Optional[str] = None  # Direct connection to Supabase database

    # Supabase Storage - Production file storage
    SUPABASE_URL: Optional[str] = (
        None  # Supabase project URL (used for storage, auth, etc.)
    )
    SUPABASE_STORAGE_BUCKET: Optional[str] = None  # Storage bucket name

    # File storage - Environment-based configuration
    # Note: STORAGE_TYPE is auto-detected based on SUPABASE_DB_URL
    # If SUPABASE_DB_URL is set, STORAGE_TYPE is automatically set to "supabase"
    # This ensures consistency: Supabase DB → Supabase Storage
    _STORAGE_TYPE: Optional[str] = None  # Private field for explicit env var override
    UPLOAD_DIR: str = "../data/videos/raw"
    PROCESSED_DIR: str = "../data/videos/processed"
    MAX_FILE_SIZE: int = 104857600  # 100MB
    SUPPORTED_FORMATS: list[str] = [".mp4", ".mov", ".avi"]

    # Computer Vision
    ML_MODELS_DIR: str = "ml_models"
    YOLO_MODELS: dict[str, str] = {
        "nano": "ml_models/yolov8n.pt",
        "small": "ml_models/yolov8s.pt",
    }
    YOLO_DEFAULT_MODEL: str = (
        "nano"  # Default model to use when quality-based selection fails
    )
    CONFIDENCE_THRESHOLD: float = 0.5
    BALL_CONFIDENCE_THRESHOLD: float = 0.7

    # Pose Detection Configuration
    POSE_DETECTION_CONFIDENCE: float = (
        0.5  # Minimum detection confidence for pose estimation
    )
    POSE_TRACKING_CONFIDENCE: float = (
        0.5  # Minimum tracking confidence for pose estimation
    )
    POSE_OVERALL_CONFIDENCE: float = (
        0.8  # Overall confidence score for pose detection results
    )

    # Ball Contact Detection
    BALL_CONTACT_TIMESTAMP_TOLERANCE: float = (
        0.1  # Tolerance in seconds for duplicate contact detection
    )

    # Processing
    MAX_VIDEO_DURATION: int = 300  # 5 minutes
    FRAME_SKIP_RATIO: int = 1  # Process every frame (no skipping by default)
    MAX_VIDEO_RESOLUTION: tuple[int, int] = (3840, 2160)  # 4K support (local)
    MAX_FPS: int = 60  # 60fps support (local)

    # Docker-specific limits (will be overridden in Docker)
    DOCKER_MAX_VIDEO_RESOLUTION: tuple[int, int] = (3840, 2160)  # 1080p for Docker
    DOCKER_MAX_FPS: int = 60  # 60fps for Docker
    DOCKER_FRAME_SKIP_RATIO: int = (
        1  # Process every frame in Docker (no skipping by default)
    )

    # API
    API_V1_STR: str = "/v0"
    PROJECT_NAME: str = "Tennis Coach API"

    # CORS
    BACKEND_CORS_ORIGINS: list[str] = [
        "http://localhost:3000",
        "http://127.0.0.1:3000",
        "https://aseda-sam.github.io",
    ]

    # Authentication
    REQUIRE_AUTH: bool = True  # Set to False to skip auth in development

    # Redis / RQ Configuration
    REDIS_URL: Optional[str] = (
        None  # Redis connection URL for RQ (defaults to localhost in redis_config.py)
    )
    ENVIRONMENT: Optional[str] = (
        None  # Environment: development or production (defaults to development)
    )
    SERVICE_TYPE: Optional[str] = (
        None  # Service type: 'api' or 'worker' (defaults to 'api' in main.py)
    )

    # Rate Limiting Configuration (currently disabled - can be re-enabled in the future)
    # Auth rate limits (per IP)
    # RATE_LIMIT_AUTH_PRODUCTION: str = "5/minute"  # Production auth attempts
    # RATE_LIMIT_AUTH_OTHER: str = "10/minute"  # Other profiles (staging, etc.)
    # General API rate limits (per IP)
    # RATE_LIMIT_DEFAULT_LOCAL: str = "1000/hour"  # Local dev default
    # RATE_LIMIT_DEFAULT_PRODUCTION: str = "100/hour"  # Production default
    # Expensive operations rate limits (per IP)
    # RATE_LIMIT_VIDEO_UPLOAD: str = "10/hour"  # Video uploads (large files)
    # RATE_LIMIT_ANALYSIS: str = "20/hour"  # Analysis requests (CPU-intensive)
    # Per-user upload limits (database-based)
    MAX_VIDEO_UPLOADS_PER_DAY: int = 3  # Maximum videos per user per day (production)

    # Demo video constants
    DEMO_USER_ID: str = "00000000-0000-0000-0000-000000000001"
    DEMO_VIDEO_FILENAME: str = "demo_tennis_serve.mp4"

    # Privacy Protection: Only these user IDs can have their videos promoted to demo
    # CRITICAL: Never add real user IDs here - only admin/test/developer accounts
    # Note: In local dev mode (PROFILE=local), the promotion script allows any video
    # since there's no real user privacy concern in local development
    ALLOWED_DEMO_SOURCE_USERS: list[str] = [
        "00000000-0000-0000-0000-000000000001",  # DEMO_USER_ID - Can re-promote existing demo
        "00000000-0000-0000-0000-000000000000",  # Local dev mock user ID (for convenience)
        # Add your admin/test user IDs here, e.g.:
        # "your-admin-user-id-here",
    ]

    @property
    def database_url(self) -> str:
        """Get database URL based on profile."""
        # Profile-based database selection
        if self.PROFILE == "local":
            # Local profile: Use DATABASE_URL if set, else SQLite
            if self.DATABASE_URL:
                return self.DATABASE_URL
            return "sqlite:///../data/database/tennis_coach.db"
        else:
            # production: Require SUPABASE_DB_URL
            if not self.SUPABASE_DB_URL:
                raise ValueError(
                    f"SUPABASE_DB_URL required when PROFILE={self.PROFILE}"
                )
            return self.SUPABASE_DB_URL

    @property
    def is_production(self) -> bool:
        """Check if the profile is production."""
        return self.PROFILE == "production"

    @property
    def auth_required(self) -> bool:
        """Check if authentication is required based on profile."""
        return self.PROFILE != "local"

    @property
    def effective_max_video_duration(self) -> int:
        """Get max video duration based on profile."""
        if self.is_production:
            return 60  # 1 minute for production (memory constraints)
        return self.MAX_VIDEO_DURATION

    @property
    def effective_max_file_size(self) -> int:
        """Get max file size based on profile."""
        if self.is_production:
            return 20971520  # 20MB for production (memory constraints)
        return self.MAX_FILE_SIZE

    @property
    def effective_frame_skip_ratio(self) -> int:
        """Get frame skip ratio based on profile."""
        # Process all frames by default (no skipping)
        # Frame skip ratio of 1 means process every frame
        return self.FRAME_SKIP_RATIO

    @property
    def STORAGE_TYPE(self) -> str:  # noqa: N802 - Property name matches existing API
        """Get storage type, auto-detected if not explicitly set.

        Returns:
            "local" or "supabase" based on configuration

        Logic:
            - If _STORAGE_TYPE is explicitly set (via env var), use that
            - Otherwise, auto-detect:
              - If PROFILE == "local" → "local" (ignores Supabase vars)
              - Else if SUPABASE_DB_URL is set → "supabase"
              - Else → "supabase"
        """
        # If explicitly set via env var, use that
        if self._STORAGE_TYPE is not None:
            return self._STORAGE_TYPE

        # Profile-based detection takes precedence
        # When PROFILE=local, always use local storage (ignores Supabase vars)
        if self.PROFILE == "local":
            return "local"

        # For non-local profiles, auto-detect based on SUPABASE_DB_URL
        if self.SUPABASE_DB_URL:
            return "supabase"

        # Default fallback
        return "supabase"

    class Config:
        env_file = ".env"
        case_sensitive = True


# Create settings instance
settings = Settings()


# Profile-based configuration initialization
def initialize_profile_config() -> None:
    """Initialize configuration based on PROFILE setting."""
    profile = settings.PROFILE

    # Log storage type (now computed via property)
    logger.info(f"Profile '{profile}': Using {settings.STORAGE_TYPE} storage")

    # Determine database based on profile
    if profile == "local":
        if settings.DATABASE_URL:
            logger.info(f"Profile '{profile}': Using DATABASE_URL for local Postgres")
        else:
            logger.info(f"Profile '{profile}': Using SQLite (default)")
    else:
        if not settings.SUPABASE_DB_URL:
            raise ValueError(f"SUPABASE_DB_URL required when PROFILE={profile}")
        logger.info(f"Profile '{profile}': Using Supabase database")

    # Validate Supabase configuration when using supabase storage
    if settings.STORAGE_TYPE == "supabase":
        required_vars = {
            "SUPABASE_URL": settings.SUPABASE_URL,
            "SUPABASE_SECRET_KEY": settings.SUPABASE_SECRET_KEY,
            "SUPABASE_STORAGE_BUCKET": settings.SUPABASE_STORAGE_BUCKET,
        }
        for var_name, var_value in required_vars.items():
            if not var_value:
                raise ValueError(f"{var_name} required when STORAGE_TYPE=supabase")

    # Log auth requirement
    auth_required = profile != "local"
    logger.info(
        f"Profile '{profile}': Auth {'required' if auth_required else 'disabled'}"
    )


# Initialize profile-based configuration
initialize_profile_config()


# Configure logging based on DEBUG setting
def configure_logging() -> None:
    """Configure logging level based on DEBUG setting."""
    log_level = logging.DEBUG if settings.DEBUG else logging.INFO
    logging.basicConfig(
        level=log_level,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )
    logger.info(f"Logging configured: level={logging.getLevelName(log_level)}")


# Configure logging
configure_logging()


# Environment detection and dynamic configuration
def get_environment_limits() -> dict:
    """Get video processing limits based on environment."""
    import os

    # Check if running in Docker
    if os.path.exists("/.dockerenv"):
        return {
            "max_resolution": settings.DOCKER_MAX_VIDEO_RESOLUTION,
            "max_fps": settings.DOCKER_MAX_FPS,
            "frame_skip_ratio": settings.effective_frame_skip_ratio,
            "environment": "docker",
        }
    else:
        return {
            "max_resolution": settings.MAX_VIDEO_RESOLUTION,
            "max_fps": settings.MAX_FPS,
            "frame_skip_ratio": settings.effective_frame_skip_ratio,
            "environment": "local",
        }


# Get current environment limits
env_limits = get_environment_limits()


def create_directories() -> None:
    """Create necessary directories if they don't exist."""
    directories = [
        Path(settings.UPLOAD_DIR),
        Path(settings.PROCESSED_DIR),
        Path("../data/database"),
        Path("../data/analysis_cache"),
    ]

    for directory in directories:
        directory.mkdir(parents=True, exist_ok=True)


# Initialize directories
create_directories()
