from pathlib import Path
from typing import Optional

from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """Application settings."""

    # Environment
    ENVIRONMENT: str = "development"  # development, production

    # API Configuration
    API_HOST: str = "0.0.0.0"
    API_PORT: int = 8000
    DEBUG: bool = False

    # Database - Environment-based configuration
    # DATABASE_URL: str = "sqlite:///../data/database/tennis_coach.db"
    DATABASE_URL: Optional[str] = None

    # Supabase - Production database
    SUPABASE_URL: Optional[str] = None
    SUPABASE_KEY: Optional[str] = None
    SUPABASE_DB_URL: Optional[str] = None  # Direct connection to Supabase database

    # File storage - Environment-based configuration
    STORAGE_TYPE: str = "local"  # local, cloudinary, s3
    UPLOAD_DIR: str = "../data/videos/raw"
    PROCESSED_DIR: str = "../data/videos/processed"
    MAX_FILE_SIZE: int = 104857600  # 100MB
    SUPPORTED_FORMATS: list[str] = [".mp4", ".mov", ".avi"]

    # Computer Vision
    YOLO_MODEL_PATH: str = "yolov8n.pt"
    CONFIDENCE_THRESHOLD: float = 0.5
    BALL_CONFIDENCE_THRESHOLD: float = 0.7

    # Processing
    MAX_VIDEO_DURATION: int = 300  # 5 minutes
    FRAME_SKIP_RATIO: int = 2  # Process every nth frame
    MAX_VIDEO_RESOLUTION: tuple[int, int] = (3840, 2160)  # 4K support (local)
    MAX_FPS: int = 60  # 60fps support (local)

    # Docker-specific limits (will be overridden in Docker)
    DOCKER_MAX_VIDEO_RESOLUTION: tuple[int, int] = (1920, 1080)  # 1080p for Docker
    DOCKER_MAX_FPS: int = 60  # 60fps for Docker
    DOCKER_FRAME_SKIP_RATIO: int = 3  # Process every 3rd frame in Docker

    # API
    API_V1_STR: str = "/v0"
    PROJECT_NAME: str = "Tennis Coach API"

    # CORS
    BACKEND_CORS_ORIGINS: list[str] = ["http://localhost:3000", "http://127.0.0.1:3000"]

    @property
    def database_url(self) -> str:
        """Get database URL based on environment."""
        if self.is_production and self.SUPABASE_DB_URL:
            return self.SUPABASE_DB_URL
        if self.DATABASE_URL:
            return self.DATABASE_URL
        else:
            return "sqlite:///../data/database/tennis_coach.db"

    @property
    def is_production(self) -> bool:
        """Check if the environment is production."""
        return self.ENVIRONMENT == "production"

    class Config:
        env_file = ".env"
        case_sensitive = True


# Create settings instance
settings = Settings()


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
