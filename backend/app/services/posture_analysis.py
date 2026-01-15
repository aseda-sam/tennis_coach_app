"""
Posture analysis service for tennis coaching.

This module provides functions to analyze player posture at ball contact moments.
Starting with simple elbow angle calculation as MVP.
"""

import json
import logging
from typing import Dict, List, Optional

import numpy as np
from sqlalchemy.orm import Session

from app.models.ball_contact import BallContact
from app.models.pose_detection import PoseDetection
from app.models.video import Video

logger = logging.getLogger(__name__)


def calculate_elbow_angle(
    pose_landmarks: Dict, contact_hand: str, stroke_type: Optional[str] = None
) -> Optional[float]:
    """
    Calculate elbow angle from pose landmarks for the contact hand.

    Args:
        pose_landmarks: Dictionary with keypoint coordinates (x, y, confidence)
                       Expected format: {"left_elbow": [x, y, confidence], ...}
        contact_hand: Which hand made contact ('left' or 'right')
        stroke_type: Type of stroke (optional, for future use)

    Returns:
        Elbow angle in degrees, or None if keypoints missing or invalid stroke type
    """
    try:
        # Supported stroke types for elbow angle calculation
        # Serves and forehands/ground_strokes are single-handed strokes that work well
        # Backhands with both hands on racket are more complex and will be handled later
        supported_strokes = ["forehand", "ground_stroke", "serve"]
        if stroke_type and stroke_type.lower() not in supported_strokes:
            logger.info(
                f"Skipping elbow angle calculation for stroke type: {stroke_type}"
            )
            return None

        # Validate contact hand
        if contact_hand not in ["left", "right"]:
            logger.warning(
                f"Invalid contact hand: {contact_hand}. Expected 'left' or 'right'"
            )
            return None

        # Extract keypoint coordinates for the contact hand
        if contact_hand == "right":
            shoulder = pose_landmarks.get("right_shoulder")
            elbow = pose_landmarks.get("right_elbow")
            wrist = pose_landmarks.get("right_wrist")
        else:  # left
            shoulder = pose_landmarks.get("left_shoulder")
            elbow = pose_landmarks.get("left_elbow")
            wrist = pose_landmarks.get("left_wrist")

        # Check if all required keypoints are available
        if not all([shoulder, elbow, wrist]):
            logger.warning(
                f"Insufficient keypoints for {contact_hand} arm elbow angle calculation"
            )
            return None

        # Calculate elbow angle
        return _calculate_angle_between_points(
            shoulder[:2],  # [x, y]
            elbow[:2],  # [x, y]
            wrist[:2],  # [x, y]
        )

    except (ValueError, KeyError, IndexError) as e:
        logger.error(f"Error calculating elbow angle: {e}")
        return None


def _calculate_angle_between_points(
    point1: List[float], point2: List[float], point3: List[float]
) -> float:
    """
    Calculate angle between three points using vector math.

    Args:
        point1: First point [x, y] (e.g., shoulder)
        point2: Second point [x, y] (e.g., elbow) - vertex of angle
        point3: Third point [x, y] (e.g., wrist)

    Returns:
        Angle in degrees
    """
    # Convert to numpy arrays
    p1 = np.array(point1)
    p2 = np.array(point2)  # vertex
    p3 = np.array(point3)

    # Calculate vectors
    v1 = p1 - p2  # vector from elbow to shoulder
    v2 = p3 - p2  # vector from elbow to wrist

    # Calculate angle using dot product
    cos_angle = np.dot(v1, v2) / (np.linalg.norm(v1) * np.linalg.norm(v2))

    # Clamp to avoid numerical errors
    cos_angle = np.clip(cos_angle, -1.0, 1.0)

    # Convert to degrees
    angle_rad = np.arccos(cos_angle)
    angle_deg = np.degrees(angle_rad)

    return float(angle_deg)


