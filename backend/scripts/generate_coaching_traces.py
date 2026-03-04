#!/usr/bin/env python3
"""Generate coaching traces for all v7 reports with non-null metrics.

Calls the coaching LLM for every qualifying serve window and relies on
the JSONL logger to capture input/output pairs for eval.

Usage:
    # Start Docker first: docker compose up -d postgres
    cd backend
    python scripts/generate_coaching_traces.py
"""

import sys
from pathlib import Path

# Add backend to path
backend_dir = Path(__file__).parent.parent
sys.path.insert(0, str(backend_dir))

from sqlalchemy.orm import Session  # noqa: E402
from test_coaching_feedback import report_to_coaching_input  # noqa: E402

from app.core.database import SessionLocal  # noqa: E402
from app.models.serve_biomechanics_report import ServeBiomechanicsReport  # noqa: E402
from app.models.serve_window import ServeWindow  # noqa: E402
from app.models.video import Video  # noqa: E402
from app.services.biomechanics.serve_biomechanics_service import (  # noqa: E402
    ANALYSIS_VERSION,
)
from app.services.coaching.coaching_service import (  # noqa: E402
    generate_coaching_feedback,
)
from app.services.coaching.player_history import get_player_metric_history  # noqa: E402


def get_all_v7_reports(db: Session) -> list[ServeBiomechanicsReport]:
    """Get all v7 reports that have non-null metrics."""
    reports = (
        db.query(ServeBiomechanicsReport)
        .filter(
            ServeBiomechanicsReport.analysis_version == ANALYSIS_VERSION,
            ServeBiomechanicsReport.metrics.isnot(None),
        )
        .order_by(ServeBiomechanicsReport.serve_window_id)
        .all()
    )
    # Filter to reports that have at least one non-null metric value
    result = []
    for r in reports:
        if not r.metrics:
            continue
        has_value = False
        for phase_metrics in r.metrics.values():
            if isinstance(phase_metrics, dict):
                for m in phase_metrics.values():
                    if isinstance(m, dict) and m.get("value") is not None:
                        has_value = True
                        break
            if has_value:
                break
        if has_value:
            result.append(r)
    return result


def main() -> None:
    db = SessionLocal()
    try:
        reports = get_all_v7_reports(db)
        total = len(reports)
        print(f"Found {total} v7 reports with non-null metrics\n")

        succeeded = 0
        failed = 0
        total_input_tokens = 0
        total_output_tokens = 0

        for i, report in enumerate(reports, 1):
            sw_id = report.serve_window_id
            print(f"Processing {i}/{total}: sw={sw_id}...", end=" ", flush=True)

            try:
                metrics, phases, moments = report_to_coaching_input(report)

                # Get video.recorded_at for backwards-looking history
                sw = db.query(ServeWindow).filter(ServeWindow.id == sw_id).first()
                video = (
                    db.query(Video).filter(Video.id == sw.video_id).first()
                    if sw
                    else None
                )
                recorded_at = video.recorded_at if video else None

                history = get_player_metric_history(
                    db,
                    report.player_id,
                    before=recorded_at,
                    exclude_serve_window_id=sw_id,
                )

                result = generate_coaching_feedback(
                    metrics=metrics,
                    phases=phases,
                    moments=moments,
                    serve_window_id=sw_id,
                    history=history,
                )

                total_input_tokens += result.input_tokens
                total_output_tokens += result.output_tokens
                succeeded += 1
                print(
                    f"ok ({result.input_tokens}/{result.output_tokens} tokens, "
                    f"{result.latency_ms:.0f}ms)"
                )

            except Exception as e:  # noqa: BLE001
                failed += 1
                print(f"FAILED: {e}")

        print(f"\n{'=' * 60}")
        print(f"Total:    {total}")
        print(f"Succeeded: {succeeded}")
        print(f"Failed:    {failed}")
        print(f"Input tokens:  {total_input_tokens}")
        print(f"Output tokens: {total_output_tokens}")
        print(f"Total tokens:  {total_input_tokens + total_output_tokens}")

    finally:
        db.close()


if __name__ == "__main__":
    main()
