#!/usr/bin/env python3
"""Test the coaching feedback service against a real biomechanics report.

Usage:
    # Start Docker first: docker compose up -d postgres
    cd backend
    python scripts/test_coaching_feedback.py

    # Optionally specify a serve window ID:
    python scripts/test_coaching_feedback.py --serve-window-id 42
"""

import argparse
import json
import sys
from pathlib import Path
from typing import Any, Optional

# Add backend to path
backend_dir = Path(__file__).parent.parent
sys.path.insert(0, str(backend_dir))

from sqlalchemy.orm import Session  # noqa: E402

from app.api.routes.serve_biomechanics import (  # noqa: E402
    MOMENT_LABEL_MAP,
    PHASE_LABEL_MAP,
)
from app.core.database import SessionLocal  # noqa: E402
from app.models.serve_biomechanics_report import ServeBiomechanicsReport  # noqa: E402
from app.models.serve_window import ServeWindow  # noqa: E402
from app.models.video import Video  # noqa: E402
from app.services.biomechanics.metrics import metrics_to_flat_list  # noqa: E402
from app.services.coaching.coaching_service import (  # noqa: E402
    generate_coaching_feedback,
)
from app.services.coaching.player_history import get_player_metric_history  # noqa: E402


def get_latest_report(
    db: Session,
    serve_window_id: Optional[int] = None,
) -> ServeBiomechanicsReport:
    """Get the most recent biomechanics report (latest analysis version only)."""
    from app.services.biomechanics.serve_biomechanics_service import (
        ANALYSIS_VERSION,
    )

    query = db.query(ServeBiomechanicsReport).filter(
        ServeBiomechanicsReport.analysis_version == ANALYSIS_VERSION
    )
    if serve_window_id:
        query = query.filter(ServeBiomechanicsReport.serve_window_id == serve_window_id)
    report = query.order_by(ServeBiomechanicsReport.created_at.desc()).first()
    if not report:
        print(f"No biomechanics reports found (version={ANALYSIS_VERSION}).")
        sys.exit(1)
    return report


def report_to_coaching_input(
    report: ServeBiomechanicsReport,
) -> tuple[list[dict[str, Any]], list[dict[str, Any]], list[dict[str, Any]]]:
    """Convert a DB report to the dicts our coaching service expects."""
    phases: list[dict[str, Any]] = []
    moments: list[dict[str, Any]] = []

    if report.phase_segmentation_json:
        seg_data = json.loads(report.phase_segmentation_json)
        for pw in seg_data.get("phases", []):
            phase_name = pw["phase"]
            phases.append(
                {
                    "phase": phase_name,
                    "phase_label": PHASE_LABEL_MAP.get(
                        phase_name, phase_name.replace("_", " ").title()
                    ),
                    "start_timestamp": pw["start_timestamp"],
                    "end_timestamp": pw["end_timestamp"],
                    "confidence": pw.get("confidence", 0.0),
                    "detected": pw.get("detected", False),
                }
            )
        for mm in seg_data.get("moments", []):
            moment_name = mm["moment"]
            moments.append(
                {
                    "moment": moment_name,
                    "moment_label": MOMENT_LABEL_MAP.get(
                        moment_name, moment_name.replace("_", " ").title()
                    ),
                    "timestamp": mm.get("timestamp"),
                    "frame": mm.get("frame"),
                    "confidence": mm.get("confidence", 0.0),
                    "detected": mm.get("detected", False),
                }
            )

    metrics = metrics_to_flat_list(report.metrics or {})

    return metrics, phases, moments


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Test coaching feedback on a real report"
    )
    parser.add_argument("--serve-window-id", type=int, default=None)
    args = parser.parse_args()

    db = SessionLocal()
    try:
        report = get_latest_report(db, args.serve_window_id)
        print(f"Using report id={report.id}, serve_window_id={report.serve_window_id}")
        print(f"Analysis version: {report.analysis_version}\n")

        metrics, phases, moments = report_to_coaching_input(report)

        # Show what the LLM will see
        print("=" * 60)
        print("INPUT DATA")
        print("=" * 60)
        print(f"\nPhases ({len(phases)}):")
        for p in phases:
            print(
                f"  {p['phase_label']}: {p['start_timestamp']:.2f}s - {p['end_timestamp']:.2f}s"
            )

        print(f"\nMoments ({len(moments)}):")
        for m in moments:
            ts = m["timestamp"]
            print(f"  {m['moment_label']}: {f'{ts:.2f}s' if ts else 'not detected'}")

        print(f"\nMetrics ({len(metrics)}):")
        for m in metrics:
            val = m["value"]
            unit = m.get("unit", "")
            print(
                f"  {m['metric_name']}: {f'{val:.1f}{unit}' if val is not None else 'null'}"
            )

        # Get video.recorded_at for backwards-looking history
        sw = (
            db.query(ServeWindow)
            .filter(ServeWindow.id == report.serve_window_id)
            .first()
        )
        video = db.query(Video).filter(Video.id == sw.video_id).first() if sw else None
        recorded_at = video.recorded_at if video else None
        if recorded_at:
            print(f"Video recorded at: {recorded_at.isoformat()}")

        # Fetch player history — only serves from videos recorded before this one
        history = get_player_metric_history(
            db,
            report.player_id,
            before=recorded_at,
            exclude_serve_window_id=report.serve_window_id,
        )
        if history:
            print("\nPlayer history (excluding this serve):")
            for name, stats in history.items():
                print(
                    f"  {name}: min={stats['min']}, max={stats['max']}, "
                    f"mean={stats['mean']} ({stats['count']} serves)"
                )
        else:
            print("\nNo player history available.")

        # Call the LLM
        print("\n" + "=" * 60)
        print("CALLING LLM...")
        print("=" * 60 + "\n")

        result = generate_coaching_feedback(
            metrics=metrics,
            phases=phases,
            moments=moments,
            serve_window_id=report.serve_window_id,
            history=history,
        )

        print(result.feedback)
        print(
            f"\n--- model={result.model}, latency={result.latency_ms:.0f}ms, "
            f"tokens={result.input_tokens}/{result.output_tokens} ---"
        )

    finally:
        db.close()


if __name__ == "__main__":
    main()
