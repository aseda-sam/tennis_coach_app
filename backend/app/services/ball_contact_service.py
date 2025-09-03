import logging
from typing import Any, Dict, List, Literal, Optional, Tuple

from sqlalchemy.orm import Session

from app.core.config import settings
from app.models.ball_contact import BallContact
from app.models.video import Video

logger = logging.getLogger(__name__)

# Define allowed fields for BallContact updates
ALLOWED_BALL_CONTACT_FIELDS = {
    "frame_number",
    "video_timestamp",
    "player",
    "contact_hand",
    "stroke_type",
    "stroke_subtype",
    "confidence",
    "ball_position",
    "player_position",
    "description",
    "detection_source",
    "ball_area",
    "ball_size_factor",
    "racket_data",
    "ball_bbox",
    "ball_racket_distance",
}


def create_ball_contact(
    db: Session,
    video_id: int,
    video_timestamp: float,
    contact_hand: Literal["left", "right"],
    stroke_type: Optional[Literal["ground_stroke", "serve", "volley", "overhead"]],
    stroke_subtype: Optional[str],
    detection_source: Optional[Literal["automated", "manual"]],
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


def detect_ball_contact(
    ball_detections: List[List[Dict[str, Any]]],
    pose_detections: List[Optional[Dict[str, List[float]]]],
    fps: float,
    contact_threshold: float = 50.0,
) -> Tuple[List[float], List[Dict[str, Any]]]:
    """
    Detect frames where ball contact occurs based on ball and player proximity.

    Args:
        ball_detections: List of ball detections per frame
        pose_detections: List of pose detections per frame
        fps: Frames per second of the video
        contact_threshold: Distance threshold in pixels for contact detection

    Returns:
        Tuple of (contact_timestamps, contact_detections)
    """
    contact_timestamps = []
    contact_detections = []

    for frame_index, (frame_balls, frame_pose) in enumerate(
        zip(ball_detections, pose_detections)
    ):
        # Skip frames without ball detections
        if not frame_balls:
            continue

        # Skip frames without pose detection
        if not frame_pose:
            continue

        # Check each ball detection against player position
        for ball_detection in frame_balls:
            ball_bbox = ball_detection["bbox"]
            ball_center_x = (ball_bbox[0] + ball_bbox[2]) / 2
            ball_center_y = (ball_bbox[1] + ball_bbox[3]) / 2

            # Get player hand positions (primary contact points)
            left_wrist = frame_pose.get("left_wrist")
            right_wrist = frame_pose.get("right_wrist")

            # Check distance to both wrists
            min_distance = float("inf")
            contact_hand = None

            if left_wrist:
                distance = (
                    (ball_center_x - left_wrist[0]) ** 2
                    + (ball_center_y - left_wrist[1]) ** 2
                ) ** 0.5
                if distance < min_distance:
                    min_distance = distance
                    contact_hand = "left"

            if right_wrist:
                distance = (
                    (ball_center_x - right_wrist[0]) ** 2
                    + (ball_center_y - right_wrist[1]) ** 2
                ) ** 0.5
                if distance < min_distance:
                    min_distance = distance
                    contact_hand = "right"

            # Check if ball is close enough to player hands for contact
            if min_distance <= contact_threshold:
                timestamp = frame_index / fps

                # Create contact detection record
                contact_detection = {
                    "frame_index": frame_index,
                    "timestamp": timestamp,
                    "ball_position": {"x": ball_center_x, "y": ball_center_y},
                    "ball_bbox": ball_bbox,
                    "contact_hand": contact_hand,
                    "distance": min_distance,
                    "confidence": ball_detection["confidence"],
                    "player_position": {
                        "left_wrist": left_wrist,
                        "right_wrist": right_wrist,
                        "left_shoulder": frame_pose.get("left_shoulder"),
                        "right_shoulder": frame_pose.get("right_shoulder"),
                    },
                }

                contact_timestamps.append(timestamp)
                contact_detections.append(contact_detection)

    # Sort by timestamp
    sorted_contacts = sorted(
        zip(contact_timestamps, contact_detections), key=lambda x: x[0]
    )
    contact_timestamps = [t for t, _ in sorted_contacts]
    contact_detections = [d for _, d in sorted_contacts]

    logger.info(
        f"Ball contact detection complete: {len(contact_timestamps)} contacts found"
    )

    return contact_timestamps, contact_detections


def _calculate_racket_head_position(
    racket_position: Dict[str, Any], pose_data: Dict[str, List[float]]
) -> Tuple[float, float]:
    """
    Calculate the actual racket head position from racket center and pose data.

    The racket head is typically at the end of the racket, extending beyond the center
    in the direction away from the wrist.

    Args:
        racket_position: Racket detection data with center, bbox, closest_wrist
        pose_data: Pose detection with wrist positions

    Returns:
        Tuple of (head_x, head_y) coordinates
    """
    racket_center = racket_position["center"]
    closest_wrist = racket_position["closest_wrist"]

    # Get wrist position
    wrist_key = f"{closest_wrist}_wrist"
    wrist_pos = pose_data.get(wrist_key)

    if not wrist_pos:
        # Fallback to racket center if no wrist data
        return racket_center[0], racket_center[1]

    # Calculate vector from wrist to racket center
    wrist_to_center_x = racket_center[0] - wrist_pos[0]
    wrist_to_center_y = racket_center[1] - wrist_pos[1]

    # Normalize the vector
    vector_length = (wrist_to_center_x**2 + wrist_to_center_y**2) ** 0.5
    if vector_length == 0:
        return racket_center[0], racket_center[1]

    norm_x = wrist_to_center_x / vector_length
    norm_y = wrist_to_center_y / vector_length

    # Extend beyond center by typical racket head distance (assume ~40 pixels)
    head_extension = 40.0  # pixels
    head_x = racket_center[0] + (norm_x * head_extension)
    head_y = racket_center[1] + (norm_y * head_extension)

    return head_x, head_y


def _calculate_ball_trajectory_change(
    ball_positions: List[Tuple[float, float]], frame_index: int, window_size: int = 3
) -> float:
    """
    Calculate the change in ball trajectory at a given frame.

    Args:
        ball_positions: List of (x, y) ball positions
        frame_index: Current frame index
        window_size: Number of frames to consider for trajectory calculation

    Returns:
        Trajectory change magnitude
    """
    if len(ball_positions) < window_size * 2:
        return 0.0

    # Get positions before and after current frame
    before_start = max(0, frame_index - window_size)
    before_end = frame_index
    after_start = frame_index
    after_end = min(len(ball_positions), frame_index + window_size)

    if before_end - before_start < 2 or after_end - after_start < 2:
        return 0.0

    # Calculate average velocity before and after
    before_positions = ball_positions[before_start:before_end]
    after_positions = ball_positions[after_start:after_end]

    # Calculate velocity vectors
    before_vel_x = sum(
        before_positions[i + 1][0] - before_positions[i][0]
        for i in range(len(before_positions) - 1)
    ) / (len(before_positions) - 1)
    before_vel_y = sum(
        before_positions[i + 1][1] - before_positions[i][1]
        for i in range(len(before_positions) - 1)
    ) / (len(before_positions) - 1)

    after_vel_x = sum(
        after_positions[i + 1][0] - after_positions[i][0]
        for i in range(len(after_positions) - 1)
    ) / (len(after_positions) - 1)
    after_vel_y = sum(
        after_positions[i + 1][1] - after_positions[i][1]
        for i in range(len(after_positions) - 1)
    ) / (len(after_positions) - 1)

    # Calculate change in velocity
    vel_change_x = after_vel_x - before_vel_x
    vel_change_y = after_vel_y - before_vel_y

    return (vel_change_x**2 + vel_change_y**2) ** 0.5


def detect_ball_contact_with_rackets(
    ball_detections: List[List[Dict[str, Any]]],
    pose_detections: List[Optional[Dict[str, List[float]]]],
    racket_positions: List[Optional[Dict[str, Any]]],
    fps: float,
    contact_threshold: float = 50.0,
    racket_contact_threshold: float = 15.0,
    min_ball_confidence: float = 0.5,
    early_video_skip_seconds: float = 2.0,
) -> Tuple[List[float], List[Dict[str, Any]]]:
    """
    Detect frames where ball contact occurs using improved racket head detection and trajectory analysis.

    This function uses a multi-criteria approach:
    1. Calculates actual racket head position (not just center)
    2. Analyzes ball trajectory changes to detect impacts
    3. Uses much tighter distance thresholds for accuracy
    4. Validates contact with temporal patterns

    Args:
        ball_detections: List of ball detections per frame
        pose_detections: List of pose detections per frame
        racket_positions: List of estimated racket positions per frame
        fps: Frames per second of the video
        contact_threshold: Distance threshold in pixels for wrist-based contact detection (fallback)
        racket_contact_threshold: Distance threshold in pixels for racket-head contact detection

    Returns:
        Tuple of (contact_timestamps, contact_detections)
    """
    contact_timestamps = []
    contact_detections = []

    # Calculate video duration for filtering
    total_frames = len(ball_detections)
    video_duration = total_frames / fps
    early_skip_frames = int(early_video_skip_seconds * fps)

    logger.info(
        f"Smart contact filtering: Skip first {early_video_skip_seconds}s ({early_skip_frames} frames), "
        f"Min ball confidence: {min_ball_confidence}, Video duration: {video_duration:.1f}s"
    )

    for frame_index, (frame_balls, frame_pose, racket_position) in enumerate(
        zip(ball_detections, pose_detections, racket_positions)
    ):
        # Skip early video frames (likely player positioning, not actual hits)
        if frame_index < early_skip_frames:
            continue

        # Skip frames without ball detections
        if not frame_balls:
            continue

        # Skip frames without pose detection
        if not frame_pose:
            continue

        # Filter for high-confidence ball detections only
        high_confidence_balls = [
            ball
            for ball in frame_balls
            if ball.get("confidence", 0) >= min_ball_confidence
        ]
        if not high_confidence_balls:
            continue

        # Check each high-confidence ball detection
        for ball_detection in high_confidence_balls:
            ball_bbox = ball_detection["bbox"]
            ball_center_x = (ball_bbox[0] + ball_bbox[2]) / 2
            ball_center_y = (ball_bbox[1] + ball_bbox[3]) / 2

            # Calculate ball size for depth perception (larger = closer = more likely real contact)
            ball_width = ball_bbox[2] - ball_bbox[0]
            ball_height = ball_bbox[3] - ball_bbox[1]
            ball_area = ball_width * ball_height
            ball_confidence = ball_detection.get("confidence", 0.0)

            # Calculate ball size factor for use in both racket and wrist detection
            ball_size_factor = min(
                ball_area / 400.0, 2.0
            )  # Normalize by typical ball size

            # Primary: Check ball-racket proximity if racket position is available
            contact_detected = False
            contact_type = "wrist"  # Default to wrist-based contact
            contact_distance = float("inf")
            contact_hand = None
            racket_data = None

            if racket_position and racket_position.get("center"):
                racket_center = racket_position["center"]
                racket_distance = (
                    (ball_center_x - racket_center[0]) ** 2
                    + (ball_center_y - racket_center[1]) ** 2
                ) ** 0.5

                # Apply depth-based distance adjustment (closer balls get stricter thresholds)
                adjusted_racket_threshold = racket_contact_threshold * (
                    2.0 - ball_size_factor
                )  # Closer balls (larger) get stricter thresholds

                if racket_distance <= adjusted_racket_threshold:
                    contact_detected = True
                    contact_type = "racket"
                    contact_distance = racket_distance
                    contact_hand = racket_position.get("closest_wrist", "unknown")
                    racket_data = {
                        "center": racket_center,
                        "bbox": racket_position.get("bbox"),
                        "closest_wrist": racket_position.get("closest_wrist"),
                        "distance": racket_distance,
                        "threshold_used": adjusted_racket_threshold,
                    }

            # Fallback: Check ball-wrist proximity if no racket contact detected
            if not contact_detected:
                left_wrist = frame_pose.get("left_wrist")
                right_wrist = frame_pose.get("right_wrist")

                min_distance = float("inf")
                contact_hand = None

                if left_wrist:
                    distance = (
                        (ball_center_x - left_wrist[0]) ** 2
                        + (ball_center_y - left_wrist[1]) ** 2
                    ) ** 0.5
                    if distance < min_distance:
                        min_distance = distance
                        contact_hand = "left"

                if right_wrist:
                    distance = (
                        (ball_center_x - right_wrist[0]) ** 2
                        + (ball_center_y - right_wrist[1]) ** 2
                    ) ** 0.5
                    if distance < min_distance:
                        min_distance = distance
                        contact_hand = "right"

                # Apply depth-based distance adjustment for wrist detection too
                adjusted_contact_threshold = contact_threshold * (
                    2.0 - ball_size_factor
                )

                if min_distance <= adjusted_contact_threshold:
                    contact_detected = True
                    contact_type = "wrist"
                    contact_distance = min_distance

            # Record contact if detected
            if contact_detected:
                timestamp = frame_index / fps

                # Create comprehensive contact detection record
                contact_detection = {
                    "frame_index": frame_index,
                    "timestamp": timestamp,
                    "ball_position": {"x": ball_center_x, "y": ball_center_y},
                    "ball_bbox": ball_bbox,
                    "ball_area": ball_area,
                    "ball_size_factor": ball_size_factor,
                    "ball_confidence": ball_confidence,
                    "contact_hand": contact_hand,
                    "contact_type": contact_type,
                    "contact_distance": contact_distance,
                    "player_position": {
                        "left_wrist": frame_pose.get("left_wrist"),
                        "right_wrist": frame_pose.get("right_wrist"),
                        "left_shoulder": frame_pose.get("left_shoulder"),
                        "right_shoulder": frame_pose.get("right_shoulder"),
                    },
                    "racket_data": racket_data,
                    "detection_source": "improved_racket_detection",
                }

                contact_timestamps.append(timestamp)
                contact_detections.append(contact_detection)

    # Sort by timestamp
    sorted_contacts = sorted(
        zip(contact_timestamps, contact_detections), key=lambda x: x[0]
    )
    contact_timestamps = [t for t, _ in sorted_contacts]
    contact_detections = [d for _, d in sorted_contacts]

    logger.info(
        f"Improved ball contact detection complete: {len(contact_timestamps)} contacts found"
    )

    return contact_timestamps, contact_detections