def get_pose_at_contact(
    ball_contact: BallContact, pose_detection: PoseDetection, video: Video
) -> Optional[Dict]:
    """
    Get pose data for the frame closest to ball contact timestamp.

    Args:
        ball_contact: BallContact object with video_timestamp
        pose_detection: PoseDetection object with pose_data
        video: Video object with fps metadata

    Returns:
        Pose landmarks for contact frame, or None if not found
    """
    try:
        if not pose_detection.pose_data:
            logger.warning("No pose data available")
            return None

        # Deserialize pose data
        raw_pose_data = json.loads(pose_detection.pose_data)

        if not raw_pose_data:
            logger.warning("Empty pose data")
            return None

        # Use stored frame_number if available, otherwise calculate from timestamp
        if ball_contact.frame_number is not None:
            target_frame = ball_contact.frame_number
            logger.debug(
                f"Using stored frame_number: {target_frame} for contact {ball_contact.id}"
            )
        else:
            # Fallback: calculate frame from timestamp and FPS
            fps = video.fps if video.fps else 30.0  # Use actual FPS or fallback to 30
            target_frame = int(ball_contact.video_timestamp * fps)
            logger.debug(
                f"Calculated frame {target_frame} from timestamp {ball_contact.video_timestamp}s using FPS: {fps}"
            )

        # Find the closest available frame
        if target_frame < len(raw_pose_data):
            frame_data = raw_pose_data[target_frame]
            if frame_data is not None:
                return frame_data

        # If exact frame not found, search for nearest frame with pose data
        for offset in range(1, min(10, len(raw_pose_data))):  # Search within 10 frames
            # Try frames before and after
            for direction in [-1, 1]:
                frame_idx = target_frame + (offset * direction)
                if 0 <= frame_idx < len(raw_pose_data):
                    frame_data = raw_pose_data[frame_idx]
                    if frame_data is not None:
                        logger.info(
                            f"Using frame {frame_idx} (offset {offset * direction}) for contact at {ball_contact.video_timestamp}s"
                        )
                        return frame_data

        logger.warning(
            f"No pose data found near timestamp {ball_contact.video_timestamp}s"
        )
        return None

    except (json.JSONDecodeError, ValueError, KeyError) as e:
        logger.error(f"Error getting pose at contact: {e}")
        return None


def analyze_contact_posture(db: Session, ball_contact_id: int) -> Optional[float]:
    """
    Analyze posture for a specific ball contact.

    Args:
        db: Database session
        ball_contact_id: ID of the ball contact to analyze

    Returns:
        Calculated elbow angle, or None if analysis failed
    """
    try:
        # Fetch ball contact
        ball_contact = (
            db.query(BallContact).filter(BallContact.id == ball_contact_id).first()
        )

        if not ball_contact:
            logger.error(f"Ball contact {ball_contact_id} not found")
            return None

        # Fetch video for FPS metadata
        video = db.query(Video).filter(Video.id == ball_contact.video_id).first()
        if not video:
            logger.error(f"Video {ball_contact.video_id} not found")
            return None

        # Fetch pose detection for the same video
        pose_detection = (
            db.query(PoseDetection)
            .filter(
                PoseDetection.video_id == ball_contact.video_id,
                PoseDetection.status == "completed",
            )
            .first()
        )

        if not pose_detection:
            logger.error(
                f"No completed pose detection found for video {ball_contact.video_id}"
            )
            return None

        # Get pose data at contact moment
        pose_landmarks = get_pose_at_contact(ball_contact, pose_detection, video)

        if not pose_landmarks:
            logger.error(f"No pose data found for contact {ball_contact_id}")
            return None

        # Calculate elbow angle using contact hand and stroke type
        elbow_angle = calculate_elbow_angle(
            pose_landmarks, ball_contact.contact_hand, ball_contact.stroke_type
        )

        if elbow_angle is not None:
            logger.info(
                f"Calculated elbow angle {elbow_angle:.1f}° for {ball_contact.contact_hand}-handed {ball_contact.stroke_type or 'stroke'} contact {ball_contact_id}"
            )
        else:
            logger.warning(
                f"Failed to calculate elbow angle for contact {ball_contact_id} (hand: {ball_contact.contact_hand}, stroke: {ball_contact.stroke_type})"
            )

        return elbow_angle

    except (ValueError, KeyError, AttributeError) as e:
        logger.error(f"Error analyzing contact posture: {e}")
        return None


