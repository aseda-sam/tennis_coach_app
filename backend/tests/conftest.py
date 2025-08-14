"""
Test configuration and shared fixtures.
"""

import shutil
import tempfile
from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.core.database import Base, get_db
from app.main import app

# Test database configuration
SQLALCHEMY_DATABASE_URL = "sqlite:///./test.db"
engine = create_engine(
    SQLALCHEMY_DATABASE_URL, connect_args={"check_same_thread": False}
)
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


@pytest.fixture(scope="session")
def test_db():
    """Create test database."""
    Base.metadata.create_all(bind=engine)
    yield engine
    Base.metadata.drop_all(bind=engine)


@pytest.fixture
def db_session(test_db):
    """Create test database session."""
    session = TestingSessionLocal()
    try:
        yield session
    finally:
        session.close()


@pytest.fixture
def client(db_session):
    """Create test client with database override."""

    def override_get_db():
        try:
            yield db_session
        finally:
            pass

    app.dependency_overrides[get_db] = override_get_db
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()


@pytest.fixture
def temp_upload_dir():
    """Create temporary upload directory."""
    temp_dir = tempfile.mkdtemp()
    yield Path(temp_dir)
    shutil.rmtree(temp_dir, ignore_errors=True)


@pytest.fixture
def test_video_path():
    """Path to test video file."""
    test_data_dir = Path(__file__).parent / "test_data"
    video_path = test_data_dir / "test_tennis_video.mp4"

    if not video_path.exists():
        pytest.skip(
            "Test video file not found. Please add a test video to tests/test_data/"
        )

    return video_path


@pytest.fixture
def sample_video_content():
    """Create a minimal video file for basic API tests."""
    # This creates a very basic MP4-like file for API testing
    # Not suitable for actual video processing, but good for endpoint testing
    content = b"\x00\x00\x00\x20ftypmp41\x00\x00\x00\x00mp41isom\x00\x00\x00\x08free"
    return content


@pytest.fixture
def cleanup_test_files():
    """Cleanup fixture to remove test-generated files."""
    yield
    # Clean up any test-generated files
    test_dirs = [
        Path("../data/videos/processed"),
        Path("../data/analysis_cache"),
    ]

    for test_dir in test_dirs:
        if test_dir.exists():
            for file_path in test_dir.glob("*"):
                if file_path.is_file():
                    file_path.unlink(missing_ok=True)
