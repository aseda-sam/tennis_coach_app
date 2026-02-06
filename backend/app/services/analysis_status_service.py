"""Service for video analysis status operations."""

from typing import Dict, List

from sqlalchemy.orm import Session

from app.models.pose_detection import PoseDetection
from app.models.video import Video
from app.services import video_service


def get_video_analysis_status(db: Session, video_id: int) -> dict:
    """Get analysis status for a single video.

    Args:
        db: Database session
        video_id: Video ID

    Returns:
        Dict with video_id, has_analysis (bool), and analysis_types (list)

    Raises:
        ValueError: If video not found
    """
    db_video = video_service.get_video_by_id(db, video_id)
    if not db_video:
        raise ValueError(f"Video with ID {video_id} not found")

    analysis_types = []
    has_analysis = False

    # Check for pose detection
    pose_detection = (
        db.query(PoseDetection).filter(PoseDetection.video_id == video_id).first()
    )
    if pose_detection and pose_detection.status == "completed":
        has_analysis = True
        analysis_types.append("pose_detection")

    return {
        "video_id": video_id,
        "has_analysis": has_analysis,
        "analysis_types": analysis_types,
    }


def get_bulk_analysis_status(
    db: Session,
    video_ids: List[int],
    user_id: str,
    is_admin: bool = False,
) -> List[dict]:
    """Get analysis status for multiple videos in bulk.

    Args:
        db: Database session
        video_ids: List of video IDs to check
        user_id: User ID for authorization check
        is_admin: Whether the user is an admin (admins can see all videos)

    Returns:
        List of analysis status dicts, one per video_id

    Raises:
        ValueError: If any video not found or access denied
    """
    # Verify all videos exist and user has access
    query = db.query(Video).filter(Video.id.in_(video_ids))
    if not is_admin:
        query = query.filter(Video.user_id == user_id)

    accessible_videos = {video.id for video in query.all()}

    # Check for unauthorized access
    unauthorized_ids = set(video_ids) - accessible_videos
    if unauthorized_ids:
        raise ValueError(f"Videos not found or access denied: {list(unauthorized_ids)}")

    # Fetch all pose detections in one query
    pose_detections = (
        db.query(PoseDetection)
        .filter(
            PoseDetection.video_id.in_(video_ids),
            PoseDetection.status == "completed",
        )
        .all()
    )

    # Build lookup maps for O(1) access
    pose_map: Dict[int, PoseDetection] = {pd.video_id: pd for pd in pose_detections}

    # Build response for each video
    statuses = []
    for video_id in video_ids:
        analysis_types = []
        has_analysis = False

        if video_id in pose_map:
            has_analysis = True
            analysis_types.append("pose_detection")

        statuses.append(
            {
                "video_id": video_id,
                "has_analysis": has_analysis,
                "analysis_types": analysis_types,
            }
        )

    return statuses
