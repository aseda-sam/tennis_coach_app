"""
API routes for pose detection analysis.
"""

import logging

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.api.schemas.pose_detection import (
    PoseDetectionInfo,
    PoseDetectionMetrics,
    PoseDetectionRequest,
    PoseDetectionResponse,
    PoseDetectionStartResponse,
)
from app.core.database import get_db
from app.models.video import Video
from app.services.pose_detection import PoseDetectionService
from app.utils.error_handling import handle_processing_error

router = APIRouter(prefix="/v0/pose-detection", tags=["pose-detection"])
logger = logging.getLogger(__name__)


@router.post("/analyze/{video_id}", response_model=PoseDetectionStartResponse)
async def analyze_pose_detection(
    video_id: int,
    request: PoseDetectionRequest = PoseDetectionRequest(),
    db: Session = Depends(get_db),
) -> PoseDetectionStartResponse:
    """
    Start pose detection analysis for a video.

    This endpoint analyzes a video for human pose detection using MediaPipe.
    The analysis identifies key body landmarks and tracks pose quality metrics.
    """
    try:
        # Verify video exists
        video = db.query(Video).filter(Video.id == video_id).first()
        if not video:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Video with ID {video_id} not found",
            )

        # Check for existing pose detection
        pose_service = PoseDetectionService()
        existing_detection = pose_service.get_detection_by_video_id(db, video_id)

        if existing_detection and existing_detection.status == "completed":
            return PoseDetectionStartResponse(
                pose_detection_id=existing_detection.id,
                video_filename=video.filename,
                status="completed",
                message="Pose detection already completed for this video",
                estimated_duration=existing_detection.processing_time_seconds,
                task_id=None,
            )

        # Delete any failed existing detection
        if existing_detection and existing_detection.status == "failed":
            db.delete(existing_detection)
            db.commit()

        # Run pose detection analysis
        from pathlib import Path

        video_path = Path(video.file_path)
        if not video_path.exists():
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Video file not found: {video.file_path}",
            )

        # Perform pose detection analysis
        detection_results = pose_service.analyze_video_file(
            video_path=video_path,
            confidence_threshold=request.confidence_threshold,
            detection_threshold=request.detection_threshold,
            max_frames=request.max_frames,
        )

        # Check for analysis errors
        if "error" in detection_results:
            raise handle_processing_error("pose_detection", detection_results["error"])

        # Save results to database
        pose_detection = pose_service.save_detection_results(
            db, video_id, detection_results
        )

        # Create annotated video if pose detection was successful
        try:
            from app.services.video_annotation import VideoAnnotationService

            annotation_service = VideoAnnotationService()
            annotation = annotation_service.create_pose_annotation(
                db=db,
                video_id=video_id,
                pose_detection_id=pose_detection.id,
                annotation_style="standard",
            )
            logger.info(f"Created pose annotation {annotation.id} for video {video_id}")
        except (OSError, ValueError, RuntimeError) as e:
            logger.warning(
                f"Failed to create pose annotation for video {video_id}: {e}"
            )
            # Don't fail the entire operation if annotation creation fails

        return PoseDetectionStartResponse(
            pose_detection_id=pose_detection.id,
            video_filename=video.filename,
            status="completed",
            message="Pose detection analysis completed successfully",
            estimated_duration=detection_results.get("processing_time_seconds", 0.0),
            task_id=None,
        )

    except HTTPException:
        raise
    except (OSError, RuntimeError, ValueError) as e:
        raise handle_processing_error("pose_detection", str(e)) from e


@router.get("/{video_id}", response_model=PoseDetectionResponse)
async def get_pose_detection(
    video_id: int,
    include_pose_data: bool = False,
    db: Session = Depends(get_db),
) -> PoseDetectionResponse:
    """
    Get pose detection results for a video.

    Returns the most recent pose detection analysis results for the specified video.

    Args:
        video_id: ID of the video
        include_pose_data: If True, includes frame-by-frame pose keypoint data
        db: Database session
    """
    try:
        # Verify video exists
        video = db.query(Video).filter(Video.id == video_id).first()
        if not video:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Video with ID {video_id} not found",
            )

        # Get pose detection results
        pose_service = PoseDetectionService()
        pose_detection = pose_service.get_detection_by_video_id(db, video_id)

        if not pose_detection:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"No pose detection found for video {video_id}",
            )

        # Build metrics object
        metrics = PoseDetectionMetrics(
            total_frames=pose_detection.total_frames,
            frames_with_poses=pose_detection.frames_with_poses,
            total_pose_detections=pose_detection.total_pose_detections,
            detection_rate=pose_detection.detection_rate,
            average_pose_confidence=pose_detection.average_pose_confidence,
            min_pose_confidence=pose_detection.min_pose_confidence,
            max_pose_confidence=pose_detection.max_pose_confidence,
            pose_stability_score=pose_detection.pose_stability_score,
            confidence_threshold=pose_detection.confidence_threshold,
            detection_threshold=pose_detection.detection_threshold,
            processing_time_seconds=pose_detection.processing_time_seconds,
            frame_processing_rate=pose_detection.frame_processing_rate,
        )

        # Get frame-by-frame pose data if requested
        frame_data = None
        if include_pose_data:
            frame_data = pose_service.get_formatted_pose_data(pose_detection)

        # Build pose detection info
        pose_info = PoseDetectionInfo(
            id=pose_detection.id,
            video_id=pose_detection.video_id,
            metrics=metrics,
            frame_data=frame_data,
            created_at=pose_detection.created_at,
            completed_at=pose_detection.completed_at,
            status=pose_detection.status,
            error_message=pose_detection.error_message,
        )

        return PoseDetectionResponse(
            pose_detection=pose_info,
            message="Pose detection results retrieved successfully",
        )

    except HTTPException:
        raise
    except (OSError, RuntimeError, ValueError) as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to retrieve pose detection: {e!s}",
        ) from e
