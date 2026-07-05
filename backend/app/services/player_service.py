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
    "height_cm",
    "age_group",
    "gender",
    "notes",
}

OTHER_PLAYER_NAME = "Someone Else"


def create_player(
    db: Session,
    name: str,
    dominant_hand: Literal["left", "right"],
    user_id: str,
    backhand_style: Optional[Literal["one_handed", "two_handed"]] = None,
    height_cm: Optional[float] = None,
    age_group: Optional[str] = None,
    gender: Optional[str] = None,
    notes: Optional[str] = None,
) -> Player:
    """
    Create a new Player record in the database.

    Args:
        db (Session): SQLAlchemy database session.
        name (str): Player name.
        dominant_hand (Literal["left", "right"]): Dominant hand.
        backhand_style (Optional[Literal["one_handed", "two_handed"]]): Backhand style.
        height_cm (Optional[float]): Height in cm.
        age_group (Optional[str]): Age group.
        gender (Optional[str]): Gender identity.
        notes (Optional[str]): Additional notes.
        user_id (Optional[str]): UUID of the user who owns this player.

    Returns:
        Player: The created Player database object.
    """
    logger.info(
        "Creating new player: name='%s', dominant_hand='%s', user_id='%s'",
        name,
        dominant_hand,
        user_id,
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
            "Player creation failed: player with name '%s' already exists for user '%s' (ID: %s)",
            name,
            user_id,
            existing_player.id,
        )
        raise ValueError(f"Player with name '{name}' already exists")

    # Create new player
    db_player = Player(
        name=name,
        dominant_hand=dominant_hand,
        backhand_style=backhand_style,
        height_cm=height_cm,
        age_group=age_group,
        gender=gender,
        notes=notes,
        user_id=user_id,
    )
    db.add(db_player)
    db.commit()
    db.refresh(db_player)

    logger.info(
        "✅ Successfully created player: ID=%s, name='%s', dominant_hand='%s', user_id='%s'",
        db_player.id,
        name,
        dominant_hand,
        user_id,
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
    logger.debug("Retrieving player by ID: %s", player_id)
    player = db.query(Player).filter(Player.id == player_id).first()

    if player:
        logger.debug("Found player: ID=%s, name='%s'", player.id, player.name)
    else:
        logger.debug("Player not found: ID=%s", player_id)

    return player


def list_user_players(
    db: Session,
    user_id: str,
    is_admin: bool = False,
    name_filter: Optional[str] = None,
    skip: int = 0,
    limit: int = 100,
) -> List[Player]:
    """List players for a user with optional filtering and pagination.

    Args:
        db: Database session
        user_id: User ID to filter by (if not admin)
        is_admin: Whether the user is an admin (admins can see all players)
        name_filter: Optional name filter (partial match, case-insensitive)
        skip: Number of records to skip
        limit: Maximum number of records to return

    Returns:
        List of Player instances
    """
    query = db.query(Player)

    # Filter by user_id unless admin
    if not is_admin:
        query = query.filter(Player.user_id == user_id)

    # Apply name filter if provided
    if name_filter:
        query = query.filter(Player.name.ilike(f"%{name_filter}%"))

    return query.offset(skip).limit(limit).all()


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
        "Retrieving players: skip=%s, limit=%s, name_filter='%s'",
        skip,
        limit,
        name_filter,
    )

    query = db.query(Player)

    if name_filter:
        query = query.filter(Player.name.ilike(f"%{name_filter}%"))
        logger.debug("Applied name filter: '%s'", name_filter)

    players = query.offset(skip).limit(limit).all()
    logger.debug("Retrieved %s players", len(players))

    return players


def update_player(
    db: Session, player_id: int, **updates: str | float | int | None
) -> Player:
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
    logger.info(
        "Updating player ID=%s with fields: %s", player_id, list(updates.keys())
    )

    player = db.query(Player).filter(Player.id == player_id).first()
    if not player:
        logger.warning("Player update failed: player with ID %s not found", player_id)
        raise ValueError(f"Player with ID {player_id} not found")

    # Validate that all update keys are allowed fields
    invalid_fields = set(updates.keys()) - ALLOWED_PLAYER_FIELDS
    if invalid_fields:
        logger.warning(
            "Player update failed: invalid fields %s for player ID %s",
            invalid_fields,
            player_id,
        )
        raise ValueError(
            f"Invalid fields for update: {invalid_fields}. Allowed fields: {ALLOWED_PLAYER_FIELDS}"
        )

    # Check for name conflicts if name is being updated (per-user, not global)
    if "name" in updates and updates["name"] != player.name:
        existing_player = (
            db.query(Player)
            .filter(
                Player.name == updates["name"],
                Player.user_id == player.user_id,  # Only check within same user
            )
            .first()
        )
        if existing_player:
            logger.warning(
                "Player update failed: name conflict - player with name '%s' already exists for user %s (ID: %s)",
                updates["name"],
                player.user_id,
                existing_player.id,
            )
            raise ValueError(
                f"Player with name '{updates['name']}' already exists for this user"
            )

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
        "✅ Successfully updated player ID=%s: %s", player_id, ", ".join(updated_fields)
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
    logger.info("Deleting player ID=%s", player_id)

    # First check if the player exists
    player = db.query(Player).filter(Player.id == player_id).first()
    if not player:
        logger.warning("Player deletion failed: player with ID %s not found", player_id)
        raise ValueError(f"Player with ID {player_id} not found")

    # Log player details before deletion
    logger.info(
        "Deleting player: ID=%s, name='%s', dominant_hand='%s'",
        player.id,
        player.name,
        player.dominant_hand,
    )

    # Delete the player (ball contacts will have player_id set to NULL due to ondelete="SET NULL")
    db.delete(player)
    db.commit()

    logger.info(
        "✅ Successfully deleted player ID=%s (name='%s')", player_id, player.name
    )


