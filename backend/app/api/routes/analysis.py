"""
API routes for video analysis functionality.
"""

from typing import List

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.services.analysis_service import (
    analyze_video,
    delete_analysis,
    get_all_analyses,
    get_analysis_by_video,
)

router = APIRouter()


class AnalysisResponse(BaseModel):
    """Response model for analysis results."""

    id: int
    video_filename: str
    analysis_type: str
    total_frames: int
    frames_with_balls: int
    total_ball_detections: int
    average_detections_per_frame: float
    detection_rate: float
    processing_time: float
    model_used: str | None
    confidence_threshold: float


class AnalysisSummary(BaseModel):
    """Summary model for analysis results."""

    message: str
    analysis_id: int | None = None
    processing_time: float | None = None
    analysis_summary: dict | None = None
    frames_processed: int | None = None
    error: str | None = None


@router.post("/{video_filename}", response_model=AnalysisSummary)
async def start_analysis(
    video_filename: str, db: Session = Depends(get_db)
) -> AnalysisSummary:
    """
    Start analysis for a specific video.

    Args:
        video_filename: Name of the video file to analyze
        db: Database session

    Returns:
        Analysis results summary
    """
    try:
        result = analyze_video(db, video_filename)
        return AnalysisSummary(**result)
    except (OSError, ValueError, RuntimeError) as e:
        raise HTTPException(status_code=500, detail=f"Analysis failed: {e!s}") from e


@router.get("/{video_filename}", response_model=AnalysisResponse)
async def get_analysis(
    video_filename: str, db: Session = Depends(get_db)
) -> AnalysisResponse:
    """
    Get analysis results for a specific video.

    Args:
        video_filename: Name of the video file
        db: Database session

    Returns:
        Analysis results
    """
    analysis = get_analysis_by_video(db, video_filename)
    if not analysis:
        raise HTTPException(
            status_code=404, detail=f"No analysis found for {video_filename}"
        )

    return AnalysisResponse(
        id=analysis.id,
        video_filename=analysis.video_filename,
        analysis_type=analysis.analysis_type,
        total_frames=analysis.total_frames,
        frames_with_balls=analysis.frames_with_balls,
        total_ball_detections=analysis.total_ball_detections,
        average_detections_per_frame=analysis.average_detections_per_frame,
        detection_rate=analysis.detection_rate,
        processing_time=analysis.processing_time,
        model_used=analysis.model_used,
        confidence_threshold=analysis.confidence_threshold,
    )


@router.get("/", response_model=List[AnalysisResponse])
async def list_analyses(db: Session = Depends(get_db)) -> List[AnalysisResponse]:
    """
    Get all analysis results.

    Args:
        db: Database session

    Returns:
        List of all analysis results
    """
    analyses = get_all_analyses(db)
    return [
        AnalysisResponse(
            id=analysis.id,
            video_filename=analysis.video_filename,
            analysis_type=analysis.analysis_type,
            total_frames=analysis.total_frames,
            frames_with_balls=analysis.frames_with_balls,
            total_ball_detections=analysis.total_ball_detections,
            average_detections_per_frame=analysis.average_detections_per_frame,
            detection_rate=analysis.detection_rate,
            processing_time=analysis.processing_time,
            model_used=analysis.model_used,
            confidence_threshold=analysis.confidence_threshold,
        )
        for analysis in analyses
    ]


@router.delete("/{video_filename}")
async def delete_analysis_results(
    video_filename: str, db: Session = Depends(get_db)
) -> dict:
    """
    Delete analysis results for a video.

    Args:
        video_filename: Name of the video file
        db: Database session

    Returns:
        Success message
    """
    if delete_analysis(db, video_filename):
        return {"message": f"Analysis for {video_filename} deleted successfully"}
    else:
        raise HTTPException(
            status_code=404, detail=f"No analysis found for {video_filename}"
        )
