"""Progress overview service — aggregation logic for serve metrics."""

import logging
import math
from datetime import datetime, timedelta, timezone
from typing import Optional

from sqlalchemy import func
from sqlalchemy.orm import Session

from app.api.schemas.progress import (
    CourtSideDistribution,
    ElbowAngleMetric,
    KneeBendMetric,
    ProgressMetricDataPoint,
    ProgressMetrics,
    ProgressResponse,
)
from app.models.serve_attempt import ServeAttempt
from app.models.video import Video

logger = logging.getLogger(__name__)

# Healthy elbow angle range (degrees) — "improving" means moving toward this window
HEALTHY_ELBOW_MIN = 140.0
HEALTHY_ELBOW_MAX = 170.0

# Trend threshold: > 3% change = improving/declining
TREND_THRESHOLD = 0.03

# Consistency rating thresholds (standard deviation in degrees)
CONSISTENCY_EXCELLENT = 5.0
CONSISTENCY_GOOD = 10.0
CONSISTENCY_FAIR = 15.0


def _parse_time_window(time_period: str) -> Optional[datetime]:
    """Return the start datetime for the given time period, or None for 'all'."""
    now = datetime.now(timezone.utc)
    if time_period == "7d":
        return now - timedelta(days=7)
    if time_period == "30d":
        return now - timedelta(days=30)
    return None  # "all"


def _get_previous_window(
    time_period: str, window_start: Optional[datetime]
) -> tuple[Optional[datetime], Optional[datetime]]:
    """Return (start, end) for the previous equivalent time window."""
    if time_period == "all" or window_start is None:
        return None, None
    now = datetime.now(timezone.utc)
    duration = now - window_start
    return window_start - duration, window_start


def _consistency_rating(std_dev: float) -> str:
    """Map standard deviation to a consistency rating."""
    if std_dev <= CONSISTENCY_EXCELLENT:
        return "excellent"
    if std_dev <= CONSISTENCY_GOOD:
        return "good"
    if std_dev <= CONSISTENCY_FAIR:
        return "fair"
    return "needs_work"


def _elbow_trend(current_avg: float, previous_avg: Optional[float]) -> str:
    """Determine elbow angle trend.

    "Improving" means moving closer to the healthy range (140-170 degrees).
    """
    if previous_avg is None:
        return "stable"

    healthy_mid = (HEALTHY_ELBOW_MIN + HEALTHY_ELBOW_MAX) / 2.0

    current_distance = abs(current_avg - healthy_mid)
    previous_distance = abs(previous_avg - healthy_mid)

    if previous_distance == 0:
        return "stable"

    change_ratio = (previous_distance - current_distance) / previous_distance

    if change_ratio > TREND_THRESHOLD:
        return "improving"
    if change_ratio < -TREND_THRESHOLD:
        return "declining"
    return "stable"


def _knee_bend_trend(current_rate: float, previous_rate: Optional[float]) -> str:
    """Determine knee bend trend. Higher rate = improving."""
    if previous_rate is None:
        return "stable"

    if previous_rate == 0:
        return "improving" if current_rate > 0 else "stable"

    change_ratio = (current_rate - previous_rate) / previous_rate

    if change_ratio > TREND_THRESHOLD:
        return "improving"
    if change_ratio < -TREND_THRESHOLD:
        return "declining"
    return "stable"


def _query_serves(
    db: Session,
    user_id: str,
    player_id: Optional[int],
    window_start: Optional[datetime],
    window_end: Optional[datetime] = None,
) -> "Query":  # noqa: F821
    """Build base query for serve attempts joined with video, filtered by user and time."""
    query = (
        db.query(ServeAttempt)
        .join(Video, ServeAttempt.video_id == Video.id)
        .filter(ServeAttempt.user_id == user_id)
    )

    if player_id is not None:
        query = query.filter(ServeAttempt.player_id == player_id)

    if window_start is not None:
        query = query.filter(Video.recorded_at >= window_start)

    if window_end is not None:
        query = query.filter(Video.recorded_at < window_end)

    # Only include videos that have recorded_at set
    query = query.filter(Video.recorded_at.isnot(None))

    return query


def _compute_elbow_angle_metric(
    db: Session,
    user_id: str,
    player_id: Optional[int],
    window_start: Optional[datetime],
    time_period: str,
) -> Optional[ElbowAngleMetric]:
    """Compute elbow angle metrics grouped by video."""
    # Get per-video averages for current window
    rows = (
        _query_serves(db, user_id, player_id, window_start)
        .filter(ServeAttempt.elbow_angle_at_contact.isnot(None))
        .with_entities(
            Video.id,
            func.date(Video.recorded_at).label("date"),
            func.avg(ServeAttempt.elbow_angle_at_contact).label("avg"),
            func.count(ServeAttempt.id).label("count"),
        )
        .group_by(Video.id, func.date(Video.recorded_at))
        .order_by(func.date(Video.recorded_at))
        .all()
    )

    if not rows:
        return None

    data_points = [
        ProgressMetricDataPoint(
            date=str(row.date),
            avg=round(row.avg, 1),
            count=row.count,
        )
        for row in rows
    ]

    # Overall current average and std dev
    all_angles = (
        _query_serves(db, user_id, player_id, window_start)
        .filter(ServeAttempt.elbow_angle_at_contact.isnot(None))
        .with_entities(ServeAttempt.elbow_angle_at_contact)
        .all()
    )
    angles = [a[0] for a in all_angles]
    current_avg = sum(angles) / len(angles)
    variance = sum((a - current_avg) ** 2 for a in angles) / len(angles)
    std_dev = math.sqrt(variance)

    # Previous window average for trend
    prev_start, prev_end = _get_previous_window(time_period, window_start)
    previous_avg = None
    if prev_start is not None:
        prev_rows = (
            _query_serves(db, user_id, player_id, prev_start, prev_end)
            .filter(ServeAttempt.elbow_angle_at_contact.isnot(None))
            .with_entities(func.avg(ServeAttempt.elbow_angle_at_contact))
            .first()
        )
        if prev_rows and prev_rows[0] is not None:
            previous_avg = round(prev_rows[0], 1)

    return ElbowAngleMetric(
        current_avg=round(current_avg, 1),
        previous_avg=previous_avg,
        trend=_elbow_trend(current_avg, previous_avg),
        consistency=round(std_dev, 1),
        consistency_rating=_consistency_rating(std_dev),
        data_points=data_points,
    )


