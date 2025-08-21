"""
Test configuration utilities.
"""

import os
from contextlib import suppress
from pathlib import Path
from typing import Dict


def setup_test_environment(test_dirs: Dict[str, Path]) -> None:
    """Set up test environment with proper directory structure."""
    # Create test directories
    for dir_path in test_dirs.values():
        dir_path.mkdir(parents=True, exist_ok=True)

    # Set environment variables for test
    os.environ["ENVIRONMENT"] = "test"
    os.environ["UPLOAD_DIR"] = str(test_dirs["upload_dir"])
    os.environ["PROCESSED_DIR"] = str(test_dirs["processed_dir"])
    os.environ["ML_MODELS_DIR"] = str(test_dirs["ml_models_dir"])


def cleanup_test_environment(test_dirs: Dict[str, Path]) -> None:
    """Clean up test environment."""
    # Remove test directories
    for dir_path in test_dirs.values():
        if dir_path.exists():
            for file_path in dir_path.glob("*"):
                if file_path.is_file():
                    file_path.unlink(missing_ok=True)
            with suppress(OSError):
                # Directory not empty, that's okay
                dir_path.rmdir()


def get_test_video_path() -> Path:
    """Get path to test video file."""
    test_data_dir = Path(__file__).parent / "test_data"
    video_path = test_data_dir / "test_tennis_video.mp4"
    return video_path


def create_test_video_content() -> bytes:
    """Create minimal test video content."""
    return b"\x00\x00\x00\x20ftypmp41\x00\x00\x00\x00mp41isom\x00\x00\x00\x08free"
