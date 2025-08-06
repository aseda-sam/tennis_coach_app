from pathlib import Path

from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """Application settings."""

    # Database
    DATABASE_URL: str = "sqlite:///./data/database/tennis_analysis.db"

    # File storage
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

    # API
    API_V1_STR: str = "/api"
    PROJECT_NAME: str = "Tennis Analysis API"

    # CORS
    BACKEND_CORS_ORIGINS: list[str] = [
        "http://localhost:3000",
        "http://127.0.0.1:3000"
    ]

    class Config:
        env_file = ".env"
        case_sensitive = True

# Create settings instance
settings = Settings()

def create_directories() -> None:
    """Create necessary directories if they don't exist."""
    directories = [
        Path(settings.UPLOAD_DIR),
        Path(settings.PROCESSED_DIR),
        Path("./data/database"),
        Path("./data/analysis_cache")
    ]

    for directory in directories:
        directory.mkdir(parents=True, exist_ok=True)

# Initialize directories
create_directories()
