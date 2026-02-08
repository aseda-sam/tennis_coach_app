"""Service for serve attempt operations."""

import logging
from datetime import datetime
from typing import List, Optional

from sqlalchemy.orm import Session

from app.api.schemas.serve_attempt import ServeAttemptCreate, ServeAttemptUpdate
from app.core.shot_types import SERVE_SUBTYPES, is_valid_serve_subtype
from app.models.player import Player
from app.models.serve_attempt import ServeAttempt
from app.services import player_service, video_service

logger = logging.getLogger(__name__)


def validate_serve_attempt_timestamps(
    start_timestamp: float,
    end_timestamp: float,
    contact_timestamp: Optional[float] = None,
) -> None:
    """Validate serve attempt timestamps.

    Args:
        start_timestamp: Start timestamp
        end_timestamp: End timestamp
        contact_timestamp: Optional contact timestamp

    Raises:
        ValueError: If timestamps are invalid
    """
    if start_timestamp >= end_timestamp:
        raise ValueError("start_timestamp must be less than end_timestamp")

    if contact_timestamp is not None and (
        contact_timestamp < start_timestamp or contact_timestamp > end_timestamp
    ):
        raise ValueError(
            "contact_timestamp must be between start_timestamp and end_timestamp"
        )


def validate_serve_subtype(serve_subtype: Optional[str]) -> None:
    """Validate serve subtype.

    Args:
        serve_subtype: Serve subtype to validate

    Raises:
        ValueError: If serve subtype is invalid
    """
    if serve_subtype and not is_valid_serve_subtype(serve_subtype):
        raise ValueError(
            f"Invalid serve_subtype: {serve_subtype}. "
            f"Valid options: {', '.join(SERVE_SUBTYPES)}"
        )


def validate_player_ownership(
    db: Session,
    player_id: int,
    user_id: str,
) -> Player:
    """Validate that a player exists and belongs to the user.

    Args:
        db: Database session
        player_id: Player ID to validate
        user_id: User ID to check ownership

    Returns:
        Player instance

    Raises:
        ValueError: If player not found or access denied
    """
    player = db.query(Player).filter(Player.id == player_id).first()
    if not player or player.user_id != user_id:
        raise ValueError("Player not found or access denied")
    return player


def create_serve_attempt(
    db: Session,
    serve_attempt_data: ServeAttemptCreate,
    user_id: str,
) -> ServeAttempt:
    """Create a new serve attempt.

    Args:
        db: Database session
        serve_attempt_data: Serve attempt creation data
        user_id: User ID creating the serve attempt

    Returns:
        Created ServeAttempt instance

    Raises:
        ValueError: If video not found, timestamps invalid, or player access denied
    """
    # Get video to check it exists
    video = video_service.get_video_by_id(db, serve_attempt_data.video_id)
    if not video:
        raise ValueError(f"Video with ID {serve_attempt_data.video_id} not found")

    # Validate timestamps
    validate_serve_attempt_timestamps(
        serve_attempt_data.start_timestamp,
        serve_attempt_data.end_timestamp,
        serve_attempt_data.contact_timestamp,
    )

    # Validate serve subtype
    validate_serve_subtype(serve_attempt_data.serve_subtype)

    # Auto-assign default player if not provided
    player_id = serve_attempt_data.player_id
    if not player_id:
        if video.primary_player_id:
            player_id = video.primary_player_id
            logger.debug(
                "Auto-assigned video primary player %s for serve attempt", player_id
            )
        else:
            default_player = player_service.get_or_create_default_player(db, user_id)
            player_id = default_player.id
            logger.debug("Auto-assigned default player %s for serve attempt", player_id)

    # Validate player ownership
    validate_player_ownership(db, player_id, user_id)

    # Create serve attempt
    db_serve_attempt = ServeAttempt(
        video_id=serve_attempt_data.video_id,
        user_id=user_id,
        player_id=player_id,
        start_timestamp=serve_attempt_data.start_timestamp,
        end_timestamp=serve_attempt_data.end_timestamp,
        contact_timestamp=serve_attempt_data.contact_timestamp,
        court_side=serve_attempt_data.court_side,
        serve_number=serve_attempt_data.serve_number,
        serve_subtype=serve_attempt_data.serve_subtype,
        in_out=serve_attempt_data.in_out,
    )
    db.add(db_serve_attempt)
    db.commit()
    db.refresh(db_serve_attempt)

    logger.info(
        f"Created serve attempt {db_serve_attempt.id} for video {serve_attempt_data.video_id}"
    )

    return db_serve_attempt


def get_serve_attempt_by_id(
    db: Session,
    serve_attempt_id: int,
    user_id: str,
) -> ServeAttempt:
    """Get a serve attempt by ID with authorization check.

    Args:
        db: Database session
        serve_attempt_id: Serve attempt ID
        user_id: User ID for authorization

    Returns:
        ServeAttempt instance

    Raises:
        ValueError: If serve attempt not found or access denied
    """
    serve_attempt = (
        db.query(ServeAttempt).filter(ServeAttempt.id == serve_attempt_id).first()
    )

    if not serve_attempt:
        raise ValueError(f"Serve attempt with ID {serve_attempt_id} not found")

    if serve_attempt.user_id != user_id:
        raise ValueError("Access denied")

    return serve_attempt


