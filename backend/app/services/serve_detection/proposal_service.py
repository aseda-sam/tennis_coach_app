"""Service for managing serve window proposals."""

import json
import logging
from datetime import datetime
from typing import Dict, List, Optional

from sqlalchemy.orm import Session

from app.models.pose_detection import PoseDetection
from app.models.serve_attempt import ServeAttempt
from app.models.serve_window_proposal import ServeWindowProposal
from app.models.video import Video
from app.services import player_service
from app.services.serve_detection.feature_extractor import extract_frame_features
from app.services.serve_detection.heuristic_detector import detect_serve_windows

logger = logging.getLogger(__name__)

MODEL_VERSION = "heuristic-v1"


def check_existing_proposals_or_attempts(
    db: Session, video_id: int, user_id: str
) -> Dict:
    """
    Check if there are existing proposals or serve attempts for a video.

    Returns:
        Dict with counts of pending_proposals, reviewed_proposals, and serve_attempts
    """
    pending_proposals = (
        db.query(ServeWindowProposal)
        .filter(
            ServeWindowProposal.video_id == video_id,
            ServeWindowProposal.user_id == user_id,
            ServeWindowProposal.status == "pending",
        )
        .count()
    )

    reviewed_proposals = (
        db.query(ServeWindowProposal)
        .filter(
            ServeWindowProposal.video_id == video_id,
            ServeWindowProposal.user_id == user_id,
            ServeWindowProposal.status.in_(["accepted", "rejected", "edited"]),
        )
        .count()
    )

    serve_attempts = (
        db.query(ServeAttempt)
        .filter(
            ServeAttempt.video_id == video_id,
            ServeAttempt.user_id == user_id,
        )
        .count()
    )

    return {
        "pending_proposals": pending_proposals,
        "reviewed_proposals": reviewed_proposals,
        "serve_attempts": serve_attempts,
    }


def clear_pending_proposals(db: Session, video_id: int, user_id: str) -> int:
    """
    Clear all pending proposals for a video.

    Args:
        db: Database session
        video_id: Video ID
        user_id: User ID (for tenancy)

    Returns:
        Number of proposals deleted
    """
    deleted_count = (
        db.query(ServeWindowProposal)
        .filter(
            ServeWindowProposal.video_id == video_id,
            ServeWindowProposal.user_id == user_id,
            ServeWindowProposal.status == "pending",
        )
        .delete(synchronize_session=False)
    )
    db.commit()
    logger.info(f"Cleared {deleted_count} pending proposals for video {video_id}")
    return deleted_count


