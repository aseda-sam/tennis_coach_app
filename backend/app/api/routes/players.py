"""Player API routes."""

from typing import List, Optional

from fastapi import APIRouter, Depends, Query, status
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
from app.services import player_service
from app.utils.authorization import is_admin, require_player_access
from app.utils.error_handling import handle_service_error

router = APIRouter(tags=["players"])


def _create_player_info(db: Session, player: Player) -> PlayerInfo:
    """Convert Player model to PlayerInfo schema."""
    return PlayerInfo.model_validate(player)


@router.post("/", response_model=PlayerInfo, status_code=status.HTTP_201_CREATED)
def create_player(
    player: PlayerCreate,
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> PlayerInfo:
    """Create a new player."""
    try:
        db_player = player_service.create_player(
            db=db,
            name=player.name,
            dominant_hand=player.dominant_hand,
            user_id=current_user["id"],
            backhand_style=player.backhand_style,
            height_cm=player.height_cm,
            age_group=player.age_group,
            gender=player.gender,
            notes=player.notes,
        )

        return _create_player_info(db, db_player)
    except Exception as e:  # noqa: BLE001
        handle_service_error(e, "create_player", {})


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
        players = player_service.list_user_players(
            db=db,
            user_id=current_user["id"],
            is_admin=is_admin(current_user),
            name_filter=name,
            skip=skip,
            limit=limit,
        )

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
    except Exception as e:  # noqa: BLE001
        handle_service_error(e, "get_players", {"user_id": current_user["id"]})


@router.get("/me", response_model=PlayerInfo)
def get_my_player(
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> PlayerInfo:
    """Get the default player profile for the current user."""
    try:
        default_player = player_service.get_or_create_default_player(
            db, current_user["id"]
        )
        return _create_player_info(db, default_player)
    except Exception as e:  # noqa: BLE001
        handle_service_error(e, "get_my_player", {})


@router.put("/me", response_model=PlayerInfo)
def upsert_my_player(
    player_update: PlayerUpdate,
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> PlayerInfo:
    """Create or update the default player profile for the current user."""
    try:
        # Extract update data, filtering out None values
        update_data = player_update.model_dump(exclude_unset=True)
        if update_data.get("name") is None:
            update_data.pop("name", None)
        if update_data.get("dominant_hand") is None:
            update_data.pop("dominant_hand", None)

        # Get or create default player, passing provided data for initial creation
        # If name is not provided, use display_name from user metadata
        player_name = update_data.get("name")
        if not player_name:
            user_metadata = current_user.get("user_metadata", {})
            player_name = user_metadata.get("display_name")

        default_player = player_service.get_or_create_default_player(
            db,
            current_user["id"],
            name=player_name,
            dominant_hand=update_data.get("dominant_hand"),
            backhand_style=update_data.get("backhand_style"),
            height_cm=update_data.get("height_cm"),
            age_group=update_data.get("age_group"),
            gender=update_data.get("gender"),
            user_metadata=current_user.get("user_metadata"),
        )

        # If player already existed, update it with any new data
        if update_data:
            default_player = player_service.update_player(
                db, default_player.id, **update_data
            )

        return _create_player_info(db, default_player)
    except Exception as e:  # noqa: BLE001
        handle_service_error(e, "upsert_my_player", {})


@router.get("/{player_id}", response_model=PlayerInfo)
def get_player(
    player_id: int,
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> PlayerInfo:
    """Get a specific player by ID."""
    try:
        player = player_service.get_player_by_id(db, player_id)
        if not player:
            raise ValueError(f"Player with ID {player_id} not found")

        # Check authorization
        require_player_access(player, current_user)

        return _create_player_info(db, player)
    except Exception as e:  # noqa: BLE001
        handle_service_error(e, "get_player", {"player_id": player_id})


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
        player = player_service.get_player_by_id(db, player_id)
        if not player:
            raise ValueError(f"Player with ID {player_id} not found")

        # Check authorization (only owner can update)
        require_player_access(player, current_user)

        # Filter out None values for update
        update_data = player_update.model_dump(exclude_unset=True)
        if update_data.get("name") is None:
            update_data.pop("name", None)
        if update_data.get("dominant_hand") is None:
            update_data.pop("dominant_hand", None)

        if not update_data:
            # No fields to update, return current player
            pass
        else:
            player = player_service.update_player(db, player_id, **update_data)

        return _create_player_info(db, player)
    except Exception as e:  # noqa: BLE001
        handle_service_error(e, "update_player", {"player_id": player_id})


@router.delete("/{player_id}", response_model=PlayerDeleteResponse)
def delete_player(
    player_id: int,
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> PlayerDeleteResponse:
    """Delete a player."""
    try:
        # Get player first to check authorization
        player = player_service.get_player_by_id(db, player_id)
        if not player:
            raise ValueError(f"Player with ID {player_id} not found")

        # Check authorization (only owner can delete)
        require_player_access(player, current_user)

        player_service.delete_player(db, player_id)
        return PlayerDeleteResponse(message=f"Player {player_id} deleted successfully")
    except Exception as e:  # noqa: BLE001
        handle_service_error(e, "delete_player", {"player_id": player_id})
