"""Serve detection API routes."""

import logging
from typing import List

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.api.schemas.serve_attempt import ServeAttemptInfo
from app.api.schemas.serve_detection import (
    AcceptProposalRequest,
    BulkAcceptRequest,
    BulkAcceptResponse,
    ClearProposalsResponse,
    DetectionStatusResponse,
    EditProposalRequest,
    ProposeResponse,
    RejectByConfidenceRequest,
    RejectByConfidenceResponse,
    ServeWindowProposalInfo,
)
from app.core.config import settings
from app.core.database import get_db
from app.dependencies.auth import get_current_user
from app.services import video_service
from app.services.serve_detection import proposal_service
from app.utils.authorization import require_video_access, require_video_not_demo
from app.utils.error_handling import handle_not_found_error, log_and_raise_error

logger = logging.getLogger(__name__)

router = APIRouter(tags=["serve-detection"])


@router.get(
    "/videos/{video_id}/serve-detection/status",
    response_model=DetectionStatusResponse,
)
async def get_detection_status(
    video_id: int,
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> DetectionStatusResponse:
    """
    Get serve detection status for a video.

    Returns counts of existing proposals and serve attempts.
    """
    try:
        # Get video to check authorization
        video = video_service.get_video_by_id(db, video_id)
        if not video:
            raise handle_not_found_error("video", str(video_id))

        # Check authorization
        require_video_access(video, current_user)

        # Get status
        status_data = proposal_service.check_existing_proposals_or_attempts(
            db, video_id, current_user["id"]
        )

        can_run = (
            status_data["pending_proposals"] == 0 and status_data["serve_attempts"] == 0
        )

        return DetectionStatusResponse(
            video_id=video_id,
            pending_proposals=status_data["pending_proposals"],
            reviewed_proposals=status_data["reviewed_proposals"],
            serve_attempts=status_data["serve_attempts"],
            can_run_detection=can_run,
        )

    except Exception as e:  # noqa: BLE001 - catch-all for log_and_raise_error
        log_and_raise_error(e, "get_detection_status", {"video_id": video_id})


@router.post(
    "/videos/{video_id}/serve-detection/propose",
    response_model=ProposeResponse,
    status_code=status.HTTP_200_OK,
)
async def propose_serve_windows(
    video_id: int,
    force: bool = Query(
        default=False,
        description="Force detection even if proposals exist (clears pending proposals)",
    ),
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> ProposeResponse:
    """
    Run serve detection on a video and generate proposals.

    Requires pose detection to be completed first.
    Will fail if pending proposals or serve attempts already exist,
    unless force=true is specified (which clears pending proposals first).
    """
    try:
        # Get video to check authorization
        video = video_service.get_video_by_id(db, video_id)
        if not video:
            raise handle_not_found_error("video", str(video_id))

        # Check authorization
        require_video_access(video, current_user)
        require_video_not_demo(video, current_user)

        # Generate proposals
        proposals = proposal_service.generate_proposals(
            db, video_id, current_user["id"], force=force
        )

        return ProposeResponse(
            video_id=video_id,
            proposals=[ServeWindowProposalInfo.model_validate(p) for p in proposals],
            count=len(proposals),
        )

    except ValueError as e:
        log_and_raise_error(e, "propose_serve_windows", {"video_id": video_id})
    except Exception as e:  # noqa: BLE001 - catch-all for log_and_raise_error
        log_and_raise_error(e, "propose_serve_windows", {"video_id": video_id})


@router.delete(
    "/videos/{video_id}/serve-detection/proposals",
    response_model=ClearProposalsResponse,
)
async def clear_proposals(
    video_id: int,
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> ClearProposalsResponse:
    """
    Clear all pending proposals for a video.

    Only clears pending proposals, not accepted/rejected ones.
    """
    try:
        # Get video to check authorization
        video = video_service.get_video_by_id(db, video_id)
        if not video:
            raise handle_not_found_error("video", str(video_id))

        # Check authorization
        require_video_access(video, current_user)
        require_video_not_demo(video, current_user)

        # Clear proposals
        cleared_count = proposal_service.clear_pending_proposals(
            db, video_id, current_user["id"]
        )

        return ClearProposalsResponse(
            video_id=video_id,
            cleared_count=cleared_count,
        )

    except Exception as e:  # noqa: BLE001 - catch-all for log_and_raise_error
        log_and_raise_error(e, "clear_proposals", {"video_id": video_id})


@router.get(
    "/videos/{video_id}/serve-detection/proposals",
    response_model=List[ServeWindowProposalInfo],
)
async def get_proposals(
    video_id: int,
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> List[ServeWindowProposalInfo]:
    """
    Get pending proposals for a video.
    """
    try:
        # Get video to check authorization
        video = video_service.get_video_by_id(db, video_id)
        if not video:
            raise handle_not_found_error("video", str(video_id))

        # Check authorization
        require_video_access(video, current_user)

        # Get pending proposals for this video and user
        proposals = proposal_service.get_pending_proposals(
            db=db,
            video_id=video_id,
            user_id=current_user["id"],
        )

        return [ServeWindowProposalInfo.model_validate(p) for p in proposals]

    except Exception as e:  # noqa: BLE001 - catch-all for log_and_raise_error
        log_and_raise_error(e, "get_proposals", {"video_id": video_id})


@router.post(
    "/serve-detection/proposals/{proposal_id}/accept",
    response_model=ServeAttemptInfo,
    status_code=status.HTTP_201_CREATED,
)
async def accept_proposal(
    proposal_id: int,
    request: AcceptProposalRequest,
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> ServeAttemptInfo:
    """
    Accept a proposal as-is, creating a ServeAttempt.
    """
    try:
        serve_attempt = proposal_service.accept_proposal(
            db, proposal_id, current_user["id"], request.player_id
        )
        return ServeAttemptInfo.model_validate(serve_attempt)

    except ValueError as e:
        log_and_raise_error(e, "accept_proposal", {"proposal_id": proposal_id})
    except Exception as e:  # noqa: BLE001 - catch-all for log_and_raise_error
        log_and_raise_error(e, "accept_proposal", {"proposal_id": proposal_id})


@router.post(
    "/serve-detection/proposals/{proposal_id}/reject",
    status_code=status.HTTP_200_OK,
)
async def reject_proposal(
    proposal_id: int,
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> dict:
    """
    Reject a proposal.
    """
    try:
        proposal_service.reject_proposal(db, proposal_id, current_user["id"])
        return {"message": f"Proposal {proposal_id} rejected"}

    except ValueError as e:
        log_and_raise_error(e, "reject_proposal", {"proposal_id": proposal_id})
    except Exception as e:  # noqa: BLE001 - catch-all for log_and_raise_error
        log_and_raise_error(e, "reject_proposal", {"proposal_id": proposal_id})


@router.post(
    "/serve-detection/proposals/{proposal_id}/edit",
    response_model=ServeAttemptInfo,
    status_code=status.HTTP_201_CREATED,
)
async def edit_proposal(
    proposal_id: int,
    request: EditProposalRequest,
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> ServeAttemptInfo:
    """
    Accept a proposal with edited timestamps, creating a ServeAttempt.
    """
    try:
        serve_attempt = proposal_service.accept_with_edits(
            db,
            proposal_id,
            current_user["id"],
            request.start_timestamp,
            request.end_timestamp,
            request.player_id,
        )
        return ServeAttemptInfo.model_validate(serve_attempt)

    except ValueError as e:
        error_msg = str(e).lower()
        if "not found" in error_msg or "unauthorized" in error_msg:
            raise handle_not_found_error("proposal", str(proposal_id)) from e
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        ) from e
    except HTTPException:
        raise
    except Exception as e:  # noqa: BLE001 - catch-all for log_and_raise_error
        log_and_raise_error(e, "edit_proposal", {"proposal_id": proposal_id})


@router.post(
    "/videos/{video_id}/serve-detection/proposals/accept-all",
    response_model=BulkAcceptResponse,
    status_code=status.HTTP_200_OK,
)
async def accept_all_proposals(
    video_id: int,
    request: BulkAcceptRequest,
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> BulkAcceptResponse:
    """
    Accept all pending proposals for a video, creating ServeAttempts.

    This is a bulk operation that accepts all pending proposals at once,
    creating a ServeAttempt for each one.
    """
    try:
        # Get video to check authorization
        video = video_service.get_video_by_id(db, video_id)
        if not video:
            raise handle_not_found_error("video", str(video_id))

        # Check authorization
        require_video_access(video, current_user)
        require_video_not_demo(video, current_user)

        # Accept all proposals
        serve_attempts = proposal_service.accept_all_proposals(
            db, video_id, current_user["id"], request.player_id
        )

        return BulkAcceptResponse(
            video_id=video_id,
            accepted_count=len(serve_attempts),
            serve_attempt_ids=[sa.id for sa in serve_attempts],
        )

    except ValueError as e:
        log_and_raise_error(e, "accept_all_proposals", {"video_id": video_id})
    except Exception as e:  # noqa: BLE001 - catch-all for log_and_raise_error
        log_and_raise_error(e, "accept_all_proposals", {"video_id": video_id})


@router.post(
    "/videos/{video_id}/serve-detection/proposals/reject-by-confidence",
    response_model=RejectByConfidenceResponse,
    status_code=status.HTTP_200_OK,
)
async def reject_proposals_by_confidence(
    video_id: int,
    request: RejectByConfidenceRequest,
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> RejectByConfidenceResponse:
    """
    Reject all pending proposals below a confidence threshold.

    This is a bulk operation that rejects proposals with confidence
    scores below the specified threshold. If not provided, uses the
    SERVE_DETECTION_LOW_CONFIDENCE_THRESHOLD from config (default: 60%).
    """
    try:
        # Get video to check authorization
        video = video_service.get_video_by_id(db, video_id)
        if not video:
            raise handle_not_found_error("video", str(video_id))

        # Check authorization
        require_video_access(video, current_user)
        require_video_not_demo(video, current_user)

        # Use config default if threshold not provided
        threshold = (
            request.threshold
            if request.threshold is not None
            else settings.SERVE_DETECTION_LOW_CONFIDENCE_THRESHOLD
        )

        # Reject low confidence proposals
        rejected_count = proposal_service.reject_proposals_by_confidence(
            db, video_id, current_user["id"], threshold
        )

        return RejectByConfidenceResponse(
            video_id=video_id,
            rejected_count=rejected_count,
            threshold=threshold,
        )

    except ValueError as e:
        log_and_raise_error(e, "reject_by_confidence", {"video_id": video_id})
    except Exception as e:  # noqa: BLE001 - catch-all for log_and_raise_error
        log_and_raise_error(e, "reject_by_confidence", {"video_id": video_id})
