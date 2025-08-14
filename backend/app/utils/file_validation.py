"""File validation utilities for video uploads."""

from pathlib import Path
from typing import Optional

from app.core.config import settings
from app.utils.error_handling import handle_file_error


def validate_video_file(
    filename: str, file_size: int, content_type: Optional[str] = None
) -> None:
    """
    Validate video file for upload.

    Args:
        filename: Name of the file
        file_size: Size of the file in bytes
        content_type: MIME type of the file

    Raises:
        APIError: If validation fails
    """

    # Validate filename
    if not filename or not filename.strip():
        raise handle_file_error("invalid", "", "Filename cannot be empty")

    # Validate file extension
    file_ext = Path(filename).suffix.lower()
    if file_ext not in settings.SUPPORTED_FORMATS:
        raise handle_file_error(
            "unsupported_format",
            filename,
            f"Supported formats: {', '.join(settings.SUPPORTED_FORMATS)}",
        )

    # Validate file size
    if file_size <= 0:
        raise handle_file_error("invalid", filename, "File size must be positive")

    if file_size > settings.MAX_FILE_SIZE:
        max_size_mb = settings.MAX_FILE_SIZE / (1024 * 1024)
        raise handle_file_error(
            "too_large", filename, f"Maximum file size is {max_size_mb:.1f}MB"
        )

    # Validate content type (optional)
    if content_type:
        valid_content_types = {
            "video/mp4",
            "video/quicktime",
            "video/x-msvideo",
            "video/x-ms-wmv",
            "video/x-matroska",
        }

        if content_type not in valid_content_types:
            raise handle_file_error(
                "unsupported_format",
                filename,
                f"Content type {content_type} not supported",
            )


def validate_file_exists(file_path: Path, filename: str) -> None:
    """
    Validate that a file exists on disk.

    Args:
        file_path: Path to the file
        filename: Name of the file for error messages

    Raises:
        APIError: If file doesn't exist
    """

    if not file_path.exists():
        raise handle_file_error("not_found", filename, "File not found on disk")

    if not file_path.is_file():
        raise handle_file_error("invalid", filename, "Path is not a file")


def get_safe_filename(filename: str) -> str:
    """
    Get a safe filename by removing potentially dangerous characters.

    Args:
        filename: Original filename

    Returns:
        Safe filename
    """

    # Remove or replace dangerous characters
    dangerous_chars = ["/", "\\", ":", "*", "?", '"', "<", ">", "|"]
    safe_filename = filename

    for char in dangerous_chars:
        safe_filename = safe_filename.replace(char, "_")

    # Remove leading/trailing whitespace and dots
    safe_filename = safe_filename.strip(". ")

    return safe_filename


def ensure_unique_filename(filename: str, directory: Path) -> str:
    """
    Ensure filename is unique in the given directory.

    Args:
        filename: Original filename
        directory: Directory to check for uniqueness

    Returns:
        Unique filename
    """

    if not directory.exists():
        return filename

    base_name = Path(filename).stem
    extension = Path(filename).suffix
    counter = 1

    unique_filename = filename

    while (directory / unique_filename).exists():
        unique_filename = f"{base_name}_{counter}{extension}"
        counter += 1

    return unique_filename


def get_file_size_mb(file_size_bytes: int) -> float:
    """
    Convert file size from bytes to megabytes.

    Args:
        file_size_bytes: File size in bytes

    Returns:
        File size in megabytes
    """

    return file_size_bytes / (1024 * 1024)


def format_file_size(file_size_bytes: int) -> str:
    """
    Format file size in human-readable format.

    Args:
        file_size_bytes: File size in bytes

    Returns:
        Formatted file size string
    """

    if file_size_bytes < 1024:
        return f"{file_size_bytes} B"
    elif file_size_bytes < 1024 * 1024:
        return f"{file_size_bytes / 1024:.1f} KB"
    elif file_size_bytes < 1024 * 1024 * 1024:
        return f"{file_size_bytes / (1024 * 1024):.1f} MB"
    else:
        return f"{file_size_bytes / (1024 * 1024 * 1024):.1f} GB"
