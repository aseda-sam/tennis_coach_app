"""
Tests for the automated pipeline: auto-accept proposals + auto-compute biomechanics.

Validates that after pose analysis, high-confidence proposals are auto-accepted
and biomechanics are computed without manual intervention.
"""

from unittest.mock import MagicMock, patch

import pytest
from sqlalchemy.orm import Session

from app.models.player import Player
from app.models.serve_window import ServeWindow
from app.models.video import Video
from app.services.serve_detection.proposal_service import auto_accept_proposals


@pytest.fixture
def test_video(db_session: Session, test_user_id: str) -> Video:
    """Create a test video."""
    video = Video(
        user_id=test_user_id,
        filename="test_video.mp4",
        file_path="/test/path/video.mp4",
        file_size=1024000,
        content_type="video/mp4",
        status="uploaded",
        fps=30.0,
        width=1920,
        height=1080,
    )
    db_session.add(video)
    db_session.commit()
    db_session.refresh(video)
    return video


@pytest.fixture
def test_player(db_session: Session, test_user_id: str) -> Player:
    """Create a test player."""
    player = Player(
        user_id=test_user_id,
        name="Test Player",
        dominant_hand="right",
    )
    db_session.add(player)
    db_session.commit()
    db_session.refresh(player)
    return player


@pytest.fixture
def proposals_mixed_confidence(
    db_session: Session,
    test_video: Video,
    test_user_id: str,
) -> list[ServeWindow]:
    """Create proposals with varying confidence levels."""
    proposals = [
        ServeWindow(
            video_id=test_video.id,
            user_id=test_user_id,
            start_timestamp=1.0,
            end_timestamp=3.0,
            source="auto",
            status="pending",
            confidence=0.9,
        ),
        ServeWindow(
            video_id=test_video.id,
            user_id=test_user_id,
            start_timestamp=5.0,
            end_timestamp=7.0,
            source="auto",
            status="pending",
            confidence=0.75,
        ),
        ServeWindow(
            video_id=test_video.id,
            user_id=test_user_id,
            start_timestamp=9.0,
            end_timestamp=11.0,
            source="auto",
            status="pending",
            confidence=0.4,
        ),
    ]
    for p in proposals:
        db_session.add(p)
    db_session.commit()
    for p in proposals:
        db_session.refresh(p)
    return proposals


class TestAutoAcceptProposals:
    """Tests for auto_accept_proposals service function."""

    def test_accepts_above_threshold_rejects_below(
        self,
        db_session: Session,
        test_video: Video,
        test_player: Player,
        test_user_id: str,
        proposals_mixed_confidence: list[ServeWindow],
    ) -> None:
        """Proposals above threshold are accepted, below are rejected."""
        test_video.primary_player_id = test_player.id
        db_session.commit()

        accepted = auto_accept_proposals(
            db=db_session,
            video_id=test_video.id,
            user_id=test_user_id,
            confidence_threshold=0.6,
        )

        assert len(accepted) == 2
        assert all(s.status == "accepted" for s in accepted)
        assert all(s.player_id == test_player.id for s in accepted)

        rejected = (
            db_session.query(ServeWindow)
            .filter(
                ServeWindow.video_id == test_video.id,
                ServeWindow.status == "rejected",
            )
            .all()
        )
        assert len(rejected) == 1
        assert rejected[0].confidence == 0.4

    def test_uses_default_player_when_no_primary(
        self,
        db_session: Session,
        test_video: Video,
        test_user_id: str,
        proposals_mixed_confidence: list[ServeWindow],
    ) -> None:
        """Falls back to default player when video has no primary_player_id."""
        assert test_video.primary_player_id is None

        accepted = auto_accept_proposals(
            db=db_session,
            video_id=test_video.id,
            user_id=test_user_id,
            confidence_threshold=0.6,
        )

        assert len(accepted) == 2
        assert all(s.player_id is not None for s in accepted)

    def test_returns_empty_when_no_proposals(
        self,
        db_session: Session,
        test_video: Video,
        test_user_id: str,
    ) -> None:
        """Returns empty list when no pending proposals exist."""
        accepted = auto_accept_proposals(
            db=db_session,
            video_id=test_video.id,
            user_id=test_user_id,
        )

        assert accepted == []

    def test_uses_config_default_threshold(
        self,
        db_session: Session,
        test_video: Video,
        test_player: Player,
        test_user_id: str,
        proposals_mixed_confidence: list[ServeWindow],
    ) -> None:
        """Uses AUTO_ACCEPT_CONFIDENCE_THRESHOLD from config when no threshold passed."""
        test_video.primary_player_id = test_player.id
        db_session.commit()

        with patch("app.core.config.settings") as mock_settings:
            mock_settings.AUTO_ACCEPT_CONFIDENCE_THRESHOLD = 0.8

            accepted = auto_accept_proposals(
                db=db_session,
                video_id=test_video.id,
                user_id=test_user_id,
            )

        assert len(accepted) == 1
        assert accepted[0].confidence == 0.9


class TestComputeBiomechanicsBatch:
    """Tests for compute_biomechanics_batch service function."""

    def test_computes_for_all_accepted_windows(
        self,
        db_session: Session,
        test_video: Video,
        test_player: Player,
        test_user_id: str,
    ) -> None:
        """Biomechanics are computed for each accepted serve window."""
        windows = []
        for i in range(3):
            sw = ServeWindow(
                video_id=test_video.id,
                user_id=test_user_id,
                player_id=test_player.id,
                start_timestamp=float(i * 4),
                end_timestamp=float(i * 4 + 2),
                source="auto",
                status="accepted",
                confidence=0.9,
            )
            db_session.add(sw)
            windows.append(sw)
        db_session.commit()
        for sw in windows:
            db_session.refresh(sw)

        from app.services.biomechanics.serve_biomechanics_service import (
            compute_biomechanics_batch,
        )

        with patch(
            "app.services.biomechanics.serve_biomechanics_service.serve_biomechanics_service"
        ) as mock_service:
            mock_report = MagicMock()
            mock_report.id = 1
            mock_service.compute_analysis.return_value = mock_report

            compute_biomechanics_batch(
                db=db_session,
                video_id=test_video.id,
                user_id=test_user_id,
            )

        assert mock_service.compute_analysis.call_count == 3

    def test_skips_windows_with_existing_reports(
        self,
        db_session: Session,
        test_video: Video,
        test_player: Player,
        test_user_id: str,
    ) -> None:
        """Windows that already have reports are skipped."""
        sw = ServeWindow(
            video_id=test_video.id,
            user_id=test_user_id,
            player_id=test_player.id,
            start_timestamp=1.0,
            end_timestamp=3.0,
            source="auto",
            status="accepted",
            confidence=0.9,
        )
        db_session.add(sw)
        db_session.commit()
        db_session.refresh(sw)

        from app.services.biomechanics.serve_biomechanics_service import (
            compute_biomechanics_batch,
        )

        with patch(
            "app.services.biomechanics.serve_biomechanics_service.serve_biomechanics_service"
        ) as mock_service:
            mock_service.get_or_compute_analysis.return_value = MagicMock()
            mock_service.compute_analysis.return_value = MagicMock()

            compute_biomechanics_batch(
                db=db_session,
                video_id=test_video.id,
                user_id=test_user_id,
            )

        assert mock_service.compute_analysis.call_count == 1
