"""
Analysis service for handling video analysis operations.
"""

import json
import logging
import time
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, Optional

from sqlalchemy.orm import Session

from app.core.config import settings
from app.models.analysis import Analysis
from app.services.cv_service import cv_service

logger = logging.getLogger(__name__)


def create_analysis_record(
    db: Session,
    video_id: int,
    video_filename: str,
    analysis_type: str,
    analysis_results: Dict[str, Any],
    processing_time: float,
    model_used: Optional[str] = None,
    confidence_threshold: float = 0.5,
    status: str = "completed",
) -> Analysis:
    """
    Create a new analysis record in the database.

    Args:
        db: Database session
        video_filename: Name of the analyzed video file
        analysis_type: Type of analysis performed
        analysis_results: Results from the analysis
        processing_time: Time taken for processing
        model_used: Model used for analysis
        confidence_threshold: Confidence threshold used

    Returns:
        Created Analysis record
    """
    analysis = Analysis(
        video_id=video_id,
        video_filename=video_filename,
        analysis_type=analysis_type,
        total_frames=analysis_results.get("frames_processed", 0),
        frames_with_balls=analysis_results.get("analysis_summary", {}).get(
            "frames_with_balls", 0
        ),
        total_ball_detections=analysis_results.get("analysis_summary", {}).get(
            "total_ball_detections", 0
        ),
        average_detections_per_frame=analysis_results.get("analysis_summary", {}).get(
            "average_detections_per_frame", 0.0
        ),
        detection_rate=analysis_results.get("analysis_summary", {}).get(
            "detection_rate", 0.0
        ),
        frames_with_pose=analysis_results.get("analysis_summary", {}).get(
            "frames_with_pose", 0
        ),
        pose_detection_rate=analysis_results.get("analysis_summary", {}).get(
            "pose_detection_rate", 0.0
        ),
        ball_detections=json.dumps(analysis_results.get("ball_detections", [])),
        pose_detections=json.dumps(analysis_results.get("pose_detections", [])),
        annotated_video_path=analysis_results.get("annotated_video_path"),
        processing_time=processing_time,
        model_used=model_used,
        confidence_threshold=confidence_threshold,
        status=status,
    )

    db.add(analysis)
    db.commit()
    db.refresh(analysis)

    logger.info(f"Created analysis record for {video_filename}")
    return analysis


def get_analysis_by_id(db: Session, analysis_id: int) -> Optional[Analysis]:
    """
    Get analysis by ID.

    Args:
        db: Database session
        analysis_id: Analysis ID

    Returns:
        Analysis record if found, None otherwise
    """
    return db.query(Analysis).filter(Analysis.id == analysis_id).first()


def get_analysis_by_video(db: Session, video_filename: str) -> Optional[Analysis]:
    """
    Get analysis results for a specific video.

    Args:
        db: Database session
        video_filename: Name of the video file

    Returns:
        Analysis record if found, None otherwise
    """
    return db.query(Analysis).filter(Analysis.video_filename == video_filename).first()


def get_analysis_by_video_id(db: Session, video_id: int) -> Optional[Analysis]:
    """
    Get analysis results for a specific video by ID.

    Args:
        db: Database session
        video_id: ID of the video

    Returns:
        Analysis record if found, None otherwise
    """
    return db.query(Analysis).filter(Analysis.video_id == video_id).first()


def get_all_analyses(db: Session) -> list[Analysis]:
    """
    Get all analysis records.

    Args:
        db: Database session

    Returns:
        List of all analysis records
    """
    return db.query(Analysis).order_by(Analysis.created_at.desc()).all()


