"""Test configuration and shared fixtures."""

import os
import shutil
from pathlib import Path
from typing import Generator

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.core.database import Base, get_db
from app.main import app

# Test database configuration
SQLALCHEMY_DATABASE_URL = "sqlite:///./tests/test.db"
engine = create_engine(
    SQLALCHEMY_DATABASE_URL, connect_args={"check_same_thread": False}
)
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


@pytest.fixture(scope="session")
def test_db() -> Generator:
    """Create test database."""
    Base.metadata.create_all(bind=engine)
    yield
    Base.metadata.drop_all(bind=engine)


@pytest.fixture
def db_session(test_db: Generator) -> Generator:
    """Create a new database session for a test."""
    # Drop and recreate tables for each test to ensure clean state
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)

    session = TestingSessionLocal()
    try:
        yield session
    finally:
        session.close()


@pytest.fixture
def client(db_session: Generator) -> Generator[TestClient, None, None]:
    """Create a test client with database override."""
    def override_get_db() -> Generator:
        try:
            yield db_session
        finally:
            pass

    app.dependency_overrides[get_db] = override_get_db

    with TestClient(app) as test_client:
        yield test_client

    app.dependency_overrides.clear()


@pytest.fixture(autouse=True)
def cleanup_test_files() -> Generator:
    """Clean up any files starting with test_ after each test."""
    yield
    
    # Clean up any test_ files in the data directories
    base_data_dir = Path("../data")
    for main_dir in [base_data_dir / "videos" / "raw",
                     base_data_dir / "videos" / "processed",
                     base_data_dir / "analysis_cache"]:
        if main_dir.exists():
            for file_path in main_dir.glob("test_*"):
                if file_path.is_file():
                    file_path.unlink(missing_ok=True)
