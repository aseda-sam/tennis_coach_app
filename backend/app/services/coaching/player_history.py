"""Player historical metrics — compute-on-the-fly aggregations for coaching context.

NOTE: This module lives in coaching/ because it's the only consumer today.
If other services need player metric history (e.g. trend API, session
comparison), move it to backend/app/services/player_history.py.

Queries the player's past biomechanics reports and returns summary stats
(min, max, mean, count) per metric. No stored aggregations — Postgres
handles this in milliseconds at our scale.

History is scoped by video.recorded_at (when the serve was actually played),
NOT by report.created_at (when the pipeline ran). This ensures that
uploading a 6-month-old video doesn't pollute the history of recent serves.
"""

import logging
from datetime import datetime
from typing import Any, Optional

from sqlalchemy import text
from sqlalchemy.orm import Session

from app.services.biomechanics.serve_biomechanics_service import ANALYSIS_VERSION

logger = logging.getLogger(__name__)

# Metrics to aggregate and their JSONB paths.
# Each entry: (metric_name, jsonb_phase_key, jsonb_metric_key)
_METRIC_PATHS = [
    ("knee_flexion_min_deg", "toss", "knee_flexion_min_deg"),
    ("toss_peak_height", "toss", "toss_peak_height"),
    ("toss_laterality", "toss", "toss_laterality"),
    ("toss_drop", "toss", "toss_drop"),
]


def get_player_metric_history(
    db: Session,
    player_id: int,
    *,
    before: Optional[datetime] = None,
    exclude_serve_window_id: Optional[int] = None,
) -> dict[str, dict[str, Any]]:
    """Compute per-metric aggregations from a player's historical reports.

    Args:
        before: Only include serves from videos recorded before this
            timestamp. Use the current serve's video.recorded_at to get
            a backwards-looking history. If None, includes all serves.
        exclude_serve_window_id: Exclude this serve window from the stats
            (to avoid self-comparison).

    Returns a dict keyed by metric_name, each containing:
        min, max, mean, count.

    Only uses the latest report per serve window (highest report id)
    to avoid counting re-computations multiple times.
    """
    results: dict[str, dict[str, Any]] = {}

    for metric_name, phase_key, metric_key in _METRIC_PATHS:
        query = text("""
            WITH latest_per_window AS (
                SELECT DISTINCT ON (sbr.serve_window_id)
                    sbr.serve_window_id,
                    (sbr.metrics -> :phase_key ->> :metric_key)::float AS val,
                    v.recorded_at
                FROM serve_biomechanics_reports sbr
                JOIN serve_windows sw ON sw.id = sbr.serve_window_id
                JOIN videos v ON v.id = sw.video_id
                WHERE sbr.player_id = :player_id
                  AND sbr.analysis_version = :version
                  AND sbr.metrics -> :phase_key ->> :metric_key IS NOT NULL
                  AND (:before_ts IS NULL OR v.recorded_at < :before_ts)
                ORDER BY sbr.serve_window_id, sbr.id DESC
            )
            SELECT
                COUNT(*) AS cnt,
                ROUND(MIN(val)::numeric, 1) AS min_val,
                ROUND(MAX(val)::numeric, 1) AS max_val,
                ROUND(AVG(val)::numeric, 1) AS mean_val
            FROM latest_per_window
            WHERE (:exclude_sw IS NULL OR serve_window_id != :exclude_sw)
        """)

        row = db.execute(
            query,
            {
                "player_id": player_id,
                "phase_key": phase_key,
                "metric_key": metric_key,
                "version": ANALYSIS_VERSION,
                "before_ts": before,
                "exclude_sw": exclude_serve_window_id,
            },
        ).fetchone()

        if row and row.cnt > 0:
            results[metric_name] = {
                "count": row.cnt,
                "min": float(row.min_val),
                "max": float(row.max_val),
                "mean": float(row.mean_val),
            }

    return results
