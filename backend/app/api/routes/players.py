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
from app.models.player import Player
from app.services.player_service import (
    create_player,
    delete_player,
    get_player_by_id,
    get_players,
    update_player,
)
from app.utils.error_handling import handle_processing_error, log_and_raise_error

router = APIRouter(tags=["players"])


def _create_player_info(db: Session, player: Player) -> PlayerInfo:
    """Convert Player model to PlayerInfo schema."""
    return PlayerInfo(
        id=player.id,
        name=player.name,
        dominant_hand=player.dominant_hand,
        backhand_style=player.backhand_style,
        height=player.height,
        notes=player.notes,
        created_at=player.created_at,
        updated_at=player.updated_at,
    )


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

        return _create_player_info(db, db_player)
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

        # Create response
        return [
            PlayerListItem(
                id=player.id,
                name=player.name,
                dominant_hand=player.dominant_hand,
                backhand_style=player.backhand_style,
                height=player.height,
                created_at=player.created_at,
            )
            for player in players
        ]
    except Exception as e:
        raise handle_processing_error("get_players", str(e)) from e


@router.get("/{player_id}", response_model=PlayerInfo)
def get_player_endpoint(player_id: int, db: Session = Depends(get_db)) -> PlayerInfo:
    """Get a specific player by ID."""
    try:
        player = get_player_by_id(db, player_id)
        if not player:
            raise ValueError(f"Player with ID {player_id} not found")

        return _create_player_info(db, player)
    except ValueError as e:
        # Check if it's a "not found" error
        if "not found" in str(e).lower():
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=str(e),
            ) from e
        else:
            log_and_raise_error(e, "get_player", {"player_id": player_id})


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

        return _create_player_info(db, player)
    except ValueError as e:
        # Check if it's a "not found" error
        if "not found" in str(e).lower():
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=str(e),
            ) from e
        else:
            log_and_raise_error(e, "update_player", {"player_id": player_id})


@router.delete("/{player_id}", response_model=PlayerDeleteResponse)
def delete_player_endpoint(
    player_id: int, db: Session = Depends(get_db)
) -> PlayerDeleteResponse:
    """Delete a player."""
    try:
        delete_player(db, player_id)
        return PlayerDeleteResponse(message=f"Player {player_id} deleted successfully")
    except ValueError as e:
        # Check if it's a "not found" error
        if "not found" in str(e).lower():
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=str(e),
            ) from e
        else:
            log_and_raise_error(e, "delete_player", {"player_id": player_id})
