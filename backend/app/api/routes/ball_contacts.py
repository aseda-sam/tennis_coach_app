"""Ball contact API routes."""

from typing import List

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.api.schemas.ball_contact import (
    BallContactCreate,
    BallContactDeleteResponse,
    BallContactInfo,
    BallContactListItem,
    BallContactUpdate,
)
from app.core.database import get_db
from app.services.ball_contact_service import (
    create_ball_contact,
    delete_ball_contact,
    get_ball_contact_by_id,
    get_ball_contacts_by_video_id,
    update_ball_contact,
)

router = APIRouter(tags=["ball-contacts"])


@router.post("/", response_model=BallContactInfo, status_code=status.HTTP_201_CREATED)
def create_ball_contact_endpoint(
    ball_contact: BallContactCreate, db: Session = Depends(get_db)
) -> BallContactInfo:
    """Create a new ball contact marker."""
    try:
        db_ball_contact = create_ball_contact(
            db=db,
            video_id=ball_contact.video_id,
            video_timestamp=ball_contact.video_timestamp,
            contact_hand=ball_contact.contact_hand,
            stroke_type=ball_contact.stroke_type,
            stroke_subtype=ball_contact.stroke_subtype,
            detection_source=ball_contact.detection_source,
        )
        return BallContactInfo.model_validate(db_ball_contact)
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        ) from e


@router.get("/video/{video_id}", response_model=List[BallContactListItem])
def get_ball_contacts_by_video(
    video_id: int, db: Session = Depends(get_db)
) -> List[BallContactListItem]:
    """Get all ball contacts for a specific video."""
    try:
        ball_contacts = get_ball_contacts_by_video_id(db, video_id)
        return [
            BallContactListItem.model_validate(contact) for contact in ball_contacts
        ]
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e),
        ) from e


@router.get("/video/{video_id}/timestamps", response_model=List[float])
def get_ball_contact_timestamps(
    video_id: int, db: Session = Depends(get_db)
) -> List[float]:
    """Get all ball contact timestamps for a specific video."""
    try:
        ball_contacts = get_ball_contacts_by_video_id(db, video_id)
        return [contact.video_timestamp for contact in ball_contacts]
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e),
        ) from e


@router.get("/{ball_contact_id}", response_model=BallContactInfo)
def get_ball_contact(
    ball_contact_id: int, db: Session = Depends(get_db)
) -> BallContactInfo:
    """Get a specific ball contact by ID."""
    try:
        ball_contact = get_ball_contact_by_id(db, ball_contact_id)
        return BallContactInfo.model_validate(ball_contact)
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e),
        ) from e


@router.put("/{ball_contact_id}", response_model=BallContactInfo)
def update_ball_contact_endpoint(
    ball_contact_id: int,
    ball_contact_update: BallContactUpdate,
    db: Session = Depends(get_db),
) -> BallContactInfo:
    """Update a ball contact marker."""
    try:
        updated_contact = update_ball_contact(
            db=db,
            ball_contact_id=ball_contact_id,
            video_timestamp=ball_contact_update.video_timestamp,
            contact_hand=ball_contact_update.contact_hand,
            stroke_type=ball_contact_update.stroke_type,
            stroke_subtype=ball_contact_update.stroke_subtype,
        )
        return BallContactInfo.model_validate(updated_contact)
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        ) from e


@router.delete("/{ball_contact_id}", response_model=BallContactDeleteResponse)
def delete_ball_contact_endpoint(
    ball_contact_id: int, db: Session = Depends(get_db)
) -> BallContactDeleteResponse:
    """Delete a ball contact marker."""
    try:
        delete_ball_contact(db, ball_contact_id)
        return BallContactDeleteResponse(
            message=f"Ball contact {ball_contact_id} deleted successfully"
        )
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e),
        ) from e
