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
from app.dependencies.auth import get_current_user
from app.models.player import Player
from app.services.player_service import (
    create_player as create_player_service,
)
from app.services.player_service import (
    delete_player as delete_player_service,
)
from app.services.player_service import (
    get_player_by_id,
)
from app.services.player_service import (
    update_player as update_player_service,
)
from app.utils.authorization import is_admin, require_player_access
from app.utils.error_handling import handle_processing_error, log_and_raise_error

router = APIRouter(tags=["players"])


def _create_player_info(db: Session, player: Player) -> PlayerInfo:
    """Convert Player model to PlayerInfo schema."""
    return PlayerInfo(
        id=player.id,
        name=player.name,
        dominant_hand=player.dominant_hand,
        backhand_style=player.backhand_style,
        notes=player.notes,
        created_at=player.created_at,
        updated_at=player.updated_at,
    )


@router.post("/", response_model=PlayerInfo, status_code=status.HTTP_201_CREATED)
def create_player(
    player: PlayerCreate,
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> PlayerInfo:
    """Create a new player."""
    try:
        db_player = create_player_service(
            db=db,
            name=player.name,
            dominant_hand=player.dominant_hand,
            user_id=current_user["id"],
            backhand_style=player.backhand_style,
            notes=player.notes,
        )

        return _create_player_info(db, db_player)
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        ) from e


@router.get("/", response_model=List[PlayerListItem])
def get_players(
    skip: int = Query(0, ge=0, description="Number of records to skip"),
    limit: int = Query(
        100, ge=1, le=1000, description="Maximum number of records to return"
    ),
    name: Optional[str] = Query(None, description="Filter by name (partial match)"),
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> List[PlayerListItem]:
    """Get all players for the current user with optional filtering and pagination."""
    try:
        # Filter by user_id unless admin
        query = db.query(Player)
        if not is_admin(current_user):
            query = query.filter(Player.user_id == current_user["id"])

        if name:
            query = query.filter(Player.name.ilike(f"%{name}%"))

        players = query.offset(skip).limit(limit).all()

        # Create response
        return [
            PlayerListItem(
                id=player.id,
                name=player.name,
                dominant_hand=player.dominant_hand,
                backhand_style=player.backhand_style,
                created_at=player.created_at,
            )
            for player in players
        ]
    except Exception as e:
        raise handle_processing_error("get_players", str(e)) from e


@router.get("/{player_id}", response_model=PlayerInfo)
def get_player(
    player_id: int,
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> PlayerInfo:
    """Get a specific player by ID."""
    try:
        player = get_player_by_id(db, player_id)
        if not player:
            raise ValueError(f"Player with ID {player_id} not found")

        # Check authorization
        require_player_access(player, current_user)

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
def update_player(
    player_id: int,
    player_update: PlayerUpdate,
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> PlayerInfo:
    """Update a player."""
    try:
        # Get player first to check authorization
        player = get_player_by_id(db, player_id)
        if not player:
            raise ValueError(f"Player with ID {player_id} not found")

        # Check authorization (only owner can update)
        require_player_access(player, current_user)

        # Filter out None values for update
        update_data = {
            k: v for k, v in player_update.model_dump().items() if v is not None
        }

        if not update_data:
            # No fields to update, return current player
            pass
        else:
            player = update_player_service(db, player_id, **update_data)

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
def delete_player(
    player_id: int,
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> PlayerDeleteResponse:
    """Delete a player."""
    try:
        # Get player first to check authorization
        player = get_player_by_id(db, player_id)
        if not player:
            raise ValueError(f"Player with ID {player_id} not found")

        # Check authorization (only owner can delete)
        require_player_access(player, current_user)

        delete_player_service(db, player_id)
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
