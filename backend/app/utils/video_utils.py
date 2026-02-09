"""Video utilities (metadata, rotation, creation time)."""

import json
import subprocess
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional


def get_video_rotation(video_path: Path) -> int:
    """
    Get video rotation metadata using ffprobe.

    Phone videos often store rotation in metadata rather than rotating pixels.
    This function uses ffprobe to read the rotation value, which matches what
    browsers use for display. This is important because:

    - OpenCV 4.x auto-rotation interprets rotation signs differently than browsers
    - ffprobe returns the same rotation value that browsers use (e.g., -90 for
      counterclockwise rotation)
    - Using ffprobe ensures pose detection sees frames in the same orientation
      as browser display

    Callers use this to:
    - Store correct "display" dimensions (accounting for rotation)
    - Rotate frames before pose detection to match browser display

    Returns:
        Rotation in degrees (0, 90, 180, 270, -90, -180, -270), or 0 if unknown.
        Negative values indicate counterclockwise rotation (matching browser behavior).
    """
    try:
        result = subprocess.run(  # noqa: S603 - ffprobe is trusted
            [  # noqa: S607 - partial executable path is OK for system tool
                "ffprobe",
                "-v",
                "error",
                "-select_streams",
                "v:0",
                "-show_entries",
                "stream_tags=rotate:stream_side_data=rotation",
                "-of",
                "json",
                str(video_path),
            ],
            capture_output=True,
            text=True,
            timeout=10,
        )

        if result.returncode == 0:
            data = json.loads(result.stdout)
            streams = data.get("streams", [])
            if streams:
                # Check tags first (older metadata format)
                tags = streams[0].get("tags", {})
                if "rotate" in tags:
                    return int(tags["rotate"])

                # Check side_data (newer format)
                side_data = streams[0].get("side_data_list", [])
                for sd in side_data:
                    if "rotation" in sd:
                        return int(sd["rotation"])

    except (
        subprocess.TimeoutExpired,
        FileNotFoundError,
        json.JSONDecodeError,
        ValueError,
    ):
        # ffprobe not available or failed - fall back to no rotation
        pass

    return 0


def get_video_creation_time(video_path: Path) -> Optional[datetime]:
    """
    Get video creation timestamp from metadata using ffprobe.

    Extracts `creation_time` from format tags first, then stream tags.
    Returns timezone-aware datetime if found, None otherwise.
    """
    try:
        result = subprocess.run(  # noqa: S603 - ffprobe is trusted
            [  # noqa: S607 - partial executable path is OK for system tool
                "ffprobe",
                "-v",
                "error",
                "-show_entries",
                "format_tags=creation_time",
                "-of",
                "json",
                str(video_path),
            ],
            capture_output=True,
            text=True,
            timeout=10,
        )

        if result.returncode == 0:
            data = json.loads(result.stdout)
            format_tags = data.get("format", {}).get("tags", {})
            creation_time = format_tags.get("creation_time")
            if creation_time:
                parsed = datetime.fromisoformat(creation_time.replace("Z", "+00:00"))
                if parsed.tzinfo is None:
                    parsed = parsed.replace(tzinfo=timezone.utc)
                return parsed

        result = subprocess.run(  # noqa: S603 - ffprobe is trusted
            [  # noqa: S607 - partial executable path is OK for system tool
                "ffprobe",
                "-v",
                "error",
                "-select_streams",
                "v:0",
                "-show_entries",
                "stream_tags=creation_time",
                "-of",
                "json",
                str(video_path),
            ],
            capture_output=True,
            text=True,
            timeout=10,
        )

        if result.returncode == 0:
            data = json.loads(result.stdout)
            streams = data.get("streams", [])
            if streams:
                stream_tags = streams[0].get("tags", {})
                creation_time = stream_tags.get("creation_time")
                if creation_time:
                    parsed = datetime.fromisoformat(
                        creation_time.replace("Z", "+00:00")
                    )
                    if parsed.tzinfo is None:
                        parsed = parsed.replace(tzinfo=timezone.utc)
                    return parsed

    except (
        subprocess.TimeoutExpired,
        FileNotFoundError,
        json.JSONDecodeError,
        ValueError,
        AttributeError,
    ):
        pass

    return None
