"""Tests for Progress Overview API and service."""

import uuid
from datetime import datetime, timedelta, timezone

from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.models.player import Player
from app.models.serve_attempt import ServeAttempt
from app.models.video import Video
from app.services import progress_service


def _create_player(db: Session, user_id: str, name: str = "Test Player") -> Player:
    player = Player(name=name, user_id=user_id, dominant_hand="right")
    db.add(player)
    db.commit()
    db.refresh(player)
    return player


def _create_video(
    db: Session, user_id: str, recorded_at: datetime, player_id: int | None = None
) -> Video:
    unique = uuid.uuid4().hex[:8]
    video = Video(
        filename=f"test_{unique}.mp4",
        file_path=f"/tmp/test_{unique}.mp4",  # noqa: S108
        file_size=1000,
        user_id=user_id,
        recorded_at=recorded_at,
        status="completed",
        primary_player_id=player_id,
    )
    db.add(video)
    db.commit()
    db.refresh(video)
    return video


def _create_serve(
    db: Session,
    video_id: int,
    user_id: str,
    player_id: int,
    elbow_angle: float | None = None,
    knee_bend: bool | None = None,
    court_side: str | None = None,
) -> ServeAttempt:
    serve = ServeAttempt(
        video_id=video_id,
        user_id=user_id,
        player_id=player_id,
        start_timestamp=0.0,
        end_timestamp=2.0,
        elbow_angle_at_contact=elbow_angle,
        knee_bend_detected=knee_bend,
        court_side=court_side,
    )
    db.add(serve)
    db.commit()
    db.refresh(serve)
    return serve


# === Contract tests (API endpoint) ===


class TestProgressAPI:
    """Contract tests for GET /v0/progress/me."""

    def test_returns_200_with_correct_shape(
        self, client: TestClient, db_session: Session, test_user_id: str
    ) -> None:
        """Endpoint returns valid ProgressResponse shape."""
        response = client.get("/v0/progress/me")
        assert response.status_code == 200

        data = response.json()
        assert "time_period" in data
        assert "total_serves" in data
        assert "total_videos" in data
        assert "metrics" in data
        assert "court_side" in data
        assert data["time_period"] == "30d"

    def test_empty_data_returns_zeros(
        self, client: TestClient, db_session: Session
    ) -> None:
        """With no data, returns zero counts and null metrics."""
        response = client.get("/v0/progress/me")
        data = response.json()

        assert data["total_serves"] == 0
        assert data["total_videos"] == 0
        assert data["metrics"]["elbow_angle"] is None
        assert data["metrics"]["knee_bend"] is None
        assert data["court_side"]["deuce"] == 0
        assert data["court_side"]["ad"] == 0
        assert data["court_side"]["unknown"] == 0

    def test_time_period_filter(self, client: TestClient, db_session: Session) -> None:
        """Accepts 7d, 30d, and all time periods."""
        for period in ["7d", "30d", "all"]:
            response = client.get(f"/v0/progress/me?time_period={period}")
            assert response.status_code == 200
            assert response.json()["time_period"] == period

    def test_invalid_time_period_rejected(
        self, client: TestClient, db_session: Session
    ) -> None:
        """Invalid time_period returns 422."""
        response = client.get("/v0/progress/me?time_period=90d")
        assert response.status_code == 422

    def test_with_real_data(
        self, client: TestClient, db_session: Session, test_user_id: str
    ) -> None:
        """Endpoint returns real aggregated data."""
        player = _create_player(db_session, test_user_id)
        video = _create_video(
            db_session, test_user_id, datetime.now(timezone.utc), player.id
        )
        _create_serve(
            db_session,
            video.id,
            test_user_id,
            player.id,
            elbow_angle=150.0,
            knee_bend=True,
            court_side="deuce",
        )
        _create_serve(
            db_session,
            video.id,
            test_user_id,
            player.id,
            elbow_angle=155.0,
            knee_bend=False,
            court_side="ad",
        )

        response = client.get("/v0/progress/me?time_period=all")
        data = response.json()

        assert data["total_serves"] == 2
        assert data["total_videos"] == 1
        assert data["metrics"]["elbow_angle"] is not None
        assert data["metrics"]["elbow_angle"]["current_avg"] == 152.5
        assert data["metrics"]["knee_bend"] is not None
        assert data["metrics"]["knee_bend"]["current_rate"] == 0.5
        assert data["court_side"]["deuce"] == 1
        assert data["court_side"]["ad"] == 1


# === Service unit tests ===


