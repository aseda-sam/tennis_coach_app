"""Serve biomechanics API routes."""

import json
import logging
from typing import List

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.api.schemas.serve_biomechanics import (
    BiomechanicsReportResponse,
    MetricValueResponse,
    PhaseWindowResponse,
)
from app.core.database import get_db
from app.dependencies.auth import get_current_user
from app.models.serve_biomechanics_report import ServeBiomechanicsReport
from app.services.biomechanics.metrics import metrics_to_flat_list
from app.services.biomechanics.serve_biomechanics_service import (
    serve_biomechanics_service,
)
from app.services.player_service import get_player_by_id
from app.utils.authorization import require_player_access
from app.utils.error_handling import handle_not_found_error, log_and_raise_error

logger = logging.getLogger(__name__)

router = APIRouter(tags=["serve-biomechanics"])

PHASE_LABEL_MAP = {
    "start": "Start",
    "release": "Release",
    "loading": "Loading",
    "cocking": "Cocking",
    "acceleration": "Acceleration",
    "contact": "Contact",
    "deceleration": "Deceleration",
    "finish": "Finish",
}


def _report_to_response(report: ServeBiomechanicsReport) -> BiomechanicsReportResponse:
    """Convert DB model to API response."""
    phase_segmentation = []
    if report.phase_segmentation_json:
        seg_data = json.loads(report.phase_segmentation_json)
        for pw in seg_data.get("phases", []):
            phase_name = pw["phase"]
            phase_segmentation.append(
                PhaseWindowResponse(
                    phase=phase_name,
                    phase_label=PHASE_LABEL_MAP.get(
                        phase_name, phase_name.replace("_", " ").title()
                    ),
                    start_timestamp=pw["start_timestamp"],
                    end_timestamp=pw["end_timestamp"],
                    confidence=pw.get("confidence", 0.0),
                    detected=pw.get("detected", False),
                )
            )

    metrics = []
    if report.metrics_json:
        from app.services.biomechanics.metrics import BiomechanicsMetrics

        metrics_obj = BiomechanicsMetrics.model_validate(
            json.loads(report.metrics_json)
        )
        for m in metrics_to_flat_list(metrics_obj):
            metrics.append(MetricValueResponse(**m))

    return BiomechanicsReportResponse(
        id=report.id,
        serve_window_id=report.serve_window_id,
        phase_segmentation=phase_segmentation,
        metrics=metrics,
        analysis_version=report.analysis_version,
        created_at=report.created_at,
    )


@router.get(
    "/serve-windows/{serve_window_id}/biomechanics",
    response_model=BiomechanicsReportResponse,
)
async def get_serve_biomechanics(
    serve_window_id: int,
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> BiomechanicsReportResponse:
    """Get biomechanics report for a serve window. Computes lazily on first request."""
    user_id = current_user["id"]
    try:
        report = serve_biomechanics_service.get_or_compute_analysis(
            db, serve_window_id, user_id
        )
        return _report_to_response(report)
    except ValueError as e:
        raise handle_not_found_error("serve_window", str(serve_window_id)) from e
    except Exception as e:  # noqa: BLE001 - catch-all for log_and_raise_error
        log_and_raise_error(
            e, "get_serve_biomechanics", {"serve_window_id": serve_window_id}
        )


@router.post(
    "/serve-windows/{serve_window_id}/biomechanics/compute",
    response_model=BiomechanicsReportResponse,
    status_code=status.HTTP_201_CREATED,
)
async def compute_serve_biomechanics(
    serve_window_id: int,
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> BiomechanicsReportResponse:
    """Force (re)compute biomechanics for a serve window."""
    user_id = current_user["id"]
    try:
        report = serve_biomechanics_service.compute_analysis(
            db, serve_window_id, user_id
        )
        return _report_to_response(report)
    except ValueError as e:
        raise handle_not_found_error("serve_window", str(serve_window_id)) from e
    except Exception as e:  # noqa: BLE001 - catch-all for log_and_raise_error
        log_and_raise_error(
            e, "compute_serve_biomechanics", {"serve_window_id": serve_window_id}
        )


@router.get(
    "/players/{player_id}/biomechanics/history",
    response_model=List[BiomechanicsReportResponse],
)
async def get_player_biomechanics_history(
    player_id: int,
    limit: int = Query(default=20, le=100),
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> List[BiomechanicsReportResponse]:
    """Get historical biomechanics reports for a player."""
    player = get_player_by_id(db, player_id)
    if not player:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Player {player_id} not found",
        )
    require_player_access(player, current_user)

    user_id = current_user["id"]
    try:
        reports = serve_biomechanics_service.get_player_history(
            db, player_id, user_id, limit=limit
        )
        return [_report_to_response(r) for r in reports]
    except ValueError as e:
        raise handle_not_found_error("player", str(player_id)) from e
    except Exception as e:  # noqa: BLE001 - catch-all for log_and_raise_error
        log_and_raise_error(
            e, "get_player_biomechanics_history", {"player_id": player_id}
        )
