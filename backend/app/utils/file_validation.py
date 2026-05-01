"""File validation utilities for video uploads."""

import os
import re
import secrets
import unicodedata
from datetime import datetime
from pathlib import Path
from typing import Optional

from typing_extensions import TypedDict

from app.core.config import env_limits, settings
from app.utils.error_handling import handle_file_error


class VideoMetadataDict(TypedDict):
    """Typed dict for video metadata extracted by ffprobe/OpenCV."""

    duration: float | None
    fps: float | None
    width: int | None
    height: int | None
    frame_count: int | None
    recorded_at: datetime | None


def _validate_magic_bytes(file_content: bytes) -> bool:
    """
    Check file content against known video format magic bytes.

    Args:
        file_content: Raw file bytes (at least first 12 bytes needed)

    Returns:
        True if magic bytes match a known video format
    """
    if len(file_content) < 12:
        return False

    # MP4/MOV: 'ftyp' at offset 4
    if file_content[4:8] == b"ftyp":
        return True
    # AVI: starts with 'RIFF'
    if file_content[0:4] == b"RIFF":
        return True
    # WebM/MKV: EBML header
    return file_content[0:4] == b"\x1a\x45\xdf\xa3"


def validate_video_file(
    filename: str,
    file_size: int,
    content_type: Optional[str] = None,
    metadata: Optional[VideoMetadataDict] = None,
    file_content: Optional[bytes] = None,
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

    if file_size > settings.effective_max_file_size:
        max_size_mb = settings.effective_max_file_size / (1024 * 1024)
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

    # Validate magic bytes (if file content provided)
    if file_content and not _validate_magic_bytes(file_content):
        raise handle_file_error(
            "unsupported_format",
            filename,
            "File content does not match a supported video format",
        )

    # Validate video metadata (optional)
    if metadata:
        # Resolution validation
        vid_width = metadata.get("width")
        vid_height = metadata.get("height")
        if vid_width and vid_height:
            max_width, max_height = env_limits["max_resolution"]
            max_dim = max(max_width, max_height)
            min_dim = min(max_width, max_height)
            if (
                max(vid_width, vid_height) > max_dim
                or min(vid_width, vid_height) > min_dim
            ):
                raise handle_file_error(
                    "resolution_too_high",
                    filename,
                    f"Maximum resolution is {env_limits['max_resolution'][0]}x{env_limits['max_resolution'][1]} ({env_limits['environment']} environment)",
                )

        # FPS validation
        vid_fps = metadata.get("fps")
        if vid_fps and vid_fps > (env_limits["max_fps"] + settings.FPS_TOLERANCE):
            raise handle_file_error(
                "fps_too_high",
                filename,
                f"Maximum frame rate is {env_limits['max_fps']}fps ({env_limits['environment']} environment)",
            )

        # Duration validation
        vid_duration = metadata.get("duration")
        if vid_duration and vid_duration > settings.effective_max_video_duration:
            raise handle_file_error(
                "duration_too_long",
                filename,
                f"Maximum duration is {settings.effective_max_video_duration} seconds",
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

    This function prevents header injection attacks by:
    - Removing all control characters (including CR/LF)
    - Using only safe ASCII characters
    - Normalizing Unicode characters
    - Providing a fallback for empty results

    Args:
        filename: Original filename

    Returns:
        Safe filename safe for use in HTTP headers
    """
    # Get just the filename part, removing any path components
    name = os.path.basename(filename or "")

    # Normalize Unicode characters
    name = unicodedata.normalize("NFKC", name)

    # Remove ALL control characters (0x00-0x1f, 0x7f), including CR/LF
    name = re.sub(r"[\x00-\x1f\x7f]", "", name)

    # Allow only safe ASCII characters: letters, numbers, dots, underscores, hyphens
    name = re.sub(r"[^A-Za-z0-9._-]", "_", name)

    # Collapse repeated dots and trim leading/trailing dots and spaces
    name = re.sub(r"\.{2,}", ".", name).strip(" .")

    # If the result is empty or just dots, generate a random name
    if not name or name == ".":
        name = f"upload_{secrets.token_hex(8)}"

    return name


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
