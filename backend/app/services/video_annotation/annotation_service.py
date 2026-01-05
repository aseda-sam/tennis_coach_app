"""
Video annotation service for creating annotated videos with detection overlays.
"""

import json
import logging
import time
import uuid
from contextlib import contextmanager
from datetime import datetime
from pathlib import Path
from typing import Dict, Optional, Tuple

import cv2
import numpy as np
from sqlalchemy.orm import Session

from app.core.config import settings
from app.models.pose_detection import PoseDetection
from app.models.video import Video
from app.models.video_annotation import VideoAnnotation
from app.services.storage_service import storage_service

logger = logging.getLogger(__name__)


@contextmanager
def video_writer_with_fallback(
    path: str, fps: float, size: Tuple[int, int]
) -> cv2.VideoWriter:
    """
    Context manager for cv2.VideoWriter with automatic codec fallback and cleanup.

    Tries multiple codecs in order: H264 -> avc1 -> mp4v
    Ensures proper cleanup even if codec selection fails.

    Args:
        path: Output video file path
        fps: Frames per second
        size: Video dimensions (width, height)

    Yields:
        cv2.VideoWriter instance if successful

    Raises:
        RuntimeError: If no codec works
    """
    # Try multiple codecs with fallback (H.264 should be available with opencv-python, but fallback for safety)
    # Order: H264 (best) -> avc1 (H.264 alternative) -> mp4v (widely supported)
    codecs_to_try = [
        ("H264", "H.264"),
        ("avc1", "H.264 (avc1)"),
        ("mp4v", "MPEG-4"),
    ]

    writer: Optional[cv2.VideoWriter] = None

        for fourcc_str, codec_name in codecs_to_try:
        try:
            fourcc = cv2.VideoWriter_fourcc(*fourcc_str)
            writer = cv2.VideoWriter(path, fourcc, fps, size)

            if writer.isOpened():
                logger.info(
                    f"Successfully created video writer with {codec_name} codec at {path}, fps={fps}, size={size}"
                )
                break
            else:
                logger.warning(f"VideoWriter.isOpened() returned False for {codec_name} codec")
                writer.release()
                writer = None
        except (OSError, RuntimeError, ValueError) as e:
            logger.warning(f"Failed to use {codec_name} codec: {e}")
            if writer:
                writer.release()
                writer = None
            continue

    if not writer or not writer.isOpened():
        raise RuntimeError("Failed to create video writer with any available codec")

    try:
        yield writer
    finally:
        if writer is not None:
            writer.release()


