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
    user_id: str,
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
        user_id (Optional[str]): UUID of the user who owns this player.

    Returns:
        Player: The created Player database object.
    """
    logger.info(
        f"Creating new player: name='{name}', dominant_hand='{dominant_hand}', user_id='{user_id}'"
    )

    # Validate user_id is provided (required)
    if not user_id:
        raise ValueError("user_id is required for player creation")

    # Check if player with same name already exists for this user
    # Note: Different users can have players with the same name
    query = db.query(Player).filter(Player.name == name, Player.user_id == user_id)
    existing_player = query.first()
    if existing_player:
        logger.warning(
            f"Player creation failed: player with name '{name}' already exists for user '{user_id}' (ID: {existing_player.id})"
        )
        raise ValueError(f"Player with name '{name}' already exists")

    # Create new player
    db_player = Player(
        name=name,
        dominant_hand=dominant_hand,
        backhand_style=backhand_style,
        height=height,
        notes=notes,
        user_id=user_id,
    )
    db.add(db_player)
    db.commit()
    db.refresh(db_player)

    logger.info(
        f"✅ Successfully created player: ID={db_player.id}, name='{name}', dominant_hand='{dominant_hand}', user_id='{user_id}'"
    )
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
    logger.debug(f"Retrieving player by ID: {player_id}")
    player = db.query(Player).filter(Player.id == player_id).first()

    if player:
        logger.debug(f"Found player: ID={player.id}, name='{player.name}'")
    else:
        logger.debug(f"Player not found: ID={player_id}")

    return player


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
    logger.debug(
        f"Retrieving players: skip={skip}, limit={limit}, name_filter='{name_filter}'"
    )

    query = db.query(Player)

    if name_filter:
        query = query.filter(Player.name.ilike(f"%{name_filter}%"))
        logger.debug(f"Applied name filter: '{name_filter}'")

    players = query.offset(skip).limit(limit).all()
    logger.debug(f"Retrieved {len(players)} players")

    return players


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
    logger.info(f"Updating player ID={player_id} with fields: {list(updates.keys())}")

    player = db.query(Player).filter(Player.id == player_id).first()
    if not player:
        logger.warning(f"Player update failed: player with ID {player_id} not found")
        raise ValueError(f"Player with ID {player_id} not found")

    # Validate that all update keys are allowed fields
    invalid_fields = set(updates.keys()) - ALLOWED_PLAYER_FIELDS
    if invalid_fields:
        logger.warning(
            f"Player update failed: invalid fields {invalid_fields} for player ID {player_id}"
        )
        raise ValueError(
            f"Invalid fields for update: {invalid_fields}. Allowed fields: {ALLOWED_PLAYER_FIELDS}"
        )

    # Check for name conflicts if name is being updated
    if "name" in updates and updates["name"] != player.name:
        existing_player = (
            db.query(Player).filter(Player.name == updates["name"]).first()
        )
        if existing_player:
            logger.warning(
                f"Player update failed: name conflict - player with name '{updates['name']}' already exists (ID: {existing_player.id})"
            )
            raise ValueError(f"Player with name '{updates['name']}' already exists")

    # Safely update only validated fields
    updated_fields = []
    for key, value in updates.items():
        if key in ALLOWED_PLAYER_FIELDS:
            old_value = getattr(player, key)
            setattr(player, key, value)
            updated_fields.append(f"{key}: '{old_value}' -> '{value}'")

    db.commit()
    db.refresh(player)

    logger.info(
        f"✅ Successfully updated player ID={player_id}: {', '.join(updated_fields)}"
    )
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
    logger.info(f"Deleting player ID={player_id}")

    # First check if the player exists
    player = db.query(Player).filter(Player.id == player_id).first()
    if not player:
        logger.warning(f"Player deletion failed: player with ID {player_id} not found")
        raise ValueError(f"Player with ID {player_id} not found")

    # Log player details before deletion
    logger.info(
        f"Deleting player: ID={player.id}, name='{player.name}', dominant_hand='{player.dominant_hand}'"
    )

    # Delete the player (ball contacts will have player_id set to NULL due to ondelete="SET NULL")
    db.delete(player)
    db.commit()

    logger.info(f"✅ Successfully deleted player ID={player_id} (name='{player.name}')")


def get_or_create_default_player(db: Session, user_id: str) -> Player:
    """
    Get or create the default "Me" player for a user.

    Creates a player named "Me" (or user's name if available) owned by user_id.
    This becomes the default selection for serve attempt tagging.

    Args:
        db: Database session
        user_id: User ID (UUID string)

    Returns:
        Player: The default player for this user
    """
    # Check for existing default player
    default_player = db.query(Player).filter(
        Player.user_id == user_id,
        Player.name.in_(["Me", "Default"])  # Flexible naming
    ).first()

    if default_player:
        logger.debug(f"Found existing default player for user {user_id}: ID={default_player.id}")
        return default_player

    # Create new default player
    logger.info(f"Creating default player 'Me' for user {user_id}")
    default_player = Player(
        name="Me",
        dominant_hand="right",  # Default, user can update later
        user_id=user_id
    )
    db.add(default_player)
    db.commit()
    db.refresh(default_player)
    logger.info(f"✅ Created default player for user {user_id}: ID={default_player.id}")
    return default_player