def get_or_create_default_player(
    db: Session,
    user_id: str,
    name: Optional[str] = None,
    dominant_hand: Optional[Literal["left", "right"]] = None,
    backhand_style: Optional[Literal["one_handed", "two_handed"]] = None,
    height_cm: Optional[float] = None,
    age_group: Optional[str] = None,
    gender: Optional[str] = None,
    user_metadata: Optional[dict] = None,
) -> Player:
    """
    Get or create the default player for a user.

    If a default player doesn't exist, creates one with the provided data.
    If name is not provided, uses "Me" as fallback.
    This becomes the default selection for serve window tagging.

    Args:
        db: Database session
        user_id: User ID (UUID string)
        name: Optional player name (defaults to "Me" if not provided)
        dominant_hand: Optional dominant hand (defaults to "right" if not provided)
        backhand_style: Optional backhand style
        height_cm: Optional height in centimeters
        age_group: Optional age group
        gender: Optional gender identity

    Returns:
        Player: The default player for this user
    """
    # The owner's player is identified by the is_self flag, never by
    # creation order (a "someone else" player may predate the owner's own).
    default_player = (
        db.query(Player)
        .filter(Player.user_id == user_id, Player.is_self.is_(True))
        .first()
    )

    if default_player is None:
        # Legacy data: players exist but none is flagged. Adopt the earliest
        # (matching the old creation-order behaviour) and persist the flag.
        legacy_player = (
            db.query(Player)
            .filter(Player.user_id == user_id, Player.name != OTHER_PLAYER_NAME)
            .order_by(Player.created_at.asc())
            .first()
        )
        if legacy_player:
            logger.info(
                "Adopting earliest player as self for user %s: ID=%s, name='%s'",
                user_id,
                legacy_player.id,
                legacy_player.name,
            )
            legacy_player.is_self = True
            db.commit()
            db.refresh(legacy_player)
            default_player = legacy_player

    if default_player:
        logger.debug(
            "Found existing default player for user %s: ID=%s, name='%s'",
            user_id,
            default_player.id,
            default_player.name,
        )
        # Update it if new data provided
        if name and name != default_player.name:
            logger.info(
                "Updating default player name from '%s' to '%s'",
                default_player.name,
                name,
            )
            default_player.name = name
        if dominant_hand and dominant_hand != default_player.dominant_hand:
            default_player.dominant_hand = dominant_hand
        if backhand_style is not None:
            default_player.backhand_style = backhand_style
        if height_cm is not None:
            default_player.height_cm = height_cm
        if age_group is not None:
            default_player.age_group = age_group
        if gender is not None:
            default_player.gender = gender
        db.commit()
        db.refresh(default_player)
        return default_player

    # Create new default player with provided data or defaults
    # Priority: provided name > display_name from metadata > "Me"
    if not name and user_metadata:
        name = user_metadata.get("display_name")
    player_name = name or "Me"
    player_dominant_hand = dominant_hand or "right"
    logger.info(
        "Creating default player '%s' for user %s (dominant_hand=%s)",
        player_name,
        user_id,
        player_dominant_hand,
    )
    default_player = Player(
        name=player_name,
        dominant_hand=player_dominant_hand,
        backhand_style=backhand_style,
        height_cm=height_cm,
        age_group=age_group,
        gender=gender,
        user_id=user_id,
        is_self=True,
    )
    db.add(default_player)
    db.commit()
    db.refresh(default_player)
    logger.info(
        "✅ Created default player for user %s: ID=%s, name='%s'",
        user_id,
        default_player.id,
        player_name,
    )
    return default_player


def get_or_create_other_player(db: Session, user_id: str) -> Player:
    """
    Get or create a dedicated "Someone Else" player for a user.

    This is used as the default attribution for videos tagged as "Someone Else"
    without overwriting the user's primary profile.
    """
    other_player = (
        db.query(Player)
        .filter(Player.user_id == user_id, Player.name == OTHER_PLAYER_NAME)
        .first()
    )
    if other_player:
        return other_player

    return create_player(
        db=db,
        name=OTHER_PLAYER_NAME,
        dominant_hand="right",
        user_id=user_id,
    )