def update_serve_attempt(
    db: Session,
    serve_attempt_id: int,
    updates: ServeAttemptUpdate,
    user_id: str,
) -> ServeAttempt:
    """Update a serve attempt.

    Args:
        db: Database session
        serve_attempt_id: Serve attempt ID to update
        updates: Update data
        user_id: User ID for authorization

    Returns:
        Updated ServeAttempt instance

    Raises:
        ValueError: If serve attempt not found, access denied, or validation fails
    """
    serve_attempt = get_serve_attempt_by_id(db, serve_attempt_id, user_id)

    # Validate player ownership if player_id is being updated
    if updates.player_id is not None:
        validate_player_ownership(db, updates.player_id, user_id)

    # Validate timestamps if being updated
    start_ts = (
        updates.start_timestamp
        if updates.start_timestamp is not None
        else serve_attempt.start_timestamp
    )
    end_ts = (
        updates.end_timestamp
        if updates.end_timestamp is not None
        else serve_attempt.end_timestamp
    )
    contact_ts = (
        updates.contact_timestamp
        if updates.contact_timestamp is not None
        else serve_attempt.contact_timestamp
    )

    validate_serve_attempt_timestamps(start_ts, end_ts, contact_ts)

    # Validate serve subtype if being updated
    if updates.serve_subtype is not None:
        validate_serve_subtype(updates.serve_subtype)

    # Update fields
    update_dict = updates.model_dump(exclude_unset=True)
    for key, value in update_dict.items():
        setattr(serve_attempt, key, value)

    db.commit()
    db.refresh(serve_attempt)

    logger.info("Updated serve attempt %s", serve_attempt_id)

    return serve_attempt


def delete_serve_attempt(
    db: Session,
    serve_attempt_id: int,
    user_id: str,
) -> None:
    """Delete a serve attempt.

    Args:
        db: Database session
        serve_attempt_id: Serve attempt ID to delete
        user_id: User ID for authorization

    Raises:
        ValueError: If serve attempt not found or access denied
    """
    serve_attempt = get_serve_attempt_by_id(db, serve_attempt_id, user_id)

    db.delete(serve_attempt)
    db.commit()

    logger.info("Deleted serve attempt %s", serve_attempt_id)


def list_user_serve_attempts(
    db: Session,
    user_id: str,
    player_id: Optional[int] = None,
    court_side: Optional[str] = None,
    start_date: Optional[datetime] = None,
    end_date: Optional[datetime] = None,
    video_id: Optional[int] = None,
) -> List[ServeAttempt]:
    """List serve attempts for a user with optional filters.

    Args:
        db: Database session
        user_id: User ID to filter by
        player_id: Optional player ID filter (validates ownership)
        court_side: Optional court side filter
        start_date: Optional start date filter
        end_date: Optional end date filter
        video_id: Optional video ID filter

    Returns:
        List of ServeAttempt instances ordered by creation date (newest first)

    Raises:
        ValueError: If player_id provided but player not found or access denied
    """
    query = db.query(ServeAttempt).filter(ServeAttempt.user_id == user_id)

    # Apply filters
    if player_id is not None:
        # Validate player ownership
        validate_player_ownership(db, player_id, user_id)
        query = query.filter(ServeAttempt.player_id == player_id)

    if court_side is not None:
        query = query.filter(ServeAttempt.court_side == court_side)

    if video_id is not None:
        query = query.filter(ServeAttempt.video_id == video_id)

    if start_date is not None:
        query = query.filter(ServeAttempt.created_at >= start_date)

    if end_date is not None:
        query = query.filter(ServeAttempt.created_at <= end_date)

    # Order by creation date (newest first)
    return query.order_by(ServeAttempt.created_at.desc()).all()


def reassign_video_serve_attempts(
    db: Session,
    video_id: int,
    user_id: str,
    player_id: int,
) -> int:
    """Reassign all serve attempts for a video to a new player."""
    validate_player_ownership(db, player_id, user_id)
    updated_count = (
        db.query(ServeAttempt)
        .filter(
            ServeAttempt.video_id == video_id,
            ServeAttempt.user_id == user_id,
        )
        .update({ServeAttempt.player_id: player_id}, synchronize_session=False)
    )
    db.commit()
    return updated_count


def get_serve_attempts_for_video(
    db: Session,
    video_id: int,
) -> List[ServeAttempt]:
    """Get all serve attempts for a video.

    Args:
        db: Database session
        video_id: Video ID

    Returns:
        List of ServeAttempt instances for the video
    """
    return db.query(ServeAttempt).filter(ServeAttempt.video_id == video_id).all()


def get_ball_contact_timestamps(
    db: Session,
    video_id: int,
    user_id: str,
) -> List[float]:
    """Get all ball contact timestamps for serves in a video.

    Returns sorted, unique ball contact timestamps from serve attempts that have a contact point.

    Args:
        db: Database session
        video_id: Video ID
        user_id: User ID to filter by

    Returns:
        Sorted list of unique contact timestamps
    """
    rows = (
        db.query(ServeAttempt.contact_timestamp)
        .filter(
            ServeAttempt.video_id == video_id,
            ServeAttempt.user_id == user_id,
            ServeAttempt.contact_timestamp.isnot(None),
        )
        .all()
    )
    timestamps = sorted({r[0] for r in rows if r[0] is not None})
    return timestamps