def generate_proposals(
    db: Session, video_id: int, user_id: str, force: bool = False
) -> List[ServeWindowProposal]:
    """
    Generate serve window proposals for a video using heuristic detection.

    Args:
        db: Database session
        video_id: Video ID
        user_id: User ID (for tenancy)
        force: If True, clear existing pending proposals before generating new ones

    Returns:
        List of created ServeWindowProposal records

    Raises:
        ValueError: If video not found, pose data not available, or proposals already exist
    """
    # Check for existing proposals/attempts
    existing = check_existing_proposals_or_attempts(db, video_id, user_id)

    if existing["pending_proposals"] > 0:
        if force:
            clear_pending_proposals(db, video_id, user_id)
        else:
            raise ValueError(
                f"Video already has {existing['pending_proposals']} pending proposal(s). "
                "Review or clear them before running detection again."
            )

    if existing["serve_attempts"] > 0 and not force:
        raise ValueError(
            f"Video already has {existing['serve_attempts']} serve attempt(s). "
            "Clear proposals and serve attempts if you want to re-run detection."
        )

    # Load video
    video = db.query(Video).filter(Video.id == video_id).first()
    if not video:
        raise ValueError(f"Video {video_id} not found")

    if not video.fps or video.fps <= 0:
        raise ValueError(f"Video {video_id} has invalid FPS: {video.fps}")

    # Load pose detection
    pose_detection = (
        db.query(PoseDetection)
        .filter(
            PoseDetection.video_id == video_id,
            PoseDetection.status == "completed",
        )
        .order_by(PoseDetection.created_at.desc())
        .first()
    )

    if not pose_detection:
        # Check if there's any pose detection record to give better error message
        any_pose_detection = (
            db.query(PoseDetection)
            .filter(PoseDetection.video_id == video_id)
            .order_by(PoseDetection.created_at.desc())
            .first()
        )
        if any_pose_detection:
            logger.warning(
                f"Video {video_id} has pose detection with status '{any_pose_detection.status}', "
                f"error: {any_pose_detection.error_message}"
            )
            raise ValueError(
                f"Pose detection for video {video_id} is not completed "
                f"(status: {any_pose_detection.status}). "
                "Please wait for pose detection to finish or re-run it."
            )
        else:
            raise ValueError(
                f"No pose detection found for video {video_id}. "
                "Please run pose detection first."
            )

    if not pose_detection.pose_data:
        raise ValueError(f"Pose detection {pose_detection.id} has no pose data")

    # Deserialize pose data
    try:
        raw_pose_data = json.loads(pose_detection.pose_data)
    except json.JSONDecodeError as e:
        raise ValueError(f"Failed to parse pose data: {e}") from e

    if not raw_pose_data:
        raise ValueError("Pose data is empty")

    # Log pose data structure for debugging
    logger.info(
        f"Processing {len(raw_pose_data)} frames of pose data for video {video_id}"
    )

    # Check first non-null frame to understand data format
    sample_frame = None
    for frame_data in raw_pose_data:
        if frame_data is not None:
            sample_frame = frame_data
            break

    if sample_frame:
        if isinstance(sample_frame, dict):
            logger.info(
                f"Pose data format: dict with keys: {list(sample_frame.keys())[:10]}..."
            )
            # Check if we have the expected keypoint names
            expected_keys = [
                "left_wrist",
                "right_wrist",
                "left_shoulder",
                "right_shoulder",
                "left_hip",
                "right_hip",
            ]
            missing_keys = [k for k in expected_keys if k not in sample_frame]
            if missing_keys:
                logger.warning(f"Missing expected keypoints: {missing_keys}")
        else:
            logger.warning(
                f"Unexpected pose data format: {type(sample_frame)}, expected dict"
            )

    # Extract features from each frame
    features: List[Dict] = []
    frame_shape = (video.height or 1080, video.width or 1920, 3)  # Default to 1080p

    logger.info(f"Video dimensions: {video.width}x{video.height}, FPS: {video.fps}")

    for frame_idx, frame_pose_data in enumerate(raw_pose_data):
        prev_pose = raw_pose_data[frame_idx - 1] if frame_idx > 0 else None
        frame_features = extract_frame_features(
            pose_data=frame_pose_data,
            prev_pose=prev_pose,
            fps=video.fps,
            frame_shape=frame_shape,
        )
        features.append(frame_features)

        # Log sample features for first few frames with pose data
        if frame_idx < 5 and frame_pose_data is not None:
            logger.debug(
                f"Frame {frame_idx} features: height={frame_features.get('max_wrist_height', 0):.2f}, "
                f"velocity={frame_features.get('max_wrist_velocity', 0):.1f}, "
                f"both_arms={frame_features.get('both_arms_raised', False)}"
            )

    # Detect serve windows
    proposals_data = detect_serve_windows(features, video.fps)

    if not proposals_data:
        logger.info(f"No serve windows detected for video {video_id}")
        return []

    # Create proposal records
    proposals: List[ServeWindowProposal] = []
    for proposal_data in proposals_data:
        detection_features_json = json.dumps(
            proposal_data.get("detection_features", {})
        )

        proposal = ServeWindowProposal(
            video_id=video_id,
            user_id=user_id,
            start_timestamp=proposal_data["start_timestamp"],
            end_timestamp=proposal_data["end_timestamp"],
            model_version=MODEL_VERSION,
            confidence=proposal_data["confidence"],
            detection_features=detection_features_json,
            status="pending",
        )
        db.add(proposal)
        proposals.append(proposal)

    db.commit()

    logger.info(
        f"Generated {len(proposals)} serve window proposals for video {video_id}"
    )
    return proposals