def _compute_knee_bend_metric(
    db: Session,
    user_id: str,
    player_id: Optional[int],
    window_start: Optional[datetime],
    time_period: str,
) -> Optional[KneeBendMetric]:
    """Compute knee bend rate metrics grouped by video."""
    # Query per-video serves with knee_bend_detected
    rows = (
        _query_serves(db, user_id, player_id, window_start)
        .filter(ServeAttempt.knee_bend_detected.isnot(None))
        .with_entities(
            Video.id,
            func.date(Video.recorded_at).label("date"),
            ServeAttempt.knee_bend_detected,
        )
        .order_by(func.date(Video.recorded_at))
        .all()
    )

    if not rows:
        return None

    # Group by video to compute per-video rates
    from collections import defaultdict

    video_groups: dict[tuple, list[bool]] = defaultdict(list)
    for row in rows:
        video_groups[(row[0], str(row.date))].append(bool(row.knee_bend_detected))

    data_points = []
    for (_, date), bends in sorted(video_groups.items(), key=lambda x: x[0][1]):
        total = len(bends)
        detected = sum(bends)
        rate = detected / total if total > 0 else 0.0
        data_points.append(
            ProgressMetricDataPoint(
                date=date,
                avg=round(rate, 2),
                count=total,
            )
        )

    # Overall current rate
    all_serves = (
        _query_serves(db, user_id, player_id, window_start)
        .filter(ServeAttempt.knee_bend_detected.isnot(None))
        .with_entities(ServeAttempt.knee_bend_detected)
        .all()
    )
    total = len(all_serves)
    detected = sum(1 for s in all_serves if s[0])
    current_rate = detected / total if total > 0 else 0.0

    # Previous window rate for trend
    prev_start, prev_end = _get_previous_window(time_period, window_start)
    previous_rate = None
    if prev_start is not None:
        prev_serves = (
            _query_serves(db, user_id, player_id, prev_start, prev_end)
            .filter(ServeAttempt.knee_bend_detected.isnot(None))
            .with_entities(ServeAttempt.knee_bend_detected)
            .all()
        )
        if prev_serves:
            prev_total = len(prev_serves)
            prev_detected = sum(1 for s in prev_serves if s[0])
            previous_rate = (
                round(prev_detected / prev_total, 2) if prev_total > 0 else None
            )

    return KneeBendMetric(
        current_rate=round(current_rate, 2),
        previous_rate=previous_rate,
        trend=_knee_bend_trend(current_rate, previous_rate),
        data_points=data_points,
    )


def _compute_court_side(
    db: Session,
    user_id: str,
    player_id: Optional[int],
    window_start: Optional[datetime],
) -> CourtSideDistribution:
    """Compute court side distribution."""
    serves = (
        _query_serves(db, user_id, player_id, window_start)
        .with_entities(ServeAttempt.court_side)
        .all()
    )

    deuce = sum(1 for s in serves if s[0] == "deuce")
    ad = sum(1 for s in serves if s[0] == "ad")
    unknown = sum(1 for s in serves if s[0] is None or s[0] not in ("deuce", "ad"))

    return CourtSideDistribution(deuce=deuce, ad=ad, unknown=unknown)


def get_progress(
    db: Session,
    user_id: str,
    player_id: Optional[int] = None,
    time_period: str = "30d",
) -> ProgressResponse:
    """Compute aggregated progress data for the authenticated user.

    Args:
        db: Database session.
        user_id: Authenticated user ID (scopes all queries).
        player_id: Optional player filter.
        time_period: "7d", "30d", or "all".

    Returns:
        ProgressResponse with aggregated metrics.
    """
    window_start = _parse_time_window(time_period)

    # Total serves and videos in window
    base = _query_serves(db, user_id, player_id, window_start)

    total_serves = base.count()
    total_videos = base.with_entities(Video.id).distinct().count()

    elbow_metric = _compute_elbow_angle_metric(
        db, user_id, player_id, window_start, time_period
    )
    knee_metric = _compute_knee_bend_metric(
        db, user_id, player_id, window_start, time_period
    )
    court_side = _compute_court_side(db, user_id, player_id, window_start)

    logger.info(
        "Progress computed for user=%s period=%s: %d serves, %d videos",
        user_id,
        time_period,
        total_serves,
        total_videos,
    )

    return ProgressResponse(
        time_period=time_period,
        total_serves=total_serves,
        total_videos=total_videos,
        metrics=ProgressMetrics(
            elbow_angle=elbow_metric,
            knee_bend=knee_metric,
        ),
        court_side=court_side,
    )
