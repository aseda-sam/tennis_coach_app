"""JSONL logger for LLM calls.

Every LLM interaction gets appended here as a single JSON line.
This file IS your eval dataset — you'll load these pairs later to build
test fixtures and run evals against them.

Why JSONL and not a database?
- Human-readable (cat the file, pipe to jq)
- Append-only (no schema migrations)
- Loadable into pandas in one line
- Good enough until you have production traffic
"""

import json
import logging
import time
from pathlib import Path
from typing import Any, Optional

from app.core.config import settings

logger = logging.getLogger(__name__)

_DEFAULT_LOG_DIR = Path("../data/llm_logs")


def get_log_path(log_dir: Optional[Path] = None) -> Path:
    """Get the JSONL log file path, creating the directory if needed."""
    if log_dir:
        directory = log_dir
    elif settings.LLM_LOG_DIR:
        directory = Path(settings.LLM_LOG_DIR)
    else:
        directory = _DEFAULT_LOG_DIR
    directory.mkdir(parents=True, exist_ok=True)
    return directory / "coaching_calls.jsonl"


def log_llm_call(
    *,
    input_data: dict[str, Any],
    output_text: str,
    model: str,
    latency_ms: float,
    input_tokens: int,
    output_tokens: int,
    serve_window_id: Optional[int] = None,
    error: Optional[str] = None,
    log_dir: Optional[Path] = None,
) -> None:
    """Append one LLM call record to the JSONL log.

    Each line is a self-contained JSON object with everything needed
    to reproduce and evaluate the call.
    """
    record = {
        "timestamp": time.time(),
        "model": model,
        "serve_window_id": serve_window_id,
        "input": input_data,
        "output": output_text,
        "error": error,
        "latency_ms": round(latency_ms, 1),
        "input_tokens": input_tokens,
        "output_tokens": output_tokens,
    }

    log_path = get_log_path(log_dir)
    try:
        with open(log_path, "a") as f:
            f.write(json.dumps(record) + "\n")
    except OSError:
        logger.exception("Failed to write LLM log to %s", log_path)