def analyze_video(
    db: Session,
    video_id: int,
    analysis_type: str = "ball_tracking",
    confidence_threshold: float = 0.7,
    include_pose_detection: bool = False,
) -> Dict[str, Any]:
    """
    Perform video analysis and store results.

    Args:
        db: Database session
        video_id: Video ID
        analysis_type: Type of analysis to perform
        confidence_threshold: Detection confidence threshold
        include_pose_detection: Whether to include pose detection

    Returns:
        Analysis results dictionary
    """
    from app.services.video_service import get_video_by_id

    # Get video by ID
    video = get_video_by_id(db, video_id)
    if not video:
        return {"error": f"Video with ID {video_id} not found"}

    video_filename = video.filename
    logger.info(f"Starting analysis for video: {video_filename}")

    # Check if analysis already exists and is completed
    existing_analysis = get_analysis_by_video_id(db, video_id)
    if existing_analysis and existing_analysis.status == "completed":
        logger.info(f"Analysis already exists and completed for {video_filename}")
        return {
            "message": "Analysis already exists",
            "analysis_id": existing_analysis.id,
            "analysis_summary": {
                "total_frames": existing_analysis.total_frames,
                "frames_with_balls": existing_analysis.frames_with_balls,
                "total_ball_detections": existing_analysis.total_ball_detections,
                "average_detections_per_frame": existing_analysis.average_detections_per_frame,
                "detection_rate": existing_analysis.detection_rate,
            },
        }

    # If analysis exists but is still processing, continue with analysis
    if existing_analysis and existing_analysis.status == "processing":
        logger.info(f"Analysis in progress for {video_filename}, continuing...")

    # Find video file
    video_path = Path(settings.UPLOAD_DIR) / video_filename
    if not video_path.exists():
        return {"error": f"Video file not found: {video_filename}"}

    # Quick validation: try to extract a few frames to check if video is valid
    try:
        test_frames = cv_service.extract_frames(video_path, max_frames=5)
        if not test_frames:
            return {
                "error": f"Invalid video file: {video_filename} - cannot extract frames"
            }
    except (OSError, ValueError, RuntimeError) as e:
        return {"error": f"Video validation failed: {video_filename} - {e!s}"}

    try:
        # Start timing
        start_time = time.time()

        # Perform analysis
        analysis_results = cv_service.analyze_video(
            video_path,
            include_pose=include_pose_detection,
        )

        # Calculate processing time
        processing_time = time.time() - start_time

        if "error" in analysis_results:
            return analysis_results

        # Update existing analysis record or create new one
        if existing_analysis and existing_analysis.status == "processing":
            # Update existing processing record
            analysis_record = existing_analysis
            analysis_record.total_frames = analysis_results.get("frames_processed", 0)
            analysis_record.frames_with_balls = analysis_results.get(
                "analysis_summary", {}
            ).get("frames_with_balls", 0)
            analysis_record.total_ball_detections = analysis_results.get(
                "analysis_summary", {}
            ).get("total_ball_detections", 0)
            analysis_record.average_detections_per_frame = analysis_results.get(
                "analysis_summary", {}
            ).get("average_detections_per_frame", 0.0)
            analysis_record.detection_rate = analysis_results.get(
                "analysis_summary", {}
            ).get("detection_rate", 0.0)
            analysis_record.frames_with_pose = analysis_results.get(
                "analysis_summary", {}
            ).get("frames_with_pose", 0)
            analysis_record.pose_detection_rate = analysis_results.get(
                "analysis_summary", {}
            ).get("pose_detection_rate", 0.0)
            analysis_record.ball_detections = json.dumps(
                analysis_results.get("ball_detections", [])
            )
            analysis_record.pose_detections = json.dumps(
                analysis_results.get("pose_detections", [])
            )
            analysis_record.annotated_video_path = analysis_results.get(
                "annotated_video_path"
            )
            analysis_record.processing_time = processing_time
            analysis_record.model_used = (
                "yolov8n+mediapipe"
                if cv_service.ball_detector and cv_service.pose_detector
                else "yolov8n"
                if cv_service.ball_detector
                else None
            )
            analysis_record.confidence_threshold = confidence_threshold
            analysis_record.status = "completed"
            analysis_record.completed_at = datetime.now()
            db.commit()
            db.refresh(analysis_record)
        else:
            # Create new analysis record
            analysis_record = create_analysis_record(
                db=db,
                video_id=video_id,
                video_filename=video_filename,
                analysis_type=analysis_type,
                analysis_results=analysis_results,
                processing_time=processing_time,
                model_used="yolov8n+mediapipe"
                if cv_service.ball_detector and cv_service.pose_detector
                else "yolov8n"
                if cv_service.ball_detector
                else None,
                confidence_threshold=confidence_threshold,
                status="completed",
            )

        return {
            "message": "Analysis completed successfully",
            "analysis_id": analysis_record.id,
            "processing_time": processing_time,
            "analysis_summary": analysis_results["analysis_summary"],
            "frames_processed": analysis_results["frames_processed"],
            "estimated_duration": processing_time
            * 1.2,  # Rough estimate for future videos
        }

    except (OSError, ValueError, RuntimeError) as e:
        logger.error(f"Error analyzing video {video_filename}: {e}")
        return {"error": f"Analysis failed: {e!s}"}


def update_analysis_status(
    db: Session, video_id: int, status: str, error_message: Optional[str] = None
) -> bool:
    """
    Update analysis status for a video.

    Args:
        db: Database session
        video_id: Video ID
        status: New status (processing, completed, failed)
        error_message: Error message if status is failed

    Returns:
        True if updated, False otherwise
    """
    analysis = get_analysis_by_video_id(db, video_id)
    if analysis:
        analysis.status = status
        if error_message:
            analysis.error_message = error_message
        if status in ["completed", "failed"]:
            analysis.completed_at = datetime.now()
        db.commit()
        logger.info(f"Updated analysis status for video {video_id} to {status}")
        return True
    return False


def delete_analysis(db: Session, video_filename: str) -> bool:
    """
    Delete analysis results for a video, including any annotated video files.

    Args:
        db: Database session
        video_filename: Name of the video file

    Returns:
        True if deleted, False otherwise
    """
    from pathlib import Path

    from app.core.config import settings

    analysis = get_analysis_by_video(db, video_filename)
    if analysis:
        # Delete annotated video file if it exists
        if analysis.annotated_video_path:
            annotated_path = Path(analysis.annotated_video_path)
            if annotated_path.exists():
                try:
                    annotated_path.unlink()
                    logger.info(f"Deleted annotated video: {annotated_path}")
                except OSError as e:
                    logger.warning(
                        f"Failed to delete annotated video {annotated_path}: {e}"
                    )

        # Also check for standard annotated file naming pattern
        processed_dir = Path(settings.UPLOAD_DIR).parent / "processed"
        base_name = Path(video_filename).stem
        potential_annotated = processed_dir / f"{base_name}_annotated.mp4"
        if potential_annotated.exists():
            try:
                potential_annotated.unlink()
                logger.info(f"Deleted annotated video: {potential_annotated}")
            except OSError as e:
                logger.warning(
                    f"Failed to delete annotated video {potential_annotated}: {e}"
                )

        # Delete analysis record from database
        db.delete(analysis)
        db.commit()
        logger.info(f"Deleted analysis for {video_filename}")
        return True
    return False