class TestProgressService:
    """Unit tests for progress_service.get_progress."""

    def test_no_data(self, db_session: Session, test_user_id: str) -> None:
        """Returns zero counts when user has no data."""
        result = progress_service.get_progress(
            db_session, test_user_id, time_period="all"
        )

        assert result.total_serves == 0
        assert result.total_videos == 0
        assert result.metrics.elbow_angle is None
        assert result.metrics.knee_bend is None

    def test_single_video_elbow_angle(
        self, db_session: Session, test_user_id: str
    ) -> None:
        """Elbow angle computed correctly for single video."""
        player = _create_player(db_session, test_user_id)
        video = _create_video(
            db_session, test_user_id, datetime.now(timezone.utc), player.id
        )
        _create_serve(db_session, video.id, test_user_id, player.id, elbow_angle=140.0)
        _create_serve(db_session, video.id, test_user_id, player.id, elbow_angle=160.0)

        result = progress_service.get_progress(
            db_session, test_user_id, time_period="all"
        )

        assert result.metrics.elbow_angle is not None
        assert result.metrics.elbow_angle.current_avg == 150.0
        assert result.metrics.elbow_angle.trend == "stable"
        assert len(result.metrics.elbow_angle.data_points) == 1
        assert result.metrics.elbow_angle.data_points[0].count == 2

    def test_elbow_angle_consistency_rating(
        self, db_session: Session, test_user_id: str
    ) -> None:
        """Consistency rating based on std deviation thresholds."""
        player = _create_player(db_session, test_user_id)
        video = _create_video(
            db_session, test_user_id, datetime.now(timezone.utc), player.id
        )
        # All same angle -> std dev = 0 -> excellent
        _create_serve(db_session, video.id, test_user_id, player.id, elbow_angle=150.0)
        _create_serve(db_session, video.id, test_user_id, player.id, elbow_angle=150.0)

        result = progress_service.get_progress(
            db_session, test_user_id, time_period="all"
        )

        assert result.metrics.elbow_angle is not None
        assert result.metrics.elbow_angle.consistency == 0.0
        assert result.metrics.elbow_angle.consistency_rating == "excellent"

    def test_knee_bend_rate(self, db_session: Session, test_user_id: str) -> None:
        """Knee bend rate computed as fraction of detected bends."""
        player = _create_player(db_session, test_user_id)
        video = _create_video(
            db_session, test_user_id, datetime.now(timezone.utc), player.id
        )
        _create_serve(db_session, video.id, test_user_id, player.id, knee_bend=True)
        _create_serve(db_session, video.id, test_user_id, player.id, knee_bend=True)
        _create_serve(db_session, video.id, test_user_id, player.id, knee_bend=False)
        _create_serve(db_session, video.id, test_user_id, player.id, knee_bend=False)

        result = progress_service.get_progress(
            db_session, test_user_id, time_period="all"
        )

        assert result.metrics.knee_bend is not None
        assert result.metrics.knee_bend.current_rate == 0.5

    def test_court_side_distribution(
        self, db_session: Session, test_user_id: str
    ) -> None:
        """Court side counts deuce, ad, unknown correctly."""
        player = _create_player(db_session, test_user_id)
        video = _create_video(
            db_session, test_user_id, datetime.now(timezone.utc), player.id
        )
        _create_serve(db_session, video.id, test_user_id, player.id, court_side="deuce")
        _create_serve(db_session, video.id, test_user_id, player.id, court_side="deuce")
        _create_serve(db_session, video.id, test_user_id, player.id, court_side="ad")
        _create_serve(db_session, video.id, test_user_id, player.id, court_side=None)

        result = progress_service.get_progress(
            db_session, test_user_id, time_period="all"
        )

        assert result.court_side.deuce == 2
        assert result.court_side.ad == 1
        assert result.court_side.unknown == 1

    def test_time_window_filtering(
        self, db_session: Session, test_user_id: str
    ) -> None:
        """7d window excludes older videos."""
        player = _create_player(db_session, test_user_id)
        now = datetime.now(timezone.utc)

        # Recent video (within 7d)
        v1 = _create_video(db_session, test_user_id, now - timedelta(days=2), player.id)
        _create_serve(db_session, v1.id, test_user_id, player.id, elbow_angle=150.0)

        # Old video (outside 7d)
        v2 = _create_video(
            db_session, test_user_id, now - timedelta(days=20), player.id
        )
        _create_serve(db_session, v2.id, test_user_id, player.id, elbow_angle=130.0)

        result_7d = progress_service.get_progress(
            db_session, test_user_id, time_period="7d"
        )
        result_all = progress_service.get_progress(
            db_session, test_user_id, time_period="all"
        )

        assert result_7d.total_serves == 1
        assert result_7d.total_videos == 1
        assert result_all.total_serves == 2
        assert result_all.total_videos == 2

    def test_trend_improving_toward_healthy_range(
        self, db_session: Session, test_user_id: str
    ) -> None:
        """Elbow angle trend 'improving' when moving toward 140-170 range."""
        player = _create_player(db_session, test_user_id)
        now = datetime.now(timezone.utc)

        # Previous window: angle far from healthy range
        v_old = _create_video(
            db_session, test_user_id, now - timedelta(days=50), player.id
        )
        _create_serve(db_session, v_old.id, test_user_id, player.id, elbow_angle=120.0)

        # Current window: angle closer to healthy range
        v_new = _create_video(
            db_session, test_user_id, now - timedelta(days=5), player.id
        )
        _create_serve(db_session, v_new.id, test_user_id, player.id, elbow_angle=145.0)

        result = progress_service.get_progress(
            db_session, test_user_id, time_period="30d"
        )

        assert result.metrics.elbow_angle is not None
        assert result.metrics.elbow_angle.trend == "improving"

    def test_multiple_videos_create_multiple_data_points(
        self, db_session: Session, test_user_id: str
    ) -> None:
        """Each video becomes one data point in the trend chart."""
        player = _create_player(db_session, test_user_id)
        now = datetime.now(timezone.utc)

        for i in range(3):
            video = _create_video(
                db_session, test_user_id, now - timedelta(days=i), player.id
            )
            _create_serve(
                db_session,
                video.id,
                test_user_id,
                player.id,
                elbow_angle=150.0 + i,
            )

        result = progress_service.get_progress(
            db_session, test_user_id, time_period="all"
        )

        assert result.metrics.elbow_angle is not None
        assert len(result.metrics.elbow_angle.data_points) == 3
        assert result.total_videos == 3

    def test_serves_without_metrics_excluded_from_metric_but_counted(
        self, db_session: Session, test_user_id: str
    ) -> None:
        """Serves missing elbow angle are excluded from elbow metric but counted in total."""
        player = _create_player(db_session, test_user_id)
        video = _create_video(
            db_session, test_user_id, datetime.now(timezone.utc), player.id
        )
        _create_serve(db_session, video.id, test_user_id, player.id, elbow_angle=150.0)
        _create_serve(db_session, video.id, test_user_id, player.id)  # no metrics

        result = progress_service.get_progress(
            db_session, test_user_id, time_period="all"
        )

        assert result.total_serves == 2
        assert result.metrics.elbow_angle is not None
        assert result.metrics.elbow_angle.data_points[0].count == 1

    def test_player_id_filter(self, db_session: Session, test_user_id: str) -> None:
        """player_id filters to specific player's serves."""
        p1 = _create_player(db_session, test_user_id, name="Player A")
        p2 = _create_player(db_session, test_user_id, name="Player B")
        video = _create_video(db_session, test_user_id, datetime.now(timezone.utc))
        _create_serve(db_session, video.id, test_user_id, p1.id, elbow_angle=150.0)
        _create_serve(db_session, video.id, test_user_id, p2.id, elbow_angle=160.0)

        result = progress_service.get_progress(
            db_session, test_user_id, player_id=p1.id, time_period="all"
        )

        assert result.total_serves == 1
        assert result.metrics.elbow_angle is not None
        assert result.metrics.elbow_angle.current_avg == 150.0

    def test_user_scoping(self, db_session: Session, test_user_id: str) -> None:
        """Only returns data for the authenticated user."""
        other_user = "11111111-1111-1111-1111-111111111111"
        player = _create_player(db_session, other_user, name="Other")
        video = _create_video(
            db_session, other_user, datetime.now(timezone.utc), player.id
        )
        _create_serve(db_session, video.id, other_user, player.id, elbow_angle=150.0)

        result = progress_service.get_progress(
            db_session, test_user_id, time_period="all"
        )

        assert result.total_serves == 0


