"""Overlay data API routes for client-side rendering."""

import json
import logging
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.api.schemas.overlay_data import PoseOverlayData, PoseFrame
from app.core.database import get_db
from app.dependencies.auth import get_current_user
from app.models.pose_detection import PoseDetection
from app.models.video import Video
from app.utils.authorization import require_video_access
from app.utils.error_handling import handle_not_found_error

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/v0/videos", tags=["overlay-data"])


@router.get("/{video_id}/overlay-data", response_model=PoseOverlayData)
async def get_overlay_data(
    video_id: int,
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> PoseOverlayData:
    """
    Get overlay data for client-side rendering.

    Formats existing pose detection data for frontend overlay rendering.
    No new analysis - just formatting existing data.

    Args:
        video_id: Video ID to get overlay data for

    Returns:
        PoseOverlayData with frame-by-frame pose keypoints
    """
    try:
        # Verify video exists
        video = db.query(Video).filter(Video.id == video_id).first()
        if not video:
            raise handle_not_found_error("video", str(video_id))

        # Check authorization
        require_video_access(video, current_user)

        # Get pose detection record
        pose_detection = (
            db.query(PoseDetection)
            .filter(PoseDetection.video_id == video_id)
            .order_by(PoseDetection.created_at.desc())
            .first()
        )

        if not pose_detection:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"No pose detection found for video {video_id}",
            )

        if pose_detection.status != "completed":
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Pose detection {pose_detection.id} is not completed",
            )

        # Parse pose data
        if not pose_detection.pose_data:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"No pose data available for video {video_id}",
            )

        try:
            raw_pose_data = json.loads(pose_detection.pose_data)
            confidence_scores = (
                json.loads(pose_detection.confidence_scores)
                if pose_detection.confidence_scores
                else []
            )
        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse pose data JSON: {e}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to parse pose detection data",
            ) from e

        # Get video FPS (required for timestamp calculation)
        fps = video.fps
        if not fps or fps <= 0:
            fps = 30.0  # Default fallback
            logger.warning(f"Invalid FPS for video {video_id}, using default 30.0")

        # Format frames
        frames: list[PoseFrame] = []
        for frame_index, frame_pose_data in enumerate(raw_pose_data):
            # Calculate timestamp
            timestamp = frame_index / fps if fps > 0 else 0.0

            # Get confidence for this frame
            confidence = (
                confidence_scores[frame_index]
                if frame_index < len(confidence_scores)
                else 0.0
            )

            # Format keypoints as dict (for frontend consumption)
            # Keep original format: {"left_shoulder": [x, y], ...}
            keypoints_dict: dict[str, list[float]] = {}
            if frame_pose_data:
                for keypoint_name, coordinates in frame_pose_data.items():
                    if isinstance(coordinates, list) and len(coordinates) >= 2:
                        # Store as [x, y] - frontend can add confidence if needed
                        keypoints_dict[keypoint_name] = [
                            float(coordinates[0]),
                            float(coordinates[1]),
                        ]

            frames.append(
                PoseFrame(
                    frame_index=frame_index,
                    timestamp=timestamp,
                    keypoints=keypoints_dict,
                    confidence=float(confidence) if confidence is not None else 0.0,
                )
            )

        # Get video dimensions
        width = video.width or 0
        height = video.height or 0

        return PoseOverlayData(
            video_id=video_id,
            fps=fps,
            total_frames=pose_detection.total_frames,
            width=width,
            height=height,
            frames=frames,
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting overlay data for video {video_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get overlay data: {e!s}",
        ) from e
