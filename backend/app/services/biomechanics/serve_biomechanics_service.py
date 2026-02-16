"""Serve biomechanics service — orchestrates phase segmentation + metrics computation.

load pose data → segment phases → compute metrics → store report.
No scoring or coaching.
"""

import json
import logging
from typing import List

from sqlalchemy.orm import Session

from app.models.player import Player
from app.models.serve_attempt import ServeAttempt
from app.models.serve_biomechanics_report import ServeBiomechanicsReport
from app.models.video import Video
from app.services.biomechanics.metrics import (
    compute_biomechanics_metrics,
)
from app.services.biomechanics.phase_segmentation import (
    segment_serve_phases,
)
from app.services.pose_data_service import (
    _compute_toss_metrics,
    _get_best_ball_detection,
    _select_best_pose_detection,
    get_pose_frames_in_window,
)

logger = logging.getLogger(__name__)

ANALYSIS_VERSION = "phase-metrics-v1"


class ServeBiomechanicsService:
    """Orchestrates phase segmentation, metrics computation, and storage."""

    def get_or_compute_analysis(
        self, db: Session, serve_attempt_id: int, user_id: str
    ) -> ServeBiomechanicsReport:
        """Return cached report or compute fresh.

        Lazy computation: computes on first GET, not during analysis pipeline.
        """
        existing = (
            db.query(ServeBiomechanicsReport)
            .filter(
                ServeBiomechanicsReport.serve_attempt_id == serve_attempt_id,
                ServeBiomechanicsReport.user_id == user_id,
            )
            .order_by(ServeBiomechanicsReport.created_at.desc())
            .first()
        )

        if existing is not None:
            return existing

        return self.compute_analysis(db, serve_attempt_id, user_id)

    def compute_analysis(
        self, db: Session, serve_attempt_id: int, user_id: str
    ) -> ServeBiomechanicsReport:
        """Full pipeline: load pose → segment phases → compute metrics → store.

        Raises ValueError if serve attempt, video, or pose data is missing.
        """
        serve_attempt = (
            db.query(ServeAttempt)
            .filter(
                ServeAttempt.id == serve_attempt_id,
                ServeAttempt.user_id == user_id,
            )
            .first()
        )
        if not serve_attempt:
            raise ValueError(f"Serve attempt {serve_attempt_id} not found")

        video = db.query(Video).filter(Video.id == serve_attempt.video_id).first()
        if not video:
            raise ValueError(f"Video {serve_attempt.video_id} not found")

        player = db.query(Player).filter(Player.id == serve_attempt.player_id).first()
        dominant_hand = player.dominant_hand if player else "right"

        pose_detection = _select_best_pose_detection(db, video.id)
        if not pose_detection:
            raise ValueError(
                f"No pose detection for video {video.id}. Run analysis first."
            )

        fps = video.fps or 30.0
        pose_frames = get_pose_frames_in_window(
            pose_detection,
            video,
            serve_attempt.start_timestamp,
            serve_attempt.end_timestamp,
        )

        width = video.width or 1280
        height = video.height or 720

        phase_result = segment_serve_phases(
            pose_frames=pose_frames,
            fps=fps,
            serve_start=serve_attempt.start_timestamp,
            serve_end=serve_attempt.end_timestamp,
            contact_timestamp=serve_attempt.contact_timestamp,
            dominant_hand=dominant_hand,
            video_width=width,
            video_height=height,
        )

        metrics = compute_biomechanics_metrics(
            pose_frames=pose_frames,
            fps=fps,
            serve_start=serve_attempt.start_timestamp,
            serve_end=serve_attempt.end_timestamp,
            contact_timestamp=serve_attempt.contact_timestamp,
            dominant_hand=dominant_hand,
            video_width=width,
            video_height=height,
            phases=phase_result.phases,
        )

        ball_detection = _get_best_ball_detection(db, video.id)
        if ball_detection:
            toss_metrics = _compute_toss_metrics(
                serve_attempt, ball_detection, video, pose_detection
            )
            if toss_metrics and toss_metrics.get("toss_peak_height") is not None:
                metrics.toss_peak_height = toss_metrics["toss_peak_height"]

        report = ServeBiomechanicsReport(
            serve_attempt_id=serve_attempt_id,
            user_id=user_id,
            player_id=serve_attempt.player_id,
            phase_segmentation_json=json.dumps(phase_result.model_dump(), default=str),
            metrics_json=json.dumps(metrics.model_dump(), default=str),
            analysis_version=ANALYSIS_VERSION,
        )

        db.add(report)
        db.commit()
        db.refresh(report)

        logger.info(
            "Computed biomechanics report %s for serve attempt %s",
            report.id,
            serve_attempt_id,
        )

        return report

    def get_player_history(
        self,
        db: Session,
        player_id: int,
        user_id: str,
        limit: int = 20,
    ) -> List[ServeBiomechanicsReport]:
        """Get historical biomechanics reports for a player."""
        return (
            db.query(ServeBiomechanicsReport)
            .filter(
                ServeBiomechanicsReport.player_id == player_id,
                ServeBiomechanicsReport.user_id == user_id,
            )
            .order_by(ServeBiomechanicsReport.created_at.desc())
            .limit(limit)
            .all()
        )


serve_biomechanics_service = ServeBiomechanicsService()