# === Trend logic unit tests ===


class TestTrendLogic:
    """Unit tests for trend calculation helper functions."""

    def test_elbow_trend_stable_when_no_previous(self) -> None:
        assert progress_service._elbow_trend(150.0, None) == "stable"

    def test_elbow_trend_improving_toward_healthy(self) -> None:
        # 120 -> 145 is moving toward 155 midpoint
        assert progress_service._elbow_trend(145.0, 120.0) == "improving"

    def test_elbow_trend_declining_away_from_healthy(self) -> None:
        # 145 -> 120 is moving away from 155 midpoint
        assert progress_service._elbow_trend(120.0, 145.0) == "declining"

    def test_elbow_trend_stable_within_threshold(self) -> None:
        # Both at same distance from healthy midpoint (155) -> stable
        assert progress_service._elbow_trend(155.0, 155.0) == "stable"
        # Tiny change: 154 -> 155 (distance 1 -> 0, but relative to 1 that's 100% so this improves)
        # Use values where the relative change is < 3%
        assert progress_service._elbow_trend(150.0, 150.1) == "stable"

    def test_knee_bend_trend_improving(self) -> None:
        assert progress_service._knee_bend_trend(0.85, 0.70) == "improving"

    def test_knee_bend_trend_declining(self) -> None:
        assert progress_service._knee_bend_trend(0.50, 0.80) == "declining"

    def test_knee_bend_trend_stable_when_no_previous(self) -> None:
        assert progress_service._knee_bend_trend(0.85, None) == "stable"

    def test_consistency_ratings(self) -> None:
        assert progress_service._consistency_rating(3.0) == "excellent"
        assert progress_service._consistency_rating(5.0) == "excellent"
        assert progress_service._consistency_rating(7.0) == "good"
        assert progress_service._consistency_rating(10.0) == "good"
        assert progress_service._consistency_rating(12.0) == "fair"
        assert progress_service._consistency_rating(15.0) == "fair"
        assert progress_service._consistency_rating(20.0) == "needs_work"