def analyze_all_contacts_for_video(
    db: Session, video_id: int, force_reanalysis: bool = False
) -> dict:
    """
    Analyze posture for all contacts in a video.

    Args:
        db: Database session
        video_id: ID of the video
        force_reanalysis: Whether to reanalyze even if already analyzed

    Returns:
        Dictionary with summary of analysis results
    """
    try:
        from app.models.ball_contact import BallContact

        # Fetch all contacts for the video
        contacts = (
            db.query(BallContact).filter(BallContact.video_id == video_id).all()
        )

        if not contacts:
            logger.info(f"No contacts found for video {video_id}")
            return {
                "video_id": video_id,
                "total_contacts": 0,
                "analyzed": 0,
                "failed": 0,
                "skipped": 0,
            }

        results = {
            "video_id": video_id,
            "total_contacts": len(contacts),
            "analyzed": 0,
            "failed": 0,
            "skipped": 0,
            "contact_results": [],
        }

        for contact in contacts:
            # Skip if already analyzed (unless forcing reanalysis)
            if not force_reanalysis and contact.elbow_angle is not None:
                results["skipped"] += 1
                continue

            # Analyze this contact
            contact_result = analyze_and_store_contact_posture(
                db, contact.id, force_reanalysis=force_reanalysis
            )
            results["contact_results"].append(contact_result)

            if contact_result["analysis_status"] == "success":
                results["analyzed"] += 1
            else:
                results["failed"] += 1

        logger.info(
            f"Analyzed {results['analyzed']} contacts for video {video_id} "
            f"(skipped: {results['skipped']}, failed: {results['failed']})"
        )

        return results

    except Exception as e:
        logger.error(f"Error analyzing all contacts for video {video_id}: {e}")
        return {
            "video_id": video_id,
            "total_contacts": 0,
            "analyzed": 0,
            "failed": 0,
            "skipped": 0,
            "error": str(e),
        }


def analyze_and_store_contact_posture(
    db: Session, ball_contact_id: int, force_reanalysis: bool = False
) -> dict:
    """
    Analyze posture for a specific ball contact and store results in database.

    Args:
        db: Database session
        ball_contact_id: ID of the ball contact to analyze
        force_reanalysis: Whether to reanalyze even if already analyzed

    Returns:
        Dictionary with analysis results and status
    """
    try:
        # Fetch ball contact
        ball_contact = (
            db.query(BallContact).filter(BallContact.id == ball_contact_id).first()
        )

        if not ball_contact:
            return {
                "ball_contact_id": ball_contact_id,
                "elbow_angle": None,
                "analysis_status": "failed",
                "message": "Ball contact not found",
            }

        # Check if already analyzed (unless forcing reanalysis)
        if not force_reanalysis and ball_contact.elbow_angle is not None:
            return {
                "ball_contact_id": ball_contact_id,
                "elbow_angle": ball_contact.elbow_angle,
                "analysis_status": "success",
                "message": "Analysis already completed",
            }

        # Perform posture analysis
        elbow_angle = analyze_contact_posture(db, ball_contact_id)

        if elbow_angle is not None:
            # Validate angle is within reasonable range (0-180 degrees)
            if not (0.0 <= elbow_angle <= 180.0):
                logger.warning(
                    f"Elbow angle {elbow_angle:.1f}° is outside valid range (0-180°)"
                )
                return {
                    "ball_contact_id": ball_contact_id,
                    "elbow_angle": None,
                    "analysis_status": "failed",
                    "message": f"Invalid elbow angle: {elbow_angle:.1f}° (must be 0-180°)",
                }

            # Store result in database
            ball_contact.elbow_angle = elbow_angle
            db.commit()

            return {
                "ball_contact_id": ball_contact_id,
                "elbow_angle": elbow_angle,
                "analysis_status": "success",
                "message": f"Elbow angle calculated: {elbow_angle:.1f}°",
            }
        else:
            # Determine failure reason
            if not ball_contact.contact_hand:
                status = "failed"
                message = "No contact hand specified"
            elif ball_contact.stroke_type and ball_contact.stroke_type.lower() not in [
                "forehand",
                "ground_stroke",
                "serve",
            ]:
                status = "invalid_stroke"
                message = f"Stroke type '{ball_contact.stroke_type}' not supported for posture analysis"
            else:
                status = "no_pose_data"
                message = "No pose data available for analysis"

            return {
                "ball_contact_id": ball_contact_id,
                "elbow_angle": None,
                "analysis_status": status,
                "message": message,
            }

    except (ValueError, KeyError, AttributeError, RuntimeError) as e:
        logger.error(f"Error in analyze_and_store_contact_posture: {e}")
        db.rollback()
        return {
            "ball_contact_id": ball_contact_id,
            "elbow_angle": None,
            "analysis_status": "failed",
            "message": f"Analysis failed: {e!s}",
        }
