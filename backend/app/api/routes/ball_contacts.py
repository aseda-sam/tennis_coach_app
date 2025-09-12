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
    PostureAnalysisRequest,
    PostureAnalysisResponse,
)
from app.api.schemas.video_player import BallContactPlayerOptions
from app.core.database import get_db
from app.services.ball_contact_service import (
    create_ball_contact,
    delete_ball_contact,
    get_ball_contact_by_id,
    get_ball_contacts_by_video_id,
    update_ball_contact,
)
from app.services.posture_analysis import analyze_and_store_contact_posture
from app.services.video_player_service import get_ball_contact_player_options

router = APIRouter(tags=["ball-contacts"])


@router.post("/", response_model=BallContactInfo, status_code=status.HTTP_201_CREATED)
def create_ball_contact(
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
            player_id=ball_contact.player_id,
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
        from app.models.player import Player

        ball_contacts = get_ball_contacts_by_video_id(db, video_id)

        # Create a mapping of player_id to player_name for efficiency
        player_ids = {
            contact.player_id for contact in ball_contacts if contact.player_id
        }
        players = db.query(Player).filter(Player.id.in_(player_ids)).all()
        player_name_map = {player.id: player.name for player in players}

        # Create response with player names
        return [
            BallContactListItem(
                id=contact.id,
                video_id=contact.video_id,
                frame_number=contact.frame_number,
                video_timestamp=contact.video_timestamp,
                contact_hand=contact.contact_hand,
                stroke_type=contact.stroke_type,
                stroke_subtype=contact.stroke_subtype,
                elbow_angle=contact.elbow_angle,
                detection_source=contact.detection_source,
                player_id=contact.player_id,
                player_name=player_name_map.get(contact.player_id),
                created_at=contact.created_at,
            )
            for contact in ball_contacts
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


@router.get("/player/{player_id}", response_model=List[BallContactListItem])
def get_ball_contacts_by_player(
    player_id: int, db: Session = Depends(get_db)
) -> List[BallContactListItem]:
    """Get all ball contacts for a specific player."""
    try:
        from app.models.ball_contact import BallContact
        from app.models.player import Player

        # Validate player exists
        player = db.query(Player).filter(Player.id == player_id).first()
        if not player:
            raise ValueError(f"Player with ID {player_id} not found")

        # Get ball contacts for the player
        ball_contacts = (
            db.query(BallContact).filter(BallContact.player_id == player_id).all()
        )

        # Create response with player name
        return [
            BallContactListItem(
                id=contact.id,
                video_id=contact.video_id,
                frame_number=contact.frame_number,
                video_timestamp=contact.video_timestamp,
                contact_hand=contact.contact_hand,
                stroke_type=contact.stroke_type,
                stroke_subtype=contact.stroke_subtype,
                elbow_angle=contact.elbow_angle,
                detection_source=contact.detection_source,
                player_id=contact.player_id,
                player_name=player.name,
                created_at=contact.created_at,
            )
            for contact in ball_contacts
        ]
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
def update_ball_contact(
    ball_contact_id: int,
    ball_contact_update: BallContactUpdate,
    db: Session = Depends(get_db),
) -> BallContactInfo:
    """Update a ball contact marker."""
    try:
        # Filter out None values for update, but allow None for player_id to remove assignment
        update_data = {
            k: v
            for k, v in ball_contact_update.model_dump().items()
            if v is not None or k == "player_id"
        }

        updated_contact = update_ball_contact(
            db=db,
            ball_contact_id=ball_contact_id,
            **update_data,
        )
        return BallContactInfo.model_validate(updated_contact)
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        ) from e


@router.delete("/{ball_contact_id}", response_model=BallContactDeleteResponse)
def delete_ball_contact(
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


@router.post(
    "/{ball_contact_id}/analyze-posture", response_model=PostureAnalysisResponse
)
def analyze_ball_contact_posture(
    ball_contact_id: int,
    request: PostureAnalysisRequest,
    db: Session = Depends(get_db),
) -> PostureAnalysisResponse:
    """Analyze posture for a specific ball contact."""
    try:
        result = analyze_and_store_contact_posture(
            db=db,
            ball_contact_id=ball_contact_id,
            force_reanalysis=request.force_reanalysis,
        )
        return PostureAnalysisResponse(**result)
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e),
        ) from e
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Posture analysis failed: {e!s}",
        ) from e


@router.get(
    "/{ball_contact_id}/posture-analysis", response_model=PostureAnalysisResponse
)
def get_ball_contact_posture_analysis(
    ball_contact_id: int, db: Session = Depends(get_db)
) -> PostureAnalysisResponse:
    """Get posture analysis results for a specific ball contact."""
    try:
        ball_contact = get_ball_contact_by_id(db, ball_contact_id)

        if ball_contact.elbow_angle is not None:
            return PostureAnalysisResponse(
                ball_contact_id=ball_contact_id,
                elbow_angle=ball_contact.elbow_angle,
                analysis_status="success",
                message="Posture analysis completed",
            )
        else:
            return PostureAnalysisResponse(
                ball_contact_id=ball_contact_id,
                elbow_angle=None,
                analysis_status="no_pose_data",
                message="No posture analysis available",
            )
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e),
        ) from e


@router.post(
    "/video/{video_id}/analyze-posture", response_model=List[PostureAnalysisResponse]
)
def analyze_video_posture(
    video_id: int,
    request: PostureAnalysisRequest,
    db: Session = Depends(get_db),
) -> List[PostureAnalysisResponse]:
    """Analyze posture for all ball contacts in a video."""
    try:
        # Get all ball contacts for the video
        ball_contacts = get_ball_contacts_by_video_id(db, video_id)

        if not ball_contacts:
            return []

        # Analyze each ball contact
        results = []
        for contact in ball_contacts:
            result = analyze_and_store_contact_posture(
                db=db,
                ball_contact_id=contact.id,
                force_reanalysis=request.force_reanalysis,
            )
            results.append(PostureAnalysisResponse(**result))

        return results
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e),
        ) from e
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Batch posture analysis failed: {e!s}",
        ) from e


@router.get(
    "/video/{video_id}/player-options/", response_model=BallContactPlayerOptions
)
def get_ball_contact_player_options(
    video_id: int, db: Session = Depends(get_db)
) -> BallContactPlayerOptions:
    """Get player assignment options for ball contact creation in a video."""
    try:
        options = get_ball_contact_player_options(db, video_id)
        return BallContactPlayerOptions(**options)
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get player options: {e!s}",
        ) from e
