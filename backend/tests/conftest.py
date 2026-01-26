"""
Test configuration and shared fixtures.

TDD Principle: Tests use PROFILE-based configuration (public API), not internal fields.
This ensures tests define contracts that remain stable when internals change.
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

from app.core.config import settings
from app.core.database import Base, get_db
from app.dependencies.auth import get_current_user
from app.main import app


def skip_if_supabase_storage() -> None:
    """Skip test if using Supabase storage (requires local file access)."""
    if settings.STORAGE_TYPE == "supabase":
        pytest.skip("Test requires local storage - skipped for Supabase")


@pytest.fixture(autouse=True)
def ensure_local_profile() -> Generator[None, None, None]:
    """
    Ensure tests run with PROFILE=local by default.

    This fixture runs automatically for all tests to ensure consistent test environment.
    Tests that need production profile should explicitly patch PROFILE.
    """
    # Save original PROFILE
    original_profile = os.environ.get("PROFILE")

    # Set PROFILE=local for tests (unless already set)
    if "PROFILE" not in os.environ:
        os.environ["PROFILE"] = "local"

    # Reload settings to pick up PROFILE change
    # Note: Settings are loaded at module import, so we patch the instance
    with patch.object(settings, "PROFILE", "local"):
        yield

    # Restore original PROFILE
    if original_profile is not None:
        os.environ["PROFILE"] = original_profile
    elif "PROFILE" in os.environ:
        del os.environ["PROFILE"]


@pytest.fixture
def local_profile() -> Generator[None, None, None]:
    """
    Explicitly set PROFILE=local for a test.

    Use this when you need to ensure local profile in a specific test.
    """
    with patch.object(settings, "PROFILE", "local"):
        yield


@pytest.fixture
def production_profile() -> Generator[None, None, None]:
    """
    Set PROFILE=production for a test (requires Supabase config).

    Use this when testing production-specific behavior.
    Note: You'll need to patch SUPABASE_* settings as well.
    """
    with patch.object(settings, "PROFILE", "production"):
        yield


# Test database configuration
SQLALCHEMY_DATABASE_URL = "sqlite:///./tests/test.db"
engine = create_engine(
    SQLALCHEMY_DATABASE_URL, connect_args={"check_same_thread": False}
)
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


@pytest.fixture(scope="function")
def test_db() -> Generator:
    """Create test database."""
    # Create all tables
    Base.metadata.create_all(bind=engine)
    yield engine
    # Clean up after each test
    Base.metadata.drop_all(bind=engine)


@pytest.fixture
def db_session(test_db: Generator) -> Generator:
    """Create test database session."""
    session = TestingSessionLocal()
    try:
        yield session
    finally:
        session.rollback()
        session.close()


@pytest.fixture
def test_user_id() -> str:
    """Get test user ID for creating test data."""
    return "00000000-0000-0000-0000-000000000000"


@pytest.fixture
def client(db_session: Generator) -> Generator[TestClient, None, None]:
    """
    Create test client with database override and mock auth.

    TDD Contract: This fixture provides a TestClient that:
    - Uses test database (isolated per test)
    - Has mock authentication (test_user_id)
    - Runs with PROFILE=local (via ensure_local_profile fixture)
    """

    def override_get_db() -> Generator:
        try:
            yield db_session
        finally:
            pass

    async def mock_get_current_user() -> dict:
        """Mock authentication for tests - returns test_user_id."""
        return {
            "id": "00000000-0000-0000-0000-000000000000",
            "email": "test@example.com",
            "user_metadata": {},
        }

    app.dependency_overrides[get_db] = override_get_db
    app.dependency_overrides[get_current_user] = mock_get_current_user

    # Ensure PROFILE=local for this test client
    with patch.object(settings, "PROFILE", "local"), TestClient(app) as test_client:
        yield test_client

    app.dependency_overrides.clear()


@pytest.fixture
def temp_upload_dir() -> Generator[Path, None, None]:
    """Create temporary upload directory."""
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
def cleanup_test_files() -> Generator[None, None, None]:
    """Cleanup fixture to remove test-generated files."""
    yield
    # Clean up any test-generated files
    test_dirs = [
        Path("../data/videos/processed"),
        Path("../data/analysis_cache"),
    ]

    for test_dir in test_dirs:
        if test_dir.exists():
            for file_path in test_dir.glob("test_*"):
                if file_path.is_file():
                    file_path.unlink(missing_ok=True)
