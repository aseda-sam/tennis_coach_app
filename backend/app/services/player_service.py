"""Player service functions."""

import logging
from typing import List, Literal, Optional

from sqlalchemy.orm import Session

from app.models.player import Player

logger = logging.getLogger(__name__)

# Define allowed fields for Player updates
ALLOWED_PLAYER_FIELDS = {
    "name",
    "dominant_hand",
    "backhand_style",
    "height",
    "notes",
}


def create_player(
    db: Session,
    name: str,
    dominant_hand: Literal["left", "right"],
    backhand_style: Optional[Literal["one_handed", "two_handed"]] = None,
    height: Optional[float] = None,
    notes: Optional[str] = None,
) -> Player:
    """
    Create a new Player record in the database.

    Args:
        db (Session): SQLAlchemy database session.
        name (str): Player name.
        dominant_hand (Literal["left", "right"]): Dominant hand.
        backhand_style (Optional[Literal["one_handed", "two_handed"]]): Backhand style.
        height (Optional[float]): Height in cm.
        notes (Optional[str]): Additional notes.

    Returns:
        Player: The created Player database object.
    """
    # Check if player with same name already exists
    existing_player = db.query(Player).filter(Player.name == name).first()
    if existing_player:
        raise ValueError(f"Player with name '{name}' already exists")

    # Create new player
    db_player = Player(
        name=name,
        dominant_hand=dominant_hand,
        backhand_style=backhand_style,
        height=height,
        notes=notes,
    )
    db.add(db_player)
    db.commit()
    db.refresh(db_player)
    return db_player


def get_player_by_id(db: Session, player_id: int) -> Optional[Player]:
    """
    Retrieve a Player record by its ID.

    Args:
        db (Session): SQLAlchemy database session.
        player_id (int): ID of the Player record.

    Returns:
        Player: The Player record if found, else None.
    """
    return db.query(Player).filter(Player.id == player_id).first()


def get_players(
    db: Session,
    skip: int = 0,
    limit: int = 100,
    name_filter: Optional[str] = None,
) -> List[Player]:
    """
    Retrieve all Player records with optional filtering and pagination.

    Args:
        db (Session): SQLAlchemy database session.
        skip (int): Number of records to skip.
        limit (int): Maximum number of records to return.
        name_filter (Optional[str]): Filter by name (partial match).

    Returns:
        List[Player]: List of Player records.
    """
    query = db.query(Player)

    if name_filter:
        query = query.filter(Player.name.ilike(f"%{name_filter}%"))

    return query.offset(skip).limit(limit).all()


def update_player(db: Session, player_id: int, **updates: str | float | None) -> Player:
    """
    Update an existing Player record.

    Args:
        db (Session): SQLAlchemy database session.
        player_id (int): ID of the Player record to update.
        **updates (dict): Updated fields for the Player record.

    Returns:
        Player: The updated Player record.

    Raises:
        ValueError: If the Player record is not found or invalid fields
            are provided.
    """
    player = db.query(Player).filter(Player.id == player_id).first()
    if not player:
        raise ValueError(f"Player with ID {player_id} not found")

    # Validate that all update keys are allowed fields
    invalid_fields = set(updates.keys()) - ALLOWED_PLAYER_FIELDS
    if invalid_fields:
        raise ValueError(
            f"Invalid fields for update: {invalid_fields}. Allowed fields: {ALLOWED_PLAYER_FIELDS}"
        )

    # Check for name conflicts if name is being updated
    if "name" in updates and updates["name"] != player.name:
        existing_player = (
            db.query(Player).filter(Player.name == updates["name"]).first()
        )
        if existing_player:
            raise ValueError(f"Player with name '{updates['name']}' already exists")

    # Safely update only validated fields
    for key, value in updates.items():
        if key in ALLOWED_PLAYER_FIELDS:
            setattr(player, key, value)

    db.commit()
    db.refresh(player)
    return player


def delete_player(db: Session, player_id: int) -> None:
    """
    Delete a Player record by its ID.

    Args:
        db (Session): SQLAlchemy database session.
        player_id (int): ID of the Player record to delete.

    Raises:
        ValueError: If the Player record is not found.
    """
    # First check if the player exists
    player = db.query(Player).filter(Player.id == player_id).first()
    if not player:
        raise ValueError(f"Player with ID {player_id} not found")

    # Delete the player (ball contacts will have player_id set to NULL due to ondelete="SET NULL")
    db.delete(player)
    db.commit()
