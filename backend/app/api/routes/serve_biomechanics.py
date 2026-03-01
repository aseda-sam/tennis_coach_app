"""Serve biomechanics API routes."""

import json
import logging
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.api.schemas.serve_biomechanics import (
    BiomechanicsReportResponse,
    MetricValueResponse,
    MomentMarkerResponse,
    PhaseWindowResponse,
)
from app.core.database import get_db
from app.dependencies.auth import get_current_user, get_optional_user
from app.models.serve_biomechanics_report import ServeBiomechanicsReport
from app.services import serve_window_service, video_service
from app.services.biomechanics.metrics import metrics_to_flat_list
from app.services.biomechanics.serve_biomechanics_service import (
    serve_biomechanics_service,
)
from app.services.player_service import get_player_by_id
from app.utils.authorization import (
    require_player_access,
    require_video_access_or_public_demo,
)
from app.utils.error_handling import handle_not_found_error, log_and_raise_error

logger = logging.getLogger(__name__)

router = APIRouter(tags=["serve-biomechanics"])

PHASE_LABEL_MAP = {
    "toss": "Toss",
    "trophy_load": "Trophy & Load",
    "acceleration": "Acceleration",
    "follow_through": "Follow-Through",
}

MOMENT_LABEL_MAP = {
    "ball_release": "Ball Release",
    "trophy_position": "Trophy Position",
    "racket_low_point": "Racket Low Point",
    "ball_impact": "Ball Impact",
}


def _report_to_response(report: ServeBiomechanicsReport) -> BiomechanicsReportResponse:
    """Convert DB model to API response."""
    phase_segmentation = []
    moments = []
    seg_data = None
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
        for mm in seg_data.get("moments", []):
            moment_name = mm["moment"]
            moments.append(
                MomentMarkerResponse(
                    moment=moment_name,
                    moment_label=MOMENT_LABEL_MAP.get(
                        moment_name, moment_name.replace("_", " ").title()
                    ),
                    timestamp=mm.get("timestamp"),
                    frame=mm.get("frame"),
                    confidence=mm.get("confidence", 0.0),
                    detected=mm.get("detected", False),
                )
            )

    metrics = []
    nested = report.metrics or {}
    for m in metrics_to_flat_list(nested):
        metrics.append(MetricValueResponse(**m))

    detection_meta = seg_data.get("detection_meta") if seg_data else None

    return BiomechanicsReportResponse(
        id=report.id,
        serve_window_id=report.serve_window_id,
        phase_segmentation=phase_segmentation,
        moments=moments,
        metrics=metrics,
        analysis_version=report.analysis_version,
        detection_meta=detection_meta,
        created_at=report.created_at,
    )


@router.get(
    "/serve-windows/{serve_window_id}/biomechanics",
    response_model=BiomechanicsReportResponse,
)
async def get_serve_biomechanics(
    serve_window_id: int,
    current_user: Optional[dict] = Depends(get_optional_user),
    db: Session = Depends(get_db),
) -> BiomechanicsReportResponse:
    """Get biomechanics report for a serve window. Computes lazily on first request."""
    try:
        # Look up serve window to get video for auth check
        sw = serve_window_service.get_serve_window_by_id_no_auth(db, serve_window_id)
        video = video_service.get_video_by_id(db, sw.video_id)
        if not video:
            raise handle_not_found_error("video", str(sw.video_id))
        require_video_access_or_public_demo(video, current_user)

        # For unauthenticated demo access, use the serve window owner's user_id
        user_id = current_user["id"] if current_user else sw.user_id

        report = serve_biomechanics_service.get_or_compute_analysis(
            db, serve_window_id, user_id
        )
        return _report_to_response(report)
    except ValueError as e:
        raise handle_not_found_error("serve_window", str(serve_window_id)) from e
    except HTTPException:
        raise
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
