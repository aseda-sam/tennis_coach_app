"""Service for serve window operations."""

import logging
from datetime import datetime
from typing import List, Optional, Tuple

from sqlalchemy.orm import Session

from app.api.schemas.serve_window import ServeWindowCreate, ServeWindowUpdate
from app.core.shot_types import SERVE_SUBTYPES, is_valid_serve_subtype
from app.models.player import Player
from app.models.serve_window import ServeWindow
from app.services import player_service, video_service

logger = logging.getLogger(__name__)

VISIBLE_STATUSES = ("accepted", "edited")


def validate_serve_window_timestamps(
    start_timestamp: float,
    end_timestamp: float,
    contact_timestamp: Optional[float] = None,
) -> None:
    """Validate serve window timestamps.

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


def create_serve_window(
    db: Session,
    serve_window_data: ServeWindowCreate,
    user_id: str,
) -> ServeWindow:
    """Create a new serve window.

    Args:
        db: Database session
        serve_window_data: Serve window creation data
        user_id: User ID creating the serve window

    Returns:
        Created ServeWindow instance

    Raises:
        ValueError: If video not found, timestamps invalid, or player access denied
    """
    # Get video to check it exists
    video = video_service.get_video_by_id(db, serve_window_data.video_id)
    if not video:
        raise ValueError(f"Video with ID {serve_window_data.video_id} not found")

    # Validate timestamps
    validate_serve_window_timestamps(
        serve_window_data.start_timestamp,
        serve_window_data.end_timestamp,
        serve_window_data.contact_timestamp,
    )

    # Validate serve subtype
    validate_serve_subtype(serve_window_data.serve_subtype)

    # Auto-assign default player if not provided
    player_id = serve_window_data.player_id
    if not player_id:
        if video.primary_player_id:
            player_id = video.primary_player_id
            logger.debug(
                "Auto-assigned video primary player %s for serve window", player_id
            )
        else:
            default_player = player_service.get_or_create_default_player(db, user_id)
            player_id = default_player.id
            logger.debug("Auto-assigned default player %s for serve window", player_id)

    # Validate player ownership
    validate_player_ownership(db, player_id, user_id)

    # Create serve window
    db_serve_window = ServeWindow(
        video_id=serve_window_data.video_id,
        user_id=user_id,
        player_id=player_id,
        start_timestamp=serve_window_data.start_timestamp,
        end_timestamp=serve_window_data.end_timestamp,
        contact_timestamp=serve_window_data.contact_timestamp,
        contact_source="manual"
        if serve_window_data.contact_timestamp is not None
        else None,
        court_side=serve_window_data.court_side,
        serve_number=serve_window_data.serve_number,
        serve_subtype=serve_window_data.serve_subtype,
        in_out=serve_window_data.in_out,
        source="manual",
        status="accepted",
        reviewed_at=datetime.utcnow(),
    )
    db.add(db_serve_window)
    db.commit()
    db.refresh(db_serve_window)

    logger.info(
        f"Created serve window {db_serve_window.id} for video {serve_window_data.video_id}"
    )

    return db_serve_window


def get_serve_window_by_id_no_auth(
    db: Session,
    serve_window_id: int,
) -> ServeWindow:
    """Get a serve window by ID without authorization check.

    Used when authorization is handled at the route level (e.g., demo-aware endpoints
    that check video-level access instead of user_id ownership).

    Args:
        db: Database session
        serve_window_id: Serve window ID

    Returns:
        ServeWindow instance

    Raises:
        ValueError: If serve window not found
    """
    serve_window = (
        db.query(ServeWindow).filter(ServeWindow.id == serve_window_id).first()
    )

    if not serve_window:
        raise ValueError(f"Serve window with ID {serve_window_id} not found")

    return serve_window


def get_serve_window_by_id(
    db: Session,
    serve_window_id: int,
    user_id: str,
) -> ServeWindow:
    """Get a serve window by ID with authorization check.

    Args:
        db: Database session
        serve_window_id: Serve window ID
        user_id: User ID for authorization

    Returns:
        ServeWindow instance

    Raises:
        ValueError: If serve window not found or access denied
    """
    serve_window = (
        db.query(ServeWindow).filter(ServeWindow.id == serve_window_id).first()
    )

    if not serve_window:
        raise ValueError(f"Serve window with ID {serve_window_id} not found")

    if serve_window.user_id != user_id:
        raise ValueError("Access denied")

    return serve_window


def update_serve_window(
    db: Session,
    serve_window_id: int,
    updates: ServeWindowUpdate,
    user_id: str,
) -> ServeWindow:
    """Update a serve window.

    Args:
        db: Database session
        serve_window_id: Serve window ID to update
        updates: Update data
        user_id: User ID for authorization

    Returns:
        Updated ServeWindow instance

    Raises:
        ValueError: If serve window not found, access denied, or validation fails
    """
    serve_window = get_serve_window_by_id(db, serve_window_id, user_id)

    # Validate player ownership if player_id is being updated
    if updates.player_id is not None:
        validate_player_ownership(db, updates.player_id, user_id)

    # Validate timestamps if being updated
    start_ts = (
        updates.start_timestamp
        if updates.start_timestamp is not None
        else serve_window.start_timestamp
    )
    end_ts = (
        updates.end_timestamp
        if updates.end_timestamp is not None
        else serve_window.end_timestamp
    )
    contact_ts = (
        updates.contact_timestamp
        if updates.contact_timestamp is not None
        else serve_window.contact_timestamp
    )

    validate_serve_window_timestamps(start_ts, end_ts, contact_ts)

    # Minimum duration guard
    if end_ts - start_ts < 0.5:
        raise ValueError("Window must be at least 0.5 seconds long")

    # Validate serve subtype if being updated
    if updates.serve_subtype is not None:
        validate_serve_subtype(updates.serve_subtype)

    # Check for overlap with sibling windows (if timestamps are changing)
    timestamps_changing = (
        updates.start_timestamp is not None or updates.end_timestamp is not None
    )
    if timestamps_changing:
        overlapping = (
            db.query(ServeWindow)
            .filter(
                ServeWindow.video_id == serve_window.video_id,
                ServeWindow.is_active.is_(True),
                ServeWindow.id != serve_window_id,
                ServeWindow.start_timestamp < end_ts,
                ServeWindow.end_timestamp > start_ts,
            )
            .first()
        )
        if overlapping:
            raise ValueError(
                "Updated window would overlap with an existing serve window"
            )

    # Update fields
    update_dict = updates.model_dump(exclude_unset=True)

    # Preserve original timestamps on first timing edit and set status
    if timestamps_changing:
        if serve_window.original_start_timestamp is None:
            serve_window.original_start_timestamp = serve_window.start_timestamp
        if serve_window.original_end_timestamp is None:
            serve_window.original_end_timestamp = serve_window.end_timestamp
        serve_window.status = "edited"
        serve_window.reviewed_at = datetime.utcnow()

    for key, value in update_dict.items():
        setattr(serve_window, key, value)

    # Track that contact_timestamp was set manually
    if (
        "contact_timestamp" in update_dict
        and update_dict["contact_timestamp"] is not None
    ):
        serve_window.contact_source = "manual"

    db.commit()
    db.refresh(serve_window)

    logger.info("Updated serve window %s", serve_window_id)

    return serve_window


def delete_serve_window(
    db: Session,
    serve_window_id: int,
    user_id: str,
) -> None:
    """Delete a serve window.

    Args:
        db: Database session
        serve_window_id: Serve window ID to delete
        user_id: User ID for authorization

    Raises:
        ValueError: If serve window not found or access denied
    """
    serve_window = get_serve_window_by_id(db, serve_window_id, user_id)

    db.delete(serve_window)
    db.commit()

    logger.info("Deleted serve window %s", serve_window_id)


def list_user_serve_windows(
    db: Session,
    user_id: str,
    player_id: Optional[int] = None,
    court_side: Optional[str] = None,
    start_date: Optional[datetime] = None,
    end_date: Optional[datetime] = None,
    video_id: Optional[int] = None,
) -> List[ServeWindow]:
    """List serve windows for a user with optional filters.

    Args:
        db: Database session
        user_id: User ID to filter by
        player_id: Optional player ID filter (validates ownership)
        court_side: Optional court side filter
        start_date: Optional start date filter
        end_date: Optional end date filter
        video_id: Optional video ID filter

    Returns:
        List of ServeWindow instances ordered by creation date (newest first)

    Raises:
        ValueError: If player_id provided but player not found or access denied
    """
    query = db.query(ServeWindow).filter(
        ServeWindow.user_id == user_id,
        ServeWindow.is_active.is_(True),
    )

    # Apply filters
    if player_id is not None:
        # Validate player ownership
        validate_player_ownership(db, player_id, user_id)
        query = query.filter(ServeWindow.player_id == player_id)

    if court_side is not None:
        query = query.filter(ServeWindow.court_side == court_side)

    if video_id is not None:
        query = query.filter(ServeWindow.video_id == video_id)

    if start_date is not None:
        query = query.filter(ServeWindow.created_at >= start_date)

    if end_date is not None:
        query = query.filter(ServeWindow.created_at <= end_date)

    # Order by creation date (newest first)
    return query.order_by(ServeWindow.created_at.desc()).all()


def reassign_video_serve_windows(
    db: Session,
    video_id: int,
    user_id: str,
    player_id: int,
) -> int:
    """Reassign all serve windows for a video to a new player."""
    validate_player_ownership(db, player_id, user_id)
    updated_count = (
        db.query(ServeWindow)
        .filter(
            ServeWindow.video_id == video_id,
            ServeWindow.user_id == user_id,
        )
        .update({ServeWindow.player_id: player_id}, synchronize_session=False)
    )
    db.commit()
    return updated_count


def get_serve_windows_for_video(
    db: Session,
    video_id: int,
) -> List[ServeWindow]:
    """Get all serve windows for a video.

    Args:
        db: Database session
        video_id: Video ID

    Returns:
        List of ServeWindow instances for the video
    """
    return (
        db.query(ServeWindow)
        .filter(
            ServeWindow.video_id == video_id,
            ServeWindow.is_active.is_(True),
        )
        .all()
    )


def list_serve_windows_by_video(
    db: Session,
    video_id: int,
) -> List[ServeWindow]:
    """List visible serve windows for a video (no user_id filter).

    Used by the public demo endpoint where there is no authenticated user.
    Filters by video_id, is_active, and visible statuses only.

    Args:
        db: Database session
        video_id: Video ID

    Returns:
        List of ServeWindow instances ordered by creation date (newest first)
    """
    return (
        db.query(ServeWindow)
        .filter(
            ServeWindow.video_id == video_id,
            ServeWindow.is_active.is_(True),
            ServeWindow.status.in_(VISIBLE_STATUSES),
        )
        .order_by(ServeWindow.created_at.desc())
        .all()
    )


def split_serve_window(
    db: Session,
    serve_window_id: int,
    split_at: float,
    user_id: str,
) -> Tuple[ServeWindow, ServeWindow]:
    """Split a serve window into two at split_at timestamp.

    Args:
        db: Database session
        serve_window_id: Serve window ID to split
        split_at: Timestamp to split at (must be strictly inside window bounds)
        user_id: User ID for authorization

    Returns:
        Tuple of (child_a, child_b) where child_a covers [start, split_at]
        and child_b covers [split_at, end]

    Raises:
        ValueError: If split_at is not strictly inside window or either half < 0.5s
    """
    original = get_serve_window_by_id(db, serve_window_id, user_id)

    if not (original.start_timestamp < split_at < original.end_timestamp):
        raise ValueError(
            "split_at must be strictly inside the window (start_timestamp, end_timestamp)"
        )

    if split_at - original.start_timestamp < 0.5:
        raise ValueError("First half must be at least 0.5 seconds long")
    if original.end_timestamp - split_at < 0.5:
        raise ValueError("Second half must be at least 0.5 seconds long")

    # Assign contact_timestamp to whichever child contains it
    contact_a: Optional[float] = None
    contact_b: Optional[float] = None
    contact_source_a: Optional[str] = None
    contact_source_b: Optional[str] = None
    if original.contact_timestamp is not None:
        if original.contact_timestamp <= split_at:
            contact_a = original.contact_timestamp
            contact_source_a = original.contact_source
        else:
            contact_b = original.contact_timestamp
            contact_source_b = original.contact_source

    # Deactivate original in-place
    original.is_active = False
    original.status = "edited"
    original.reviewed_at = datetime.utcnow()

    shared_meta = {
        "video_id": original.video_id,
        "user_id": original.user_id,
        "player_id": original.player_id,
        "parent_window_id": original.id,
        "status": "accepted",
        "source": "manual",
        "is_active": True,
        "court_side": original.court_side,
        "serve_number": original.serve_number,
        "serve_subtype": original.serve_subtype,
        "in_out": original.in_out,
        "reviewed_at": datetime.utcnow(),
    }

    child_a = ServeWindow(
        start_timestamp=original.start_timestamp,
        end_timestamp=split_at,
        contact_timestamp=contact_a,
        contact_source=contact_source_a,
        **shared_meta,
    )
    child_b = ServeWindow(
        start_timestamp=split_at,
        end_timestamp=original.end_timestamp,
        contact_timestamp=contact_b,
        contact_source=contact_source_b,
        **shared_meta,
    )

    db.add(child_a)
    db.add(child_b)
    db.commit()
    db.refresh(child_a)
    db.refresh(child_b)

    logger.info(
        "Split serve window %s into %s and %s at %.2f",
        serve_window_id,
        child_a.id,
        child_b.id,
        split_at,
    )

    return child_a, child_b


def get_ball_contact_timestamps(
    db: Session,
    video_id: int,
    user_id: str,
) -> List[float]:
    """Get all ball contact timestamps for serves in a video.

    Returns sorted, unique ball contact timestamps from serve windows that have a contact point.

    Args:
        db: Database session
        video_id: Video ID
        user_id: User ID to filter by

    Returns:
        Sorted list of unique contact timestamps
    """
    rows = (
        db.query(ServeWindow.contact_timestamp)
        .filter(
            ServeWindow.video_id == video_id,
            ServeWindow.user_id == user_id,
            ServeWindow.contact_timestamp.isnot(None),
        )
        .all()
    )
    timestamps = sorted({r[0] for r in rows if r[0] is not None})
    return timestamps
