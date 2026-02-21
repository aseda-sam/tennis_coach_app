"""Serve biomechanics service — orchestrates phase segmentation + metrics computation.

load pose data → segment phases → compute metrics → store report.
No scoring or coaching.
"""

import json
import logging
from typing import List

from sqlalchemy.orm import Session

from app.models.player import Player
from app.models.serve_biomechanics_report import ServeBiomechanicsReport
from app.models.serve_window import ServeWindow
from app.models.video import Video
from app.services.biomechanics.metrics import (
    compute_biomechanics_metrics,
)
from app.services.biomechanics.phase_segmentation import (
    segment_serve_phases,
)
from app.services.biomechanics.toss_metrics import (
    _compute_toss_metrics,
    _get_best_ball_detection,
)
from app.services.pose_data_service import (
    _select_best_pose_detection,
    get_pose_frames_in_window,
)

logger = logging.getLogger(__name__)

ANALYSIS_VERSION = "phase-metrics-v3"


class ServeBiomechanicsService:
    """Orchestrates phase segmentation, metrics computation, and storage."""

    def get_or_compute_analysis(
        self, db: Session, serve_window_id: int, user_id: str
    ) -> ServeBiomechanicsReport:
        """Return cached report or compute fresh.

        Lazy computation: computes on first GET, not during analysis pipeline.
        """
        existing = (
            db.query(ServeBiomechanicsReport)
            .filter(
                ServeBiomechanicsReport.serve_window_id == serve_window_id,
                ServeBiomechanicsReport.user_id == user_id,
            )
            .order_by(ServeBiomechanicsReport.created_at.desc())
            .first()
        )

        if existing is not None:
            return existing

        return self.compute_analysis(db, serve_window_id, user_id)

    def compute_analysis(
        self, db: Session, serve_window_id: int, user_id: str
    ) -> ServeBiomechanicsReport:
        """Full pipeline: load pose → segment phases → compute metrics → store.

        Raises ValueError if serve window, video, or pose data is missing.
        """
        serve_window = (
            db.query(ServeWindow)
            .filter(
                ServeWindow.id == serve_window_id,
                ServeWindow.user_id == user_id,
            )
            .first()
        )
        if not serve_window:
            raise ValueError(f"Serve window {serve_window_id} not found")

        video = db.query(Video).filter(Video.id == serve_window.video_id).first()
        if not video:
            raise ValueError(f"Video {serve_window.video_id} not found")

        player = db.query(Player).filter(Player.id == serve_window.player_id).first()
        dominant_hand = player.dominant_hand if player else "right"

        pose_detection = _select_best_pose_detection(db, video.id)
        if not pose_detection:
            raise ValueError(
                f"No pose detection for video {video.id}. Run analysis first."
            )

        # Lazy fallback: auto-detect contact from ball + wrist if not set (e.g. older videos)
        if serve_window.contact_timestamp is None:
            ball_detection = _get_best_ball_detection(db, video.id)
            if ball_detection:
                from app.services.ball_detection.contact_detector import (
                    detect_contact_timestamp,
                )

                contact_ts = detect_contact_timestamp(
                    ball_detection=ball_detection,
                    pose_detection=pose_detection,
                    serve_window=serve_window,
                    video=video,
                    dominant_hand=dominant_hand,
                )
                if contact_ts is not None:
                    serve_window.contact_timestamp = contact_ts
                    db.commit()
                    logger.info(
                        "Auto-detected contact for serve window %s at %.2fs (lazy)",
                        serve_window_id,
                        contact_ts,
                    )

        fps = video.fps or 30.0
        pose_frames = get_pose_frames_in_window(
            pose_detection,
            video,
            serve_window.start_timestamp,
            serve_window.end_timestamp,
        )

        width = video.width or 1280
        height = video.height or 720

        phase_result = segment_serve_phases(
            pose_frames=pose_frames,
            fps=fps,
            serve_start=serve_window.start_timestamp,
            serve_end=serve_window.end_timestamp,
            contact_timestamp=serve_window.contact_timestamp,
            dominant_hand=dominant_hand,
            video_width=width,
            video_height=height,
        )

        metrics = compute_biomechanics_metrics(
            pose_frames=pose_frames,
            fps=fps,
            serve_start=serve_window.start_timestamp,
            serve_end=serve_window.end_timestamp,
            contact_timestamp=serve_window.contact_timestamp,
            dominant_hand=dominant_hand,
            video_width=width,
            video_height=height,
            phases=phase_result.phases,
        )

        ball_detection = _get_best_ball_detection(db, video.id)
        if ball_detection:
            toss_metrics = _compute_toss_metrics(
                serve_window, ball_detection, video, pose_detection
            )
            if toss_metrics and toss_metrics.get("toss_peak_height") is not None:
                metrics.toss_peak_height = toss_metrics["toss_peak_height"]
            if (
                toss_metrics
                and toss_metrics.get("toss_laterality") is not None
                and video.camera_angle != "profile"
            ):
                metrics.toss_laterality = toss_metrics["toss_laterality"]

        report = ServeBiomechanicsReport(
            serve_window_id=serve_window_id,
            user_id=user_id,
            player_id=serve_window.player_id,
            phase_segmentation_json=json.dumps(phase_result.model_dump(), default=str),
            metrics_json=json.dumps(metrics.model_dump(), default=str),
            analysis_version=ANALYSIS_VERSION,
        )

        db.add(report)
        db.commit()
        db.refresh(report)

        logger.info(
            "Computed biomechanics report %s for serve window %s",
            report.id,
            serve_window_id,
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


def compute_biomechanics_batch(
    db: Session,
    video_id: int,
    user_id: str,
) -> list[ServeBiomechanicsReport]:
    """Compute biomechanics for all accepted serve windows in a video.

    Called by the RQ pipeline after auto-accept. Skips windows that
    already have a report. Errors on individual windows are logged
    and skipped so one bad window doesn't block the rest.

    Returns:
        List of successfully computed reports.
    """
    windows = (
        db.query(ServeWindow)
        .filter(
            ServeWindow.video_id == video_id,
            ServeWindow.user_id == user_id,
            ServeWindow.status.in_(["accepted", "edited"]),
        )
        .order_by(ServeWindow.start_timestamp)
        .all()
    )

    if not windows:
        logger.info(
            "No accepted serve windows for video %s, skipping biomechanics", video_id
        )
        return []

    reports: list[ServeBiomechanicsReport] = []
    for window in windows:
        try:
            report = serve_biomechanics_service.compute_analysis(db, window.id, user_id)
            reports.append(report)
        except Exception:  # noqa: BLE001 - skip individual failures
            logger.warning(
                "Failed to compute biomechanics for serve window %s, skipping",
                window.id,
                exc_info=True,
            )

    logger.info(
        "Computed biomechanics for %d/%d serve windows in video %d",
        len(reports),
        len(windows),
        video_id,
    )
    return reports
