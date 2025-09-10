"""Player API routes."""

from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.api.schemas.player import (
    PlayerCreate,
    PlayerDeleteResponse,
    PlayerInfo,
    PlayerListItem,
    PlayerUpdate,
)
from app.core.database import get_db
from app.services.player_service import (
    create_player,
    delete_player,
    get_player_ball_contact_count,
    get_player_by_id,
    get_players,
    update_player,
)

router = APIRouter(tags=["players"])


@router.post("/", response_model=PlayerInfo, status_code=status.HTTP_201_CREATED)
def create_player_endpoint(
    player: PlayerCreate, db: Session = Depends(get_db)
) -> PlayerInfo:
    """Create a new player."""
    try:
        db_player = create_player(
            db=db,
            name=player.name,
            dominant_hand=player.dominant_hand,
            backhand_style=player.backhand_style,
            height=player.height,
            notes=player.notes,
        )

        # Get ball contact count for the player
        ball_contact_count = get_player_ball_contact_count(db, db_player.id)

        # Create response with ball contact count
        player_info = PlayerInfo(
            id=db_player.id,
            name=db_player.name,
            dominant_hand=db_player.dominant_hand,
            backhand_style=db_player.backhand_style,
            height=db_player.height,
            notes=db_player.notes,
            ball_contact_count=ball_contact_count,
            created_at=db_player.created_at,
            updated_at=db_player.updated_at,
        )

        return player_info
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        ) from e


@router.get("/", response_model=List[PlayerListItem])
def get_players_endpoint(
    skip: int = Query(0, ge=0, description="Number of records to skip"),
    limit: int = Query(
        100, ge=1, le=1000, description="Maximum number of records to return"
    ),
    name: Optional[str] = Query(None, description="Filter by name (partial match)"),
    db: Session = Depends(get_db),
) -> List[PlayerListItem]:
    """Get all players with optional filtering and pagination."""
    try:
        players = get_players(db, skip=skip, limit=limit, name_filter=name)

        # Create response with ball contact counts
        player_list = []
        for player in players:
            ball_contact_count = get_player_ball_contact_count(db, player.id)
            player_list.append(
                PlayerListItem(
                    id=player.id,
                    name=player.name,
                    dominant_hand=player.dominant_hand,
                    backhand_style=player.backhand_style,
                    height=player.height,
                    ball_contact_count=ball_contact_count,
                    created_at=player.created_at,
                )
            )

        return player_list
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to retrieve players: {e!s}",
        ) from e


@router.get("/{player_id}", response_model=PlayerInfo)
def get_player_endpoint(player_id: int, db: Session = Depends(get_db)) -> PlayerInfo:
    """Get a specific player by ID."""
    try:
        player = get_player_by_id(db, player_id)
        if not player:
            raise ValueError(f"Player with ID {player_id} not found")

        # Get ball contact count for the player
        ball_contact_count = get_player_ball_contact_count(db, player.id)

        # Create response with ball contact count
        player_info = PlayerInfo(
            id=player.id,
            name=player.name,
            dominant_hand=player.dominant_hand,
            backhand_style=player.backhand_style,
            height=player.height,
            notes=player.notes,
            ball_contact_count=ball_contact_count,
            created_at=player.created_at,
            updated_at=player.updated_at,
        )

        return player_info
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e),
        ) from e


@router.put("/{player_id}", response_model=PlayerInfo)
def update_player_endpoint(
    player_id: int,
    player_update: PlayerUpdate,
    db: Session = Depends(get_db),
) -> PlayerInfo:
    """Update a player."""
    try:
        # Filter out None values for update
        update_data = {
            k: v for k, v in player_update.model_dump().items() if v is not None
        }

        if not update_data:
            # No fields to update, return current player
            player = get_player_by_id(db, player_id)
            if not player:
                raise ValueError(f"Player with ID {player_id} not found")
        else:
            player = update_player(db, player_id, **update_data)

        # Get ball contact count for the player
        ball_contact_count = get_player_ball_contact_count(db, player.id)

        # Create response with ball contact count
        player_info = PlayerInfo(
            id=player.id,
            name=player.name,
            dominant_hand=player.dominant_hand,
            backhand_style=player.backhand_style,
            height=player.height,
            notes=player.notes,
            ball_contact_count=ball_contact_count,
            created_at=player.created_at,
            updated_at=player.updated_at,
        )

        return player_info
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        ) from e


@router.delete("/{player_id}", response_model=PlayerDeleteResponse)
def delete_player_endpoint(
    player_id: int, db: Session = Depends(get_db)
) -> PlayerDeleteResponse:
    """Delete a player."""
    try:
        delete_player(db, player_id)
        return PlayerDeleteResponse(message=f"Player {player_id} deleted successfully")
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e),
        ) from e