def accept_proposal(
    db: Session, proposal_id: int, user_id: str, player_id: Optional[int] = None
) -> ServeAttempt:
    """
    Accept a proposal as-is, creating a ServeAttempt.

    Args:
        db: Database session
        proposal_id: Proposal ID
        user_id: User ID (for authorization)
        player_id: Optional player ID (defaults to user's default player)

    Returns:
        Created ServeAttempt

    Raises:
        ValueError: If proposal not found or unauthorized
    """
    proposal = (
        db.query(ServeWindowProposal)
        .filter(ServeWindowProposal.id == proposal_id)
        .first()
    )
    if not proposal:
        raise ValueError(f"Proposal {proposal_id} not found")

    if proposal.user_id != user_id:
        raise ValueError("Unauthorized: proposal belongs to different user")

    if proposal.status != "pending":
        raise ValueError(
            f"Proposal {proposal_id} already reviewed (status: {proposal.status})"
        )

    # Get or create default player if not provided
    if not player_id:
        default_player = player_service.get_or_create_default_player(db, user_id)
        player_id = default_player.id

    # Validate player ownership
    from app.models.player import Player

    player = db.query(Player).filter(Player.id == player_id).first()
    if not player or player.user_id != user_id:
        raise ValueError("Player not found or access denied")

    # Create serve attempt
    serve_attempt = ServeAttempt(
        video_id=proposal.video_id,
        user_id=user_id,
        player_id=player_id,
        start_timestamp=proposal.start_timestamp,
        end_timestamp=proposal.end_timestamp,
        source="auto_accepted",
        source_proposal_id=proposal.id,
    )
    db.add(serve_attempt)
    db.flush()  # Get serve_attempt.id

    # Update proposal
    proposal.status = "accepted"
    proposal.reviewed_at = datetime.utcnow()
    proposal.serve_attempt_id = serve_attempt.id
    db.commit()

    logger.info(f"Accepted proposal {proposal_id} as serve attempt {serve_attempt.id}")
    return serve_attempt


def reject_proposal(db: Session, proposal_id: int, user_id: str) -> None:
    """
    Reject a proposal.

    Args:
        db: Database session
        proposal_id: Proposal ID
        user_id: User ID (for authorization)

    Raises:
        ValueError: If proposal not found or unauthorized
    """
    proposal = (
        db.query(ServeWindowProposal)
        .filter(ServeWindowProposal.id == proposal_id)
        .first()
    )
    if not proposal:
        raise ValueError(f"Proposal {proposal_id} not found")

    if proposal.user_id != user_id:
        raise ValueError("Unauthorized: proposal belongs to different user")

    if proposal.status != "pending":
        raise ValueError(
            f"Proposal {proposal_id} already reviewed (status: {proposal.status})"
        )

    proposal.status = "rejected"
    proposal.reviewed_at = datetime.utcnow()
    db.commit()

    logger.info(f"Rejected proposal {proposal_id}")


def accept_with_edits(
    db: Session,
    proposal_id: int,
    user_id: str,
    new_start_timestamp: float,
    new_end_timestamp: float,
    player_id: Optional[int] = None,
) -> ServeAttempt:
    """
    Accept a proposal with edited timestamps, creating a ServeAttempt.

    Args:
        db: Database session
        proposal_id: Proposal ID
        user_id: User ID (for authorization)
        new_start_timestamp: Edited start timestamp
        new_end_timestamp: Edited end timestamp
        player_id: Optional player ID (defaults to user's default player)

    Returns:
        Created ServeAttempt

    Raises:
        ValueError: If proposal not found, unauthorized, or timestamps invalid
    """
    proposal = (
        db.query(ServeWindowProposal)
        .filter(ServeWindowProposal.id == proposal_id)
        .first()
    )
    if not proposal:
        raise ValueError(f"Proposal {proposal_id} not found")

    if proposal.user_id != user_id:
        raise ValueError("Unauthorized: proposal belongs to different user")

    if proposal.status != "pending":
        raise ValueError(
            f"Proposal {proposal_id} already reviewed (status: {proposal.status})"
        )

    if new_start_timestamp >= new_end_timestamp:
        raise ValueError("start_timestamp must be less than end_timestamp")

    # Get or create default player if not provided
    if not player_id:
        default_player = player_service.get_or_create_default_player(db, user_id)
        player_id = default_player.id

    # Validate player ownership
    from app.models.player import Player

    player = db.query(Player).filter(Player.id == player_id).first()
    if not player or player.user_id != user_id:
        raise ValueError("Player not found or access denied")

    # Create serve attempt with edited timestamps
    serve_attempt = ServeAttempt(
        video_id=proposal.video_id,
        user_id=user_id,
        player_id=player_id,
        start_timestamp=new_start_timestamp,
        end_timestamp=new_end_timestamp,
        source="auto_edited",
        source_proposal_id=proposal.id,
        original_start_timestamp=proposal.start_timestamp,
        original_end_timestamp=proposal.end_timestamp,
    )
    db.add(serve_attempt)
    db.flush()  # Get serve_attempt.id

    # Update proposal
    proposal.status = "edited"
    proposal.reviewed_at = datetime.utcnow()
    proposal.serve_attempt_id = serve_attempt.id
    db.commit()

    logger.info(
        f"Accepted proposal {proposal_id} with edits as serve attempt {serve_attempt.id}"
    )
    return serve_attempt
