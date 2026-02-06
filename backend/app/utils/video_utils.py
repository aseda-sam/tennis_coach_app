"""Video utilities (metadata, rotation)."""

import json
import subprocess
from pathlib import Path


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
