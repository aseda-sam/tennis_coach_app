"""Serve-specific analysis service for calculating elbow angles at contact."""

import json
import logging
from typing import Dict, List, Optional

from sqlalchemy.orm import Session

from app.models.player import Player
from app.models.pose_detection import PoseDetection
from app.models.serve_attempt import ServeAttempt
from app.models.video import Video
from app.services.posture_analysis import calculate_elbow_angle

logger = logging.getLogger(__name__)


def _extract_keypoints(frame_data: Optional[Dict]) -> Optional[Dict]:
    """
    Extract keypoints from frame data, handling both old and new formats.

    Args:
        frame_data: Frame data from pose_detections (either keypoints dict directly
                   or wrapper dict with frame_index/timestamp_ms/keypoints)

    Returns:
        Keypoints dict if available, None otherwise
    """
    if frame_data is None:
        return None

    # New format: {"frame_index": ..., "timestamp_ms": ..., "keypoints": {...}}
    if isinstance(frame_data, dict) and "keypoints" in frame_data:
        return frame_data.get("keypoints")

    # Old format: keypoints dict directly (backward compatibility)
    return frame_data


def get_pose_at_timestamp(
    pose_detection: PoseDetection, video: Video, timestamp: float
) -> Optional[Dict]:
    """
    Get pose data for the frame closest to a given timestamp.

    Args:
        pose_detection: PoseDetection object with pose_data
        video: Video object with fps metadata
        timestamp: Timestamp in seconds

    Returns:
        Pose landmarks for the frame closest to timestamp, or None if not found
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

        # Calculate frame from timestamp and FPS
        fps = video.fps if video.fps else 30.0
        target_frame = int(timestamp * fps)
        logger.debug(
            f"Calculated frame {target_frame} from timestamp {timestamp}s using FPS: {fps}"
        )

        # Find the closest available frame
        if target_frame < len(raw_pose_data):
            frame_data = raw_pose_data[target_frame]
            keypoints = _extract_keypoints(frame_data)
            if keypoints is not None:
                return keypoints

        # If exact frame not found, search for nearest frame with pose data
        for offset in range(1, min(10, len(raw_pose_data))):  # Search within 10 frames
            # Try frames before and after
            for direction in [-1, 1]:
                frame_idx = target_frame + (offset * direction)
                if 0 <= frame_idx < len(raw_pose_data):
                    frame_data = raw_pose_data[frame_idx]
                    keypoints = _extract_keypoints(frame_data)
                    if keypoints is not None:
                        logger.info(
                            f"Using frame {frame_idx} (offset {offset * direction}) "
                            f"for timestamp {timestamp}s"
                        )
                        return keypoints

        logger.warning(f"No pose data found near timestamp {timestamp}s")
        return None

    except (json.JSONDecodeError, ValueError, KeyError) as e:
        logger.error(f"Error getting pose at timestamp: {e}")
        return None


class ServeAnalysisService:
    """Serve-specific analysis that writes to serve_attempts."""

    def analyze_serve_attempts(
        self, db: Session, video_id: int, serve_attempts: List[ServeAttempt]
    ) -> Dict[str, any]:
        """
        Batch analyze serve attempts that have been manually tagged.

        Steps:
        1. Load pose_detection data for video
        2. For each serve_attempt:
           - If contact_timestamp exists, calculate elbow_angle_at_contact
           - Store results in serve_attempts table
        3. Return summary

        Args:
            db: Database session
            video_id: Video ID
            serve_attempts: List of serve attempts to analyze

        Returns:
            Summary dictionary with analysis results
        """
        try:
            # Load video and pose detection
            video = db.query(Video).filter(Video.id == video_id).first()
            if not video:
                raise ValueError(f"Video {video_id} not found")

            pose_detection = (
                db.query(PoseDetection)
                .filter(
                    PoseDetection.video_id == video_id,
                    PoseDetection.status == "completed",
                )
                .first()
            )

            if not pose_detection:
                raise ValueError(
                    f"No completed pose detection found for video {video_id}. "
                    "Please run pose detection first."
                )

            analyzed_count = 0
            failed_count = 0
            skipped_count = 0
            elbow_angles: List[float] = []

            for serve_attempt in serve_attempts:
                # Skip if no contact timestamp
                if not serve_attempt.contact_timestamp:
                    logger.debug(
                        f"Skipping serve attempt {serve_attempt.id} - no contact timestamp"
                    )
                    skipped_count += 1
                    continue

                # Get player to determine contact hand
                player = (
                    db.query(Player)
                    .filter(Player.id == serve_attempt.player_id)
                    .first()
                )
                if not player:
                    logger.warning(
                        f"Player {serve_attempt.player_id} not found for serve attempt {serve_attempt.id}"
                    )
                    failed_count += 1
                    continue

                # Get pose data at contact timestamp
                pose_landmarks = get_pose_at_timestamp(
                    pose_detection, video, serve_attempt.contact_timestamp
                )

                if not pose_landmarks:
                    logger.warning(
                        f"No pose data found for serve attempt {serve_attempt.id} "
                        f"at timestamp {serve_attempt.contact_timestamp}s"
                    )
                    failed_count += 1
                    continue

                # Calculate elbow angle
                elbow_angle = calculate_elbow_angle(
                    pose_landmarks=pose_landmarks,
                    contact_hand=player.dominant_hand,
                    stroke_type="serve",
                )

                if elbow_angle is not None:
                    # Validate angle is within reasonable range (0-180 degrees)
                    if not (0.0 <= elbow_angle <= 180.0):
                        logger.warning(
                            f"Elbow angle {elbow_angle:.1f}° is outside valid range "
                            f"(0-180°) for serve attempt {serve_attempt.id}"
                        )
                        failed_count += 1
                        continue

                    # Store result
                    serve_attempt.elbow_angle_at_contact = elbow_angle
                    elbow_angles.append(elbow_angle)
                    analyzed_count += 1
                    logger.debug(
                        f"Calculated elbow angle {elbow_angle:.1f}° for serve attempt {serve_attempt.id}"
                    )
                else:
                    logger.warning(
                        f"Failed to calculate elbow angle for serve attempt {serve_attempt.id}"
                    )
                    failed_count += 1

            # Commit all updates
            db.commit()

            # Calculate average elbow angle
            avg_elbow_angle = (
                sum(elbow_angles) / len(elbow_angles) if elbow_angles else None
            )

            return {
                "video_id": video_id,
                "total_serves": len(serve_attempts),
                "analyzed": analyzed_count,
                "failed": failed_count,
                "skipped": skipped_count,
                "avg_elbow_angle": avg_elbow_angle,
                "elbow_angles": elbow_angles,
            }

        except Exception as e:
            logger.error(
                f"Error analyzing serve attempts for video {video_id}: {e}",
                exc_info=True,
            )
            raise

    def calculate_elbow_angle_at_contact(
        self,
        pose_data: Dict,
        contact_timestamp: float,
        video_fps: float,
        contact_hand: str,
    ) -> Optional[float]:
        """
        Calculate elbow angle at contact point from pose data.

        Uses existing posture_analysis.calculate_elbow_angle() logic.

        Args:
            pose_data: Pose landmarks dictionary
            contact_timestamp: Contact timestamp in seconds
            video_fps: Video FPS
            contact_hand: Which hand made contact ('left' or 'right')

        Returns:
            Elbow angle in degrees, or None if calculation failed
        """
        return calculate_elbow_angle(
            pose_landmarks=pose_data,
            contact_hand=contact_hand,
            stroke_type="serve",
        )
