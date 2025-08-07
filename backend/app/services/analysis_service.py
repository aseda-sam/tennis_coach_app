"""
Analysis service for handling video analysis operations.
"""

import json
import logging
import time
from pathlib import Path
from typing import Any, Dict, Optional

from sqlalchemy.orm import Session

from app.core.config import settings
from app.models.analysis import Analysis
from app.services.cv_service import cv_service

logger = logging.getLogger(__name__)


def create_analysis_record(
    db: Session,
    video_filename: str,
    analysis_type: str,
    analysis_results: Dict[str, Any],
    processing_time: float,
    model_used: Optional[str] = None,
    confidence_threshold: float = 0.5,
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
        ball_detections=json.dumps(analysis_results.get("ball_detections", [])),
        processing_time=processing_time,
        model_used=model_used,
        confidence_threshold=confidence_threshold,
    )

    db.add(analysis)
    db.commit()
    db.refresh(analysis)

    logger.info(f"Created analysis record for {video_filename}")
    return analysis


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


def get_all_analyses(db: Session) -> list[Analysis]:
    """
    Get all analysis records.

    Args:
        db: Database session

    Returns:
        List of all analysis records
    """
    return db.query(Analysis).all()


def analyze_video(db: Session, video_filename: str) -> Dict[str, Any]:
    """
    Perform video analysis and store results.

    Args:
        db: Database session
        video_filename: Name of the video file to analyze

    Returns:
        Analysis results dictionary
    """
    logger.info(f"Starting analysis for video: {video_filename}")

    # Check if analysis already exists
    existing_analysis = get_analysis_by_video(db, video_filename)
    if existing_analysis:
        logger.info(f"Analysis already exists for {video_filename}")
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

    # Find video file
    video_path = Path(settings.UPLOAD_DIR) / video_filename
    if not video_path.exists():
        return {"error": f"Video file not found: {video_filename}"}

    try:
        # Start timing
        start_time = time.time()

        # Perform analysis
        analysis_results = cv_service.analyze_video(video_path)

        # Calculate processing time
        processing_time = time.time() - start_time

        if "error" in analysis_results:
            return analysis_results

        # Store results in database
        analysis_record = create_analysis_record(
            db=db,
            video_filename=video_filename,
            analysis_type="ball_detection",
            analysis_results=analysis_results,
            processing_time=processing_time,
            model_used="yolov8n" if cv_service.ball_detector else None,
            confidence_threshold=0.5,
        )

        return {
            "message": "Analysis completed successfully",
            "analysis_id": analysis_record.id,
            "processing_time": processing_time,
            "analysis_summary": analysis_results["analysis_summary"],
            "frames_processed": analysis_results["frames_processed"],
        }

    except Exception as e:
        logger.error(f"Error analyzing video {video_filename}: {e}")
        return {"error": f"Analysis failed: {e!s}"}


def delete_analysis(db: Session, video_filename: str) -> bool:
    """
    Delete analysis results for a video.

    Args:
        db: Database session
        video_filename: Name of the video file

    Returns:
        True if deleted, False otherwise
    """
    analysis = get_analysis_by_video(db, video_filename)
    if analysis:
        db.delete(analysis)
        db.commit()
        logger.info(f"Deleted analysis for {video_filename}")
        return True
    return False
