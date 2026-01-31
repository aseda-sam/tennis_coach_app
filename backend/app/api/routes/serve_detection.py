"""Serve detection API routes."""

import logging
from typing import List

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.api.schemas.serve_attempt import ServeAttemptInfo
from app.api.schemas.serve_detection import (
    AcceptProposalRequest,
    EditProposalRequest,
    ProposeResponse,
    ServeWindowProposalInfo,
)
from app.core.database import get_db
from app.dependencies.auth import get_current_user
from app.models.serve_window_proposal import ServeWindowProposal
from app.services import video_service
from app.services.serve_detection import proposal_service
from app.utils.authorization import require_video_access, require_video_not_demo
from app.utils.error_handling import handle_not_found_error, log_and_raise_error

logger = logging.getLogger(__name__)

router = APIRouter(tags=["serve-detection"])


@router.post(
    "/videos/{video_id}/serve-detection/propose",
    response_model=ProposeResponse,
    status_code=status.HTTP_200_OK,
)
async def propose_serve_windows(
    video_id: int,
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> ProposeResponse:
    """
    Run serve detection on a video and generate proposals.

    Requires pose detection to be completed first.
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
        proposals = proposal_service.generate_proposals(db, video_id, current_user["id"])

        return ProposeResponse(
            video_id=video_id,
            proposals=[ServeWindowProposalInfo.model_validate(p) for p in proposals],
            count=len(proposals),
        )

    except ValueError as e:
        log_and_raise_error(e, "propose_serve_windows", {"video_id": video_id})
    except Exception as e:
        log_and_raise_error(e, "propose_serve_windows", {"video_id": video_id})


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
        proposals = (
            db.query(ServeWindowProposal)
            .filter(
                ServeWindowProposal.video_id == video_id,
                ServeWindowProposal.user_id == current_user["id"],
                ServeWindowProposal.status == "pending",
            )
            .order_by(ServeWindowProposal.start_timestamp)
            .all()
        )

        return [ServeWindowProposalInfo.model_validate(p) for p in proposals]

    except Exception as e:
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
    except Exception as e:
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
    except Exception as e:
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
        # Validate timestamps
        if request.start_timestamp >= request.end_timestamp:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="start_timestamp must be less than end_timestamp",
            )

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
        log_and_raise_error(e, "edit_proposal", {"proposal_id": proposal_id})
    except HTTPException:
        raise
    except Exception as e:
        log_and_raise_error(e, "edit_proposal", {"proposal_id": proposal_id})
