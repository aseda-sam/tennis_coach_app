import logging
from typing import List, Literal, Optional

from sqlalchemy.orm import Session

from app.core.config import settings
from app.models.ball_contact import BallContact
from app.models.video import Video

logger = logging.getLogger(__name__)

# Define allowed fields for BallContact updates
ALLOWED_BALL_CONTACT_FIELDS = {
    "frame_number",
    "video_timestamp",
    "contact_hand",
    "stroke_type",
    "stroke_subtype",
    "detection_source",
}


def create_ball_contact(
    db: Session,
    video_id: int,
    video_timestamp: float,
    contact_hand: Literal["left", "right"],
    stroke_type: Optional[Literal["ground_stroke", "serve", "volley", "overhead"]],
    stroke_subtype: Optional[str],
    detection_source: Optional[Literal["automated", "manual"]],
    player_id: Optional[int] = None,
) -> BallContact:
    """
    Create a new BallContact record in the database.
    Args:
        db (Session): SQLAlchemy database session.
        video_id (int): ID of the associated video.
        video_timestamp (float): Timestamp in the video for the ball contact.
        contact_hand (Literal["left", "right"]): Hand used for the contact.
        stroke_type (Optional[Literal["ground_stroke", "serve", "volley", "overhead"]]):
            Type of stroke.
        stroke_subtype (Optional[str]): Subtype of the stroke.
        detection_source (Optional[Literal["automated", "manual"]]):
            Source of the detection.
    Returns:
        BallContact: The created BallContact database object.
    """
    # Validate Video Exists
    video = db.query(Video).filter(Video.id == video_id).first()
    if not video:
        raise ValueError(f"Video with ID {video_id} not found")

    # Validate timestamp is within video duration
    if video.duration and video_timestamp > video.duration:
        raise ValueError(
            f"Timestamp {video_timestamp} exceeds video duration {video.duration}"
        )

    # Validate timestamp is positive
    if video_timestamp < 0:
        raise ValueError("Timestamp must be greater than 0")

    # Compute frame number from timestamp and FPS
    frame_number = None
    if video.fps and video.fps > 0:
        frame_number = round(video_timestamp * video.fps)

    # Check for existing manual contact at the same timestamp (within tolerance)
    tolerance = settings.BALL_CONTACT_TIMESTAMP_TOLERANCE
    existing_manual_detection = (
        db.query(BallContact)
        .filter(
            BallContact.video_id == video_id,
            BallContact.detection_source == "manual",
            BallContact.video_timestamp.between(
                video_timestamp - tolerance, video_timestamp + tolerance
            ),
        )
        .first()
    )
    if existing_manual_detection:
        raise ValueError(
            f"Manual contact already exists at timestamp {video_timestamp} "
            f"(±{tolerance} seconds) for video {video_id}"
        )

    # Create new manual contact detection
    db_ball_contact = BallContact(
        video_timestamp=video_timestamp,
        frame_number=frame_number,
        contact_hand=contact_hand,
        video_id=video_id,
        stroke_type=stroke_type,
        stroke_subtype=stroke_subtype,
        detection_source=detection_source,
    )
    db.add(db_ball_contact)
    db.commit()
    db.refresh(db_ball_contact)
    return db_ball_contact


def get_ball_contacts_by_video_id(db: Session, video_id: int) -> List[BallContact]:
    """
    Retrieve all BallContact records associated with a given video ID.

    Args:
        db (Session): SQLAlchemy database session.
        video_id (int): ID of the video.

    Returns:
        List[BallContact]: List of BallContact records for the video.
    """
    # Validate Video Exists
    video = db.query(Video).filter(Video.id == video_id).first()
    if not video:
        raise ValueError(f"Video with ID {video_id} not found")

    return db.query(BallContact).filter(BallContact.video_id == video_id).all()


def get_ball_contact_by_id(db: Session, ball_contact_id: int) -> Optional[BallContact]:
    """
    Retrieve a BallContact record by its ID.

    Args:
        db (Session): SQLAlchemy database session.
        ball_contact_id (int): ID of the BallContact record.

    Returns:
        BallContact: The BallContact record if found, else None.
    """
    # Validate BallContact Exists
    ball_contact = (
        db.query(BallContact).filter(BallContact.id == ball_contact_id).first()
    )
    if not ball_contact:
        return None

    return ball_contact


def update_ball_contact(
    db: Session, ball_contact_id: int, **updates: str | int | float | None
) -> BallContact:
    """
    Update an existing BallContact record.

    Args:
        db (Session): SQLAlchemy database session.
        ball_contact_id (int): ID of the BallContact record to update.
        **updates (dict): Updated fields for the BallContact record.

    Returns:
        BallContact: The updated BallContact record.

    Raises:
        ValueError: If the BallContact record is not found or invalid fields
            are provided.
    """
    contact = db.query(BallContact).filter(BallContact.id == ball_contact_id).first()
    if not contact:
        raise ValueError(f"BallContact with ID {ball_contact_id} not found")

    # Validate that all update keys are allowed fields
    invalid_fields = set(updates.keys()) - ALLOWED_BALL_CONTACT_FIELDS
    if invalid_fields:
        raise ValueError(
            f"Invalid fields for update: {invalid_fields}. Allowed fields: {ALLOWED_BALL_CONTACT_FIELDS}"
        )

    # Safely update only validated fields
    for key, value in updates.items():
        if key in ALLOWED_BALL_CONTACT_FIELDS:
            setattr(contact, key, value)

    # If video_timestamp was updated, recompute frame_number
    if "video_timestamp" in updates:
        video = db.query(Video).filter(Video.id == contact.video_id).first()
        if video and video.fps and video.fps > 0:
            contact.frame_number = round(contact.video_timestamp * video.fps)
        else:
            contact.frame_number = None

    db.commit()
    db.refresh(contact)
    return contact


def delete_ball_contact(db: Session, ball_contact_id: int) -> None:
    """
    Delete a BallContact record by its ID.

    Args:
        db (Session): SQLAlchemy database session.
        ball_contact_id (int): ID of the BallContact record to delete.

    Raises:
        ValueError: If the BallContact record is not found.
    """
    # First check if the contact exists
    contact = db.query(BallContact).filter(BallContact.id == ball_contact_id).first()
    if not contact:
        raise ValueError(f"BallContact with ID {ball_contact_id} not found")

    # Delete the contact
    db.delete(contact)
    db.commit()


# Note: Automated ball contact detection functions were removed as they were never implemented.
# Only manual ball contact creation is supported through the create_ball_contact function.
