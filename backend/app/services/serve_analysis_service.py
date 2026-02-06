"""Serve-specific analysis service for calculating elbow angles at contact."""

import json
import logging
from typing import Dict, List, Optional

from sqlalchemy.orm import Session

from app.models.player import Player
from app.models.pose_detection import PoseDetection
from app.models.serve_attempt import ServeAttempt
from app.models.video import Video
from app.services.posture_analysis import (
    calculate_elbow_angle,
    calculate_knee_angle,
    calculate_knee_hip_ratio,
)

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


def _select_best_pose_detection(db: Session, video_id: int) -> Optional[PoseDetection]:
    """
    Select the best pose detection record for analysis.

    Prefers: latest 'refine' > latest 'full' > latest 'scout'.
    Always orders by created_at desc for deterministic selection.

    Args:
        db: Database session
        video_id: Video ID

    Returns:
        Best PoseDetection record, or None if none found
    """
    # Query all completed pose detections for this video, ordered by created_at desc
    all_detections = (
        db.query(PoseDetection)
        .filter(
            PoseDetection.video_id == video_id,
            PoseDetection.status == "completed",
        )
        .order_by(PoseDetection.created_at.desc())
        .all()
    )

    if not all_detections:
        return None

    # Prefer refine > full > scout
    for detection in all_detections:
        if detection.detection_mode == "refine":
            logger.info(
                "Selected refine pose detection %s for video %s",
                detection.id,
                video_id,
            )
            return detection

    for detection in all_detections:
        if detection.detection_mode == "full":
            logger.info(
                "Selected full pose detection %s for video %s",
                detection.id,
                video_id,
            )
            return detection

    # Fall back to scout (or any other mode)
    detection = all_detections[0]
    logger.info(
        "Selected %s pose detection %s for video %s",
        detection.detection_mode,
        detection.id,
        video_id,
    )
    return detection


def get_pose_frames_in_window(
    pose_detection: PoseDetection,
    video: Video,
    start_timestamp: float,
    end_timestamp: float,
) -> List[Optional[Dict]]:
    """
    Get pose data for all frames within a time window.

    Args:
        pose_detection: PoseDetection object with pose_data
        video: Video object with fps metadata
        start_timestamp: Start timestamp in seconds
        end_timestamp: End timestamp in seconds

    Returns:
        List of pose landmarks dictionaries (one per frame), or None for frames without pose
    """
    try:
        if not pose_detection.pose_data:
            logger.warning("No pose data available")
            return []

        # Deserialize pose data
        raw_pose_data = json.loads(pose_detection.pose_data)

        if not raw_pose_data:
            logger.warning("Empty pose data")
            return []

        # Calculate frame range from timestamps and FPS
        fps = video.fps if video.fps else 30.0
        start_frame = int(start_timestamp * fps)
        end_frame = int(end_timestamp * fps)

        # Extract frames in window
        frames = []
        for frame_idx in range(start_frame, min(end_frame + 1, len(raw_pose_data))):
            if frame_idx < len(raw_pose_data):
                frame_data = raw_pose_data[frame_idx]
                keypoints = _extract_keypoints(frame_data)
                frames.append(keypoints)
            else:
                frames.append(None)

        return frames

    except (json.JSONDecodeError, ValueError, KeyError) as e:
        logger.error("Error getting pose frames in window: %s", e)
        return []


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

        logger.warning("No pose data found near timestamp %ss", timestamp)
        return None

    except (json.JSONDecodeError, ValueError, KeyError) as e:
        logger.error("Error getting pose at timestamp: %s", e)
        return None