class VideoAnnotationService:
    """Service for creating annotated videos with detection overlays."""

    def __init__(self) -> None:
        """Initialize the video annotation service."""
        self.logger = logger

    def create_pose_annotation(
        self,
        db: Session,
        video_id: int,
        pose_detection_id: Optional[int] = None,
        annotation_style: str = "standard",
    ) -> VideoAnnotation:
        """
        Create an annotated video with pose detection overlays.

        Args:
            db: Database session
            video_id: ID of the video to annotate
            pose_detection_id: Optional specific pose detection to use
            annotation_style: Style of annotation ('standard', 'debug', 'presentation')

        Returns:
            VideoAnnotation record
        """
        start_time = time.time()
        logger.info(f"Starting pose annotation for video {video_id}")

        # Get video
        video = db.query(Video).filter(Video.id == video_id).first()
        if not video:
            raise ValueError(f"Video {video_id} not found")

        # Get pose detection data
        if pose_detection_id:
            pose_detection = (
                db.query(PoseDetection)
                .filter(
                    PoseDetection.id == pose_detection_id,
                    PoseDetection.video_id == video_id,
                )
                .first()
            )
        else:
            # Get most recent pose detection for this video
            pose_detection = (
                db.query(PoseDetection)
                .filter(PoseDetection.video_id == video_id)
                .order_by(PoseDetection.created_at.desc())
                .first()
            )

        if not pose_detection:
            raise ValueError(f"No pose detection found for video {video_id}")

        if pose_detection.status != "completed":
            raise ValueError(f"Pose detection {pose_detection.id} is not completed")

        # Get video file for processing
        # For Supabase, download to temp file. For local, use file_path directly.
        video_path = None
        temp_video_path = None
        try:
            if settings.STORAGE_TYPE == "supabase":
                # Download video from Supabase to temp file for processing
                logger.info(f"Downloading video from Supabase: {video.file_path}")
                video_content = storage_service.download_file(video.file_path)
                # Create temp file for processing
                import tempfile

                with tempfile.NamedTemporaryFile(
                    delete=False, suffix=".mp4", dir=settings.PROCESSED_DIR
                ) as temp_video_file:
                    temp_video_file.write(video_content)
                    temp_video_path = Path(temp_video_file.name)
                video_path = temp_video_path
            else:
                # For local storage, use file_path directly
                video_path = Path(video.file_path)

            # Create annotated video
            annotated_video_path = self._create_pose_annotated_video(
                video_path, pose_detection, annotation_style
            )

            if not annotated_video_path:
                raise RuntimeError("Failed to create annotated video")

            # Upload annotated video to storage if using Supabase
            annotated_storage_path = str(annotated_video_path)
            if settings.STORAGE_TYPE == "supabase":
                # Read the annotated video file
                with open(annotated_video_path, "rb") as f:
                    annotated_content = f.read()

                # Upload to Supabase with processed/ prefix
                # Extract just the filename from the local path
                annotated_filename = annotated_video_path.name
                supabase_path = f"processed/{annotated_filename}"
                storage_service.upload_file(
                    file_content=annotated_content,
                    file_path=supabase_path,
                    content_type="video/mp4",
                )
                annotated_storage_path = supabase_path
                logger.info(f"Uploaded annotated video to Supabase: {supabase_path}")

            # Get file size
            file_size = (
                annotated_video_path.stat().st_size
                if annotated_video_path.exists()
                else None
            )

            # Create annotation record
            annotation = VideoAnnotation(
                video_id=video_id,
                annotation_type="pose_only",
                annotated_video_path=annotated_storage_path,
                file_size_bytes=file_size,
                pose_detection_id=pose_detection.id,
                processing_time_seconds=time.time() - start_time,
                frames_annotated=pose_detection.total_frames,
                annotation_style=annotation_style,
                status="completed",
                completed_at=datetime.now(),
            )

            db.add(annotation)
            db.commit()
            db.refresh(annotation)

            logger.info(f"Created pose annotation {annotation.id} for video {video_id}")
            return annotation
        finally:
            # Clean up temp video file if created
            if temp_video_path and temp_video_path.exists():
                try:
                    temp_video_path.unlink()
                    logger.debug(f"Cleaned up temp video file: {temp_video_path}")
                except OSError as e:
                    logger.warning(
                        f"Failed to delete temp video file {temp_video_path}: {e}"
                    )

    def _create_pose_annotated_video(
        self,
        video_path: Path,
        pose_detection: PoseDetection,
        annotation_style: str = "standard",
    ) -> Optional[Path]:
        """
        Create an annotated video with pose detection overlays.

        Args:
            video_path: Path to original video
            pose_detection: Pose detection data
            annotation_style: Style of annotation

        Returns:
            Path to annotated video file
        """
        logger.info(f"Creating pose annotated video for {video_path}")

        # Parse pose data
        pose_data = (
            json.loads(pose_detection.pose_data) if pose_detection.pose_data else []
        )
        confidence_scores = (
            json.loads(pose_detection.confidence_scores)
            if pose_detection.confidence_scores
            else []
        )

        if not pose_data:
            logger.warning("No pose data available for annotation")
            return None

        # Open video
        cap = cv2.VideoCapture(str(video_path))
        if not cap.isOpened():
            logger.error(f"Could not open video: {video_path}")
            return None

        # Get video properties
        fps = cap.get(cv2.CAP_PROP_FPS)
        width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
        height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
        total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
        
        logger.info(f"Opened video: {video_path}, properties: {width}x{height}, {fps} fps, {total_frames} frames")

        # Validate FPS
        if fps <= 0 or fps > 120:
            logger.warning(f"Invalid FPS: {fps}, using 30 fps")
            fps = 30.0

        logger.info(
            f"Video properties: {width}x{height}, {fps} fps, {total_frames} frames"
        )

        # Create output path
        output_dir = Path(settings.PROCESSED_DIR)
        output_dir.mkdir(parents=True, exist_ok=True)

        base_name = video_path.stem
        annotated_filename = f"{base_name}_pose_annotated.mp4"
        annotated_path = output_dir / annotated_filename

        # Handle file conflicts
        if annotated_path.exists():
            # Add unique suffix
            unique_suffix = str(uuid.uuid4())[:8]
            annotated_filename = f"{base_name}_pose_annotated_{unique_suffix}.mp4"
            annotated_path = output_dir / annotated_filename

        logger.info(f"Creating annotated video: {annotated_path}")

        # Process frames with context manager for automatic cleanup
        frame_count = 0
        annotated_frames = 0

        try:
            with video_writer_with_fallback(
                str(annotated_path), fps, (width, height)
            ) as out:
                while True:
                    ret, frame = cap.read()
                    if not ret:
                        break

                    # Get pose data for this frame
                    frame_pose_data = (
                        pose_data[frame_count] if frame_count < len(pose_data) else None
                    )
                    frame_confidence = (
                        confidence_scores[frame_count]
                        if frame_count < len(confidence_scores)
                        else 0.0
                    )

                    # Annotate frame if pose data exists
                    if frame_pose_data and frame_confidence > 0.5:
                        annotated_frame = self._draw_pose_overlay(
                            frame, frame_pose_data, frame_confidence, annotation_style
                        )
                        write_success = out.write(annotated_frame)
                        if not write_success:
                            logger.warning(f"Failed to write annotated frame {frame_count}")
                        annotated_frames += 1
                    else:
                        # Write original frame if no pose detected
                        write_success = out.write(frame)
                        if not write_success:
                            logger.warning(f"Failed to write frame {frame_count}")

                    frame_count += 1

                    # Progress logging
                    if frame_count % 100 == 0:
                        logger.info(f"Processed {frame_count}/{total_frames} frames (annotated: {annotated_frames})")
                    elif frame_count == 1:
                        logger.info(f"Started processing frames (total: {total_frames})")

        except RuntimeError as e:
            logger.error(f"Failed to create video writer: {e}")
            cap.release()
            return None
        except (OSError, ValueError) as e:
            logger.error(f"Error processing video frames: {e}")
            cap.release()
            return None
        finally:
            cap.release()

        # Validate output
        if annotated_path.exists():
            file_size = annotated_path.stat().st_size
            logger.info(f"Annotated video file created: {annotated_path}, size: {file_size} bytes, frames: {frame_count}, annotated: {annotated_frames}")
            if file_size > 0:
                logger.info(f"Successfully created pose annotated video: {annotated_path}")
                logger.info(f"Annotated {annotated_frames}/{frame_count} frames")
                return annotated_path
            else:
                logger.error(f"Annotated video file exists but is empty (0 bytes). Processed {frame_count} frames but file is empty.")
                annotated_path.unlink()
                return None
        else:
            logger.error(f"Annotated video file was not created at {annotated_path}. Processed {frame_count} frames.")
            return None

    def _draw_pose_overlay(
        self,
        frame: np.ndarray,
        pose_data: Dict,
        confidence: float,
        style: str = "standard",
    ) -> np.ndarray:
        """
        Draw pose keypoints overlay on frame.

        Args:
            frame: Input frame
            pose_data: Pose keypoints data
            confidence: Detection confidence
            style: Annotation style

        Returns:
            Annotated frame
        """
        annotated_frame = frame.copy()

        # TODO: Implement pose connections drawing in future version
        # pose_connections = [
        #     # Face, torso, arms, legs connections would go here
        # ]

        # Color scheme based on style
        if style == "debug":
            keypoint_color = (0, 255, 255)  # Yellow
            # connection_color = (255, 0, 255)  # Magenta  # TODO: Use when connections are implemented
            confidence_color = (0, 255, 0)  # Green
        elif style == "presentation":
            keypoint_color = (0, 255, 0)  # Green
            # connection_color = (255, 255, 255)  # White  # TODO: Use when connections are implemented
            confidence_color = (255, 255, 0)  # Cyan
        else:  # standard
            keypoint_color = (0, 255, 0)  # Green
            # connection_color = (0, 255, 0)  # Green  # TODO: Use when connections are implemented
            confidence_color = (255, 255, 255)  # White

        # Draw keypoints
        for _keypoint_name, keypoint_data in pose_data.items():
            if isinstance(keypoint_data, list) and len(keypoint_data) >= 2:
                x, y = int(keypoint_data[0]), int(keypoint_data[1])
                if 0 <= x < frame.shape[1] and 0 <= y < frame.shape[0]:
                    cv2.circle(annotated_frame, (x, y), 3, keypoint_color, -1)

        # Draw connections (simplified - would need full keypoint mapping)
        # For now, just draw confidence text
        cv2.putText(
            annotated_frame,
            f"Pose Confidence: {confidence:.2f}",
            (10, 30),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.7,
            confidence_color,
            2,
        )

        return annotated_frame

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
