"""
Video annotation API routes.
"""

from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.api.schemas.video_annotation import (
    VideoAnnotationDeleteResponse,
    VideoAnnotationInfo,
    VideoAnnotationListResponse,
    VideoAnnotationRequest,
    VideoAnnotationResponse,
)
from app.core.database import get_db
from app.models.video import Video
from app.services.video_annotation import VideoAnnotationService
from app.utils.error_handling import handle_not_found_error, handle_processing_error

router = APIRouter(prefix="/v0/video-annotation", tags=["video-annotation"])


@router.post("/create/{video_id}", response_model=VideoAnnotationResponse)
async def create_video_annotation(
    video_id: int,
    request: VideoAnnotationRequest = VideoAnnotationRequest(),
    db: Session = Depends(get_db),
) -> VideoAnnotationResponse:
    """
    Create an annotated video with detection overlays.

    Args:
        video_id: ID of the video to annotate
        request: Annotation request parameters
        db: Database session

    Returns:
        Video annotation response
    """
    try:
        # Verify video exists
        video = db.query(Video).filter(Video.id == video_id).first()
        if not video:
            raise handle_not_found_error("video", str(video_id))

        # Create annotation service
        annotation_service = VideoAnnotationService()

        # Create annotation based on type
        if request.annotation_type == "pose_only":
            annotation = annotation_service.create_pose_annotation(
                db=db,
                video_id=video_id,
                pose_detection_id=request.pose_detection_id,
                annotation_style=request.annotation_style,
            )
        else:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Unsupported annotation type: {request.annotation_type}",
            )

        # Convert to response format
        annotation_info = VideoAnnotationInfo(
            id=annotation.id,
            video_id=annotation.video_id,
            annotation_type=annotation.annotation_type,
            annotated_video_path=annotation.annotated_video_path,
            file_size_bytes=annotation.file_size_bytes,
            pose_detection_id=annotation.pose_detection_id,
            # ball_detection_id=annotation.ball_detection_id,  # Future
            analysis_id=annotation.analysis_id,
            processing_time_seconds=annotation.processing_time_seconds,
            frames_annotated=annotation.frames_annotated,
            annotation_style=annotation.annotation_style,
            status=annotation.status,
            error_message=annotation.error_message,
            created_at=annotation.created_at,
            completed_at=annotation.completed_at,
        )

        return VideoAnnotationResponse(
            success=True,
            message=f"Video annotation created successfully for video {video_id}",
            annotation=annotation_info,
        )

    except HTTPException:
        raise
    except (OSError, RuntimeError, ValueError) as e:
        raise handle_processing_error("video_annotation", str(e)) from e


@router.get("/{video_id}", response_model=VideoAnnotationResponse)
async def get_video_annotation(
    video_id: int,
    annotation_type: str = "pose_only",
    db: Session = Depends(get_db),
) -> VideoAnnotationResponse:
    """
    Get video annotation for a specific video.

    Args:
        video_id: ID of the video
        annotation_type: Type of annotation to retrieve
        db: Database session

    Returns:
        Video annotation response
    """
    try:
        # Verify video exists
        video = db.query(Video).filter(Video.id == video_id).first()
        if not video:
            raise handle_not_found_error("video", str(video_id))

        # Get annotation
        annotation_service = VideoAnnotationService()
        annotation = annotation_service.get_annotation_by_video_id(
            db=db, video_id=video_id, annotation_type=annotation_type
        )

        if not annotation:
            return VideoAnnotationResponse(
                success=False,
                message=f"No {annotation_type} annotation found for video {video_id}",
                annotation=None,
            )

        # Convert to response format
        annotation_info = VideoAnnotationInfo(
            id=annotation.id,
            video_id=annotation.video_id,
            annotation_type=annotation.annotation_type,
            annotated_video_path=annotation.annotated_video_path,
            file_size_bytes=annotation.file_size_bytes,
            pose_detection_id=annotation.pose_detection_id,
            # ball_detection_id=annotation.ball_detection_id,  # Future
            analysis_id=annotation.analysis_id,
            processing_time_seconds=annotation.processing_time_seconds,
            frames_annotated=annotation.frames_annotated,
            annotation_style=annotation.annotation_style,
            status=annotation.status,
            error_message=annotation.error_message,
            created_at=annotation.created_at,
            completed_at=annotation.completed_at,
        )

        return VideoAnnotationResponse(
            success=True,
            message="Video annotation retrieved successfully",
            annotation=annotation_info,
        )

    except HTTPException:
        raise
    except (OSError, RuntimeError, ValueError) as e:
        raise handle_processing_error("video_annotation", str(e)) from e


@router.get("/", response_model=VideoAnnotationListResponse)
async def list_video_annotations(
    video_id: Optional[int] = None,
    annotation_type: Optional[str] = None,
    db: Session = Depends(get_db),
) -> VideoAnnotationListResponse:
    """
    List video annotations with optional filtering.

    Args:
        video_id: Optional filter by video ID
        annotation_type: Optional filter by annotation type
        db: Database session

    Returns:
        List of video annotations
    """
    try:
        from app.models.video_annotation import VideoAnnotation

        # Build query
        query = db.query(VideoAnnotation)

        if video_id:
            query = query.filter(VideoAnnotation.video_id == video_id)

        if annotation_type:
            query = query.filter(VideoAnnotation.annotation_type == annotation_type)

        # Order by creation date
        annotations = query.order_by(VideoAnnotation.created_at.desc()).all()

        # Convert to response format
        annotation_infos = []
        for annotation in annotations:
            annotation_info = VideoAnnotationInfo(
                id=annotation.id,
                video_id=annotation.video_id,
                annotation_type=annotation.annotation_type,
                annotated_video_path=annotation.annotated_video_path,
                file_size_bytes=annotation.file_size_bytes,
                pose_detection_id=annotation.pose_detection_id,
                # ball_detection_id=annotation.ball_detection_id,  # Future
                analysis_id=annotation.analysis_id,
                processing_time_seconds=annotation.processing_time_seconds,
                frames_annotated=annotation.frames_annotated,
                annotation_style=annotation.annotation_style,
                status=annotation.status,
                error_message=annotation.error_message,
                created_at=annotation.created_at,
                completed_at=annotation.completed_at,
            )
            annotation_infos.append(annotation_info)

        return VideoAnnotationListResponse(
            annotations=annotation_infos,
            total_count=len(annotation_infos),
        )

    except (OSError, RuntimeError, ValueError) as e:
        raise handle_processing_error("video_annotation", str(e)) from e


@router.delete("/{annotation_id}", response_model=VideoAnnotationDeleteResponse)
async def delete_video_annotation(
    annotation_id: int,
    db: Session = Depends(get_db),
) -> VideoAnnotationDeleteResponse:
    """
    Delete a video annotation and its associated file.

    Args:
        annotation_id: ID of the annotation to delete
        db: Database session

    Returns:
        Deletion confirmation
    """
    try:
        annotation_service = VideoAnnotationService()
        success = annotation_service.delete_annotation(
            db=db, annotation_id=annotation_id
        )

        if not success:
            raise handle_not_found_error("video_annotation", str(annotation_id))

        return VideoAnnotationDeleteResponse(
            success=True,
            message=f"Video annotation {annotation_id} deleted successfully",
            annotation_id=annotation_id,
        )

    except HTTPException:
        raise
    except (OSError, RuntimeError, ValueError) as e:
        raise handle_processing_error("video_annotation", str(e)) from e
