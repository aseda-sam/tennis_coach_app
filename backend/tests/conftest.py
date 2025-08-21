"""
Test configuration and shared fixtures.
"""

import os
import shutil
import tempfile
from pathlib import Path
from typing import Generator
from unittest.mock import patch

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.core.database import Base, get_db
from app.main import app

# Test database configuration - use temporary file for CI compatibility
SQLALCHEMY_DATABASE_URL = "sqlite:///:memory:"  # Use in-memory database for tests
engine = create_engine(
    SQLALCHEMY_DATABASE_URL, connect_args={"check_same_thread": False}
)
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


@pytest.fixture(scope="session")
def test_db() -> Generator:
    """Create test database."""
    Base.metadata.create_all(bind=engine)
    yield engine
    Base.metadata.drop_all(bind=engine)


@pytest.fixture
def db_session(test_db: Generator) -> Generator:
    """Create test database session with clean state for each test."""
    # Drop all tables and recreate them for each test to ensure isolation
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)

    session = TestingSessionLocal()
    try:
        yield session
    finally:
        session.close()


@pytest.fixture
def temp_test_dirs() -> Generator[dict[str, Path], None, None]:
    """Create temporary test directories for file storage."""
    # Create temporary base directory
    temp_base = tempfile.mkdtemp(prefix="tennis_coach_test_")
    temp_base_path = Path(temp_base)

    # Create test-specific subdirectories
    test_dirs = {
        "upload_dir": temp_base_path / "videos" / "raw",
        "processed_dir": temp_base_path / "videos" / "processed",
        "analysis_cache_dir": temp_base_path / "analysis_cache",
        "ml_models_dir": temp_base_path / "ml_models",
    }

    # Create all directories
    for dir_path in test_dirs.values():
        dir_path.mkdir(parents=True, exist_ok=True)

    yield test_dirs

    # Cleanup: remove entire temporary directory
    shutil.rmtree(temp_base_path, ignore_errors=True)


@pytest.fixture
def test_config_override(
    temp_test_dirs: dict[str, Path],
) -> Generator[None, None, None]:
    """Override application configuration to use test directories."""
    # Store original environment variables
    original_env = {}

    # Set test-specific environment variables
    test_env_vars = {
        "UPLOAD_DIR": str(temp_test_dirs["upload_dir"]),
        "PROCESSED_DIR": str(temp_test_dirs["processed_dir"]),
        "ML_MODELS_DIR": str(temp_test_dirs["ml_models_dir"]),
        "ENVIRONMENT": "test",  # Mark as test environment
    }

    # Backup and set environment variables
    for key, value in test_env_vars.items():
        original_env[key] = os.environ.get(key)
        os.environ[key] = value

    # Patch the settings to use test directories
    with patch(
        "app.core.config.settings.UPLOAD_DIR", str(temp_test_dirs["upload_dir"])
    ), patch(
        "app.core.config.settings.PROCESSED_DIR", str(temp_test_dirs["processed_dir"])
    ), patch(
        "app.core.config.settings.ML_MODELS_DIR", str(temp_test_dirs["ml_models_dir"])
    ), patch("app.core.config.settings.ENVIRONMENT", "test"):
        yield

    # Restore original environment variables
    for key, value in original_env.items():
        if value is not None:
            os.environ[key] = value
        else:
            os.environ.pop(key, None)


@pytest.fixture
def client(
    db_session: Generator, test_config_override: Generator[None, None, None]
) -> Generator[TestClient, None, None]:
    """Create test client with database override and test configuration."""

    def override_get_db() -> Generator:
        try:
            yield db_session
        finally:
            pass

    app.dependency_overrides[get_db] = override_get_db
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()


@pytest.fixture
def temp_upload_dir() -> Generator[Path, None, None]:
    """Create temporary upload directory (legacy fixture for backward compatibility)."""
    temp_dir = tempfile.mkdtemp()
    yield Path(temp_dir)
    shutil.rmtree(temp_dir, ignore_errors=True)


@pytest.fixture
def test_video_path() -> Path:
    """Path to test video file."""
    test_data_dir = Path(__file__).parent / "test_data"
    video_path = test_data_dir / "test_tennis_video.mp4"

    if not video_path.exists():
        pytest.skip(
            "Test video file not found. Please add a test video to tests/test_data/"
        )

    return video_path


@pytest.fixture
def sample_video_content() -> bytes:
    """Create a minimal video file for basic API tests."""
    # This creates a very basic MP4-like file for API testing
    # Not suitable for actual video processing, but good for endpoint testing
    content = b"\x00\x00\x00\x20ftypmp41\x00\x00\x00\x00mp41isom\x00\x00\x00\x08free"
    return content


@pytest.fixture
def cleanup_test_files(temp_test_dirs: dict[str, Path]) -> Generator[None, None, None]:
    """Cleanup fixture to remove test-generated files from test directories only."""
    yield
    # Clean up any test-generated files from test directories only
    for dir_path in [
        temp_test_dirs["processed_dir"],
        temp_test_dirs["analysis_cache_dir"],
    ]:
        if dir_path.exists():
            for file_path in dir_path.glob("*"):
                if file_path.is_file():
                    file_path.unlink(missing_ok=True)
