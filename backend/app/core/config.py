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
    STORAGE_TYPE: Optional[str] = None  # Auto-detected: "local" or "supabase"
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
    DOCKER_MAX_VIDEO_RESOLUTION: tuple[int, int] = (1920, 1080)  # 1080p for Docker
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

    class Config:
        env_file = ".env"
        case_sensitive = True


# Create settings instance
settings = Settings()


# Profile-based configuration initialization
def initialize_profile_config() -> None:
    """Initialize configuration based on PROFILE setting."""
    profile = settings.PROFILE

    # Determine storage type based on profile
    if settings.STORAGE_TYPE is None:
        settings.STORAGE_TYPE = "local" if profile == "local" else "supabase"
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
            "frame_skip_ratio": settings.DOCKER_FRAME_SKIP_RATIO,
            "environment": "docker",
        }
    else:
        return {
            "max_resolution": settings.MAX_VIDEO_RESOLUTION,
            "max_fps": settings.MAX_FPS,
            "frame_skip_ratio": settings.FRAME_SKIP_RATIO,
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
