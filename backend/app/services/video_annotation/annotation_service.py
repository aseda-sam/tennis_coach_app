"""
Video annotation service for cleanup operations.

Note: Video encoding functionality has been removed. This service now only
provides methods for cleaning up existing annotation records.
"""

import logging
from typing import Optional

from sqlalchemy.orm import Session

from app.models.video_annotation import VideoAnnotation
from app.services.storage_service import storage_service

logger = logging.getLogger(__name__)


class VideoAnnotationService:
    """Service for cleanup operations on video annotation records."""

    def get_annotation_by_video_id(
        self, db: Session, video_id: int, annotation_type: Optional[str] = None
    ) -> Optional[VideoAnnotation]:
        """
        Get video annotation for a video.

        Args:
            db: Database session
            video_id: ID of the video
            annotation_type: Optional filter by annotation type

        Returns:
            VideoAnnotation record if exists, None otherwise
        """
        query = db.query(VideoAnnotation).filter(VideoAnnotation.video_id == video_id)

        if annotation_type:
            query = query.filter(VideoAnnotation.annotation_type == annotation_type)

        return query.order_by(VideoAnnotation.created_at.desc()).first()

    def delete_annotation(self, db: Session, annotation_id: int) -> bool:
        """
        Delete a video annotation and its file.

        Args:
            db: Database session
            annotation_id: ID of the annotation to delete

        Returns:
            True if deleted successfully, False otherwise
        """
        annotation = (
            db.query(VideoAnnotation)
            .filter(VideoAnnotation.id == annotation_id)
            .first()
        )
        if not annotation:
            return False

        # Delete file using storage service (handles both local and Supabase)
        if annotation.annotated_video_path:
            try:
                storage_service.delete_file(annotation.annotated_video_path)
                logger.info(
                    f"Deleted annotated video file: {annotation.annotated_video_path}"
                )
            except (ValueError, RuntimeError, OSError) as e:
                logger.warning(
                    f"Failed to delete annotated video file {annotation.annotated_video_path}: {e}"
                )

        # Delete database record
        db.delete(annotation)
        db.commit()
        logger.info(f"Deleted video annotation {annotation_id}")
        return True
