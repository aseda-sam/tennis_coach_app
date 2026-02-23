"""Tests for video metadata utility helpers."""

import json
import logging
import subprocess
from datetime import datetime, timezone
from pathlib import Path
from unittest.mock import patch

from app.utils.video_utils import get_video_creation_time


def test_get_video_creation_time_returns_none_when_ffprobe_missing(caplog) -> None:
    """Missing ffprobe should not raise and should fall back gracefully."""
    with (
        patch("app.utils.video_utils.subprocess.run", side_effect=FileNotFoundError),
        caplog.at_level(logging.WARNING),
    ):
        result = get_video_creation_time(Path("test.mp4"))

    assert result is None
    assert "ffprobe is unavailable; skipping creation_time extraction" in caplog.text


def test_get_video_creation_time_reads_format_tag() -> None:
    """Creation time is parsed from format tags when present."""
    payload = {"format": {"tags": {"creation_time": "2026-01-01T12:00:00Z"}}}
    completed = subprocess.CompletedProcess(
        args=["ffprobe"], returncode=0, stdout=json.dumps(payload), stderr=""
    )

    with patch("app.utils.video_utils.subprocess.run", return_value=completed):
        result = get_video_creation_time(Path("test.mp4"))

    assert result == datetime(2026, 1, 1, 12, 0, 0, tzinfo=timezone.utc)