def _compute_knee_bend_metrics(
    pose_detection: PoseDetection,
    video: Video,
    serve_attempt: ServeAttempt,
    camera_angle: Optional[str],
) -> Dict[str, any]:
    """
    Compute knee bend metrics for a serve attempt during the early loading phase.

    Args:
        pose_detection: PoseDetection object with pose_data
        video: Video object with fps metadata
        serve_attempt: ServeAttempt with start/end/contact timestamps
        camera_angle: Camera angle from video ('profile', 'behind', etc.)

    Returns:
        Dictionary with knee bend metrics and status:
        - knee_bend_detected: bool
        - knee_bend_confidence: float (0-1)
        - knee_hip_ratio_min: float
        - knee_flexion_min_deg_left: float or None
        - knee_flexion_min_deg_right: float or None
        - status: str ('computed', 'computed_low_confidence', 'insufficient_pose_data')
    """
    # Determine analysis window (early portion of serve)
    window_start = serve_attempt.start_timestamp
    if serve_attempt.contact_timestamp:
        # Use first 50-60% of window before contact
        window_duration = serve_attempt.contact_timestamp - window_start
        window_end = window_start + (window_duration * 0.55)  # 55% of window
        # Cap at 2.0s max
        window_end = min(window_end, window_start + 2.0)
    else:
        # Use first 1.5-2.0s of window
        window_end = min(
            serve_attempt.start_timestamp + 1.75, serve_attempt.end_timestamp
        )

    # Get pose frames in window
    pose_frames = get_pose_frames_in_window(
        pose_detection, video, window_start, window_end
    )

    if not pose_frames:
        return {
            "knee_bend_detected": False,
            "knee_bend_confidence": 0.0,
            "knee_hip_ratio_min": None,
            "knee_flexion_min_deg_left": None,
            "knee_flexion_min_deg_right": None,
            "status": "insufficient_pose_data",
        }

    # Filter out None frames (no pose detected)
    valid_frames = [f for f in pose_frames if f is not None]

    if len(valid_frames) < 3:  # Need at least a few frames for reliable metrics
        return {
            "knee_bend_detected": False,
            "knee_bend_confidence": 0.0,
            "knee_hip_ratio_min": None,
            "knee_flexion_min_deg_left": None,
            "knee_flexion_min_deg_right": None,
            "status": "insufficient_pose_data",
        }

    # Compute metrics across valid frames
    knee_hip_ratios = []
    knee_angles_left = []
    knee_angles_right = []

    frame_shape = (video.height or 720, video.width or 1280, 3)

    for frame_landmarks in valid_frames:
        # Calculate knee-hip ratio
        ratio = calculate_knee_hip_ratio(frame_landmarks, frame_shape)
        if ratio is not None:
            knee_hip_ratios.append(ratio)

        # Calculate knee flexion angles
        angle_left = calculate_knee_angle(frame_landmarks, "left")
        if angle_left is not None:
            knee_angles_left.append(angle_left)

        angle_right = calculate_knee_angle(frame_landmarks, "right")
        if angle_right is not None:
            knee_angles_right.append(angle_right)

    # Determine status and confidence
    pose_coverage = len(valid_frames) / len(pose_frames) if pose_frames else 0.0
    has_ratio_data = len(knee_hip_ratios) > 0
    has_angle_data = len(knee_angles_left) > 0 or len(knee_angles_right) > 0

    if not has_ratio_data and not has_angle_data:
        return {
            "knee_bend_detected": False,
            "knee_bend_confidence": 0.0,
            "knee_hip_ratio_min": None,
            "knee_flexion_min_deg_left": None,
            "knee_flexion_min_deg_right": None,
            "status": "insufficient_pose_data",
        }

    # Compute minimums (more bend = lower ratio, lower angle)
    knee_hip_ratio_min = min(knee_hip_ratios) if knee_hip_ratios else None
    knee_flexion_min_left = min(knee_angles_left) if knee_angles_left else None
    knee_flexion_min_right = min(knee_angles_right) if knee_angles_right else None

    # Determine if knee bend was detected (heuristic: ratio < threshold or angle < threshold)
    # Lower ratio = more bend; lower angle = more flexion
    ratio_threshold = 0.3  # Empirical: adjust based on testing
    angle_threshold = 140.0  # Degrees: < 140° indicates significant bend

    detected = False
    if (
        (knee_hip_ratio_min is not None and knee_hip_ratio_min < ratio_threshold)
        or (
            knee_flexion_min_left is not None
            and knee_flexion_min_left < angle_threshold
        )
        or (
            knee_flexion_min_right is not None
            and knee_flexion_min_right < angle_threshold
        )
    ):
        detected = True

    # Calculate confidence based on pose coverage and data quality
    confidence = pose_coverage * 0.7  # Base confidence from coverage
    if has_ratio_data and has_angle_data:
        confidence += 0.2  # Bonus for having both metrics
    if len(valid_frames) >= 10:
        confidence += 0.1  # Bonus for sufficient frame count
    confidence = min(confidence, 1.0)

    # Adjust confidence based on camera angle
    if camera_angle == "profile":
        # Profile view is best for knee bend detection
        confidence = min(confidence * 1.1, 1.0)
    elif camera_angle == "behind":
        # Behind view can work but may have occlusion
        confidence = confidence * 0.9

    # Determine status
    status = "computed_low_confidence" if confidence < 0.5 else "computed"

    return {
        "knee_bend_detected": detected,
        "knee_bend_confidence": round(confidence, 3),
        "knee_hip_ratio_min": round(knee_hip_ratio_min, 4)
        if knee_hip_ratio_min is not None
        else None,
        "knee_flexion_min_deg_left": round(knee_flexion_min_left, 1)
        if knee_flexion_min_left is not None
        else None,
        "knee_flexion_min_deg_right": round(knee_flexion_min_right, 1)
        if knee_flexion_min_right is not None
        else None,
        "status": status,
    }


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

            pose_detection = _select_best_pose_detection(db, video_id)

            if not pose_detection:
                raise ValueError(
                    f"No completed pose detection found for video {video_id}. "
                    "Please run pose detection first."
                )

            analyzed_count = 0
            failed_count = 0
            skipped_count = 0
            elbow_angles: List[float] = []
            knee_bend_analyzed_count = 0
            knee_bend_failed_count = 0

            # Set analysis version
            analysis_version = "v1.0"

            for serve_attempt in serve_attempts:
                # Compute knee bend metrics (for all serves, not just those with contact)
                try:
                    knee_metrics = _compute_knee_bend_metrics(
                        pose_detection, video, serve_attempt, video.camera_angle
                    )

                    # Store knee bend results
                    serve_attempt.knee_bend_detected = knee_metrics[
                        "knee_bend_detected"
                    ]
                    serve_attempt.knee_bend_confidence = knee_metrics[
                        "knee_bend_confidence"
                    ]
                    serve_attempt.knee_hip_ratio_min = knee_metrics[
                        "knee_hip_ratio_min"
                    ]
                    serve_attempt.knee_flexion_min_deg_left = knee_metrics[
                        "knee_flexion_min_deg_left"
                    ]
                    serve_attempt.knee_flexion_min_deg_right = knee_metrics[
                        "knee_flexion_min_deg_right"
                    ]
                    serve_attempt.analysis_version = analysis_version

                    if knee_metrics["status"] != "insufficient_pose_data":
                        knee_bend_analyzed_count += 1
                        logger.debug(
                            "Computed knee bend metrics for serve attempt %s: detected=%s, confidence=%.2f",
                            serve_attempt.id,
                            knee_metrics["knee_bend_detected"],
                            knee_metrics["knee_bend_confidence"],
                        )
                    else:
                        knee_bend_failed_count += 1
                        logger.debug(
                            "Insufficient pose data for knee bend analysis on serve attempt %s",
                            serve_attempt.id,
                        )
                except Exception as e:  # noqa: BLE001 - Catch all exceptions to continue batch processing
                    logger.warning(
                        "Error computing knee bend metrics for serve attempt %s: %s",
                        serve_attempt.id,
                        e,
                        exc_info=True,
                    )
                    knee_bend_failed_count += 1

                # Compute elbow angle (only if contact timestamp exists)
                if not serve_attempt.contact_timestamp:
                    logger.debug(
                        "Skipping elbow angle for serve attempt %s - no contact timestamp",
                        serve_attempt.id,
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
                        "Player %s not found for serve attempt %s",
                        serve_attempt.player_id,
                        serve_attempt.id,
                    )
                    failed_count += 1
                    continue

                # Get pose data at contact timestamp
                pose_landmarks = get_pose_at_timestamp(
                    pose_detection, video, serve_attempt.contact_timestamp
                )

                if not pose_landmarks:
                    logger.warning(
                        "No pose data found for serve attempt %s at timestamp %ss",
                        serve_attempt.id,
                        serve_attempt.contact_timestamp,
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
                            "Elbow angle %.1f° is outside valid range (0-180°) for serve attempt %s",
                            elbow_angle,
                            serve_attempt.id,
                        )
                        failed_count += 1
                        continue

                    # Store result
                    serve_attempt.elbow_angle_at_contact = elbow_angle
                    elbow_angles.append(elbow_angle)
                    analyzed_count += 1
                    logger.debug(
                        "Calculated elbow angle %.1f° for serve attempt %s",
                        elbow_angle,
                        serve_attempt.id,
                    )
                else:
                    logger.warning(
                        "Failed to calculate elbow angle for serve attempt %s",
                        serve_attempt.id,
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
                "knee_bend_analyzed": knee_bend_analyzed_count,
                "knee_bend_failed": knee_bend_failed_count,
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
