"""
Tests for serve detection API endpoints.

Tests the bulk accept and reject operations for serve window proposals.
"""

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.models.player import Player
from app.models.serve_attempt import ServeAttempt
from app.models.serve_window_proposal import ServeWindowProposal
from app.models.video import Video


@pytest.fixture
def test_video(db_session: Session, test_user_id: str) -> Video:
    """Create a test video."""
    video = Video(
        user_id=test_user_id,
        filename="test_video.mp4",
        file_path="/test/path/video.mp4",
        file_size=1024000,  # Required field
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
def test_proposals(
    db_session: Session, test_video: Video, test_user_id: str
) -> list[ServeWindowProposal]:
    """Create test proposals with varying confidence levels."""
    proposals = [
        ServeWindowProposal(
            video_id=test_video.id,
            user_id=test_user_id,
            start_timestamp=0.0,
            end_timestamp=2.0,
            model_version="test-v1",
            confidence=0.85,  # High confidence
            status="pending",
        ),
        ServeWindowProposal(
            video_id=test_video.id,
            user_id=test_user_id,
            start_timestamp=3.0,
            end_timestamp=5.0,
            model_version="test-v1",
            confidence=0.72,  # Medium confidence
            status="pending",
        ),
        ServeWindowProposal(
            video_id=test_video.id,
            user_id=test_user_id,
            start_timestamp=6.0,
            end_timestamp=8.0,
            model_version="test-v1",
            confidence=0.55,  # Low confidence (below 60%)
            status="pending",
        ),
        ServeWindowProposal(
            video_id=test_video.id,
            user_id=test_user_id,
            start_timestamp=9.0,
            end_timestamp=11.0,
            model_version="test-v1",
            confidence=0.45,  # Low confidence (below 60%)
            status="pending",
        ),
    ]
    for p in proposals:
        db_session.add(p)
    db_session.commit()
    for p in proposals:
        db_session.refresh(p)
    return proposals


class TestBulkAcceptProposals:
    """Tests for POST /videos/{video_id}/serve-detection/proposals/accept-all."""

    def test_accept_all_creates_serve_attempts(
        self,
        client: TestClient,
        db_session: Session,
        test_video: Video,
        test_player: Player,
        test_proposals: list[ServeWindowProposal],
    ) -> None:
        """Accepting all proposals should create serve attempts for each."""
        response = client.post(
            f"/v0/videos/{test_video.id}/serve-detection/proposals/accept-all",
            json={},
        )

        assert response.status_code == 200
        data = response.json()
        assert data["video_id"] == test_video.id
        assert data["accepted_count"] == 4
        assert len(data["serve_attempt_ids"]) == 4

        # Verify serve attempts were created
        serve_attempts = (
            db_session.query(ServeAttempt)
            .filter(ServeAttempt.video_id == test_video.id)
            .all()
        )
        assert len(serve_attempts) == 4

        # Verify proposals are now accepted
        for proposal in test_proposals:
            db_session.refresh(proposal)
            assert proposal.status == "accepted"

    def test_accept_all_with_no_proposals_returns_error(
        self,
        client: TestClient,
        test_video: Video,
    ) -> None:
        """Accepting when no pending proposals exist should return error."""
        response = client.post(
            f"/v0/videos/{test_video.id}/serve-detection/proposals/accept-all",
            json={},
        )

        assert response.status_code == 400

    def test_accept_all_with_player_id(
        self,
        client: TestClient,
        db_session: Session,
        test_video: Video,
        test_player: Player,
        test_proposals: list[ServeWindowProposal],
    ) -> None:
        """Accepting with explicit player_id should use that player."""
        response = client.post(
            f"/v0/videos/{test_video.id}/serve-detection/proposals/accept-all",
            json={"player_id": test_player.id},
        )

        assert response.status_code == 200

        # Verify all serve attempts have the specified player
        serve_attempts = (
            db_session.query(ServeAttempt)
            .filter(ServeAttempt.video_id == test_video.id)
            .all()
        )
        for sa in serve_attempts:
            assert sa.player_id == test_player.id


class TestRejectByConfidence:
    """Tests for POST /videos/{video_id}/serve-detection/proposals/reject-by-confidence."""

    def test_reject_below_threshold(
        self,
        client: TestClient,
        db_session: Session,
        test_video: Video,
        test_proposals: list[ServeWindowProposal],
    ) -> None:
        """Should reject only proposals below the confidence threshold."""
        response = client.post(
            f"/v0/videos/{test_video.id}/serve-detection/proposals/reject-by-confidence",
            json={"threshold": 0.6},
        )

        assert response.status_code == 200
        data = response.json()
        assert data["video_id"] == test_video.id
        assert data["rejected_count"] == 2  # 0.55 and 0.45 are below 0.6
        assert data["threshold"] == 0.6

        # Verify correct proposals were rejected
        for proposal in test_proposals:
            db_session.refresh(proposal)
            if proposal.confidence < 0.6:
                assert proposal.status == "rejected"
            else:
                assert proposal.status == "pending"

    def test_reject_with_custom_threshold(
        self,
        client: TestClient,
        db_session: Session,
        test_video: Video,
        test_proposals: list[ServeWindowProposal],
    ) -> None:
        """Should respect custom threshold value."""
        response = client.post(
            f"/v0/videos/{test_video.id}/serve-detection/proposals/reject-by-confidence",
            json={"threshold": 0.8},
        )

        assert response.status_code == 200
        data = response.json()
        # 0.72, 0.55, 0.45 are all below 0.8
        assert data["rejected_count"] == 3

    def test_reject_with_no_matches_returns_zero(
        self,
        client: TestClient,
        db_session: Session,
        test_video: Video,
        test_proposals: list[ServeWindowProposal],
    ) -> None:
        """Should return 0 when no proposals are below threshold."""
        response = client.post(
            f"/v0/videos/{test_video.id}/serve-detection/proposals/reject-by-confidence",
            json={"threshold": 0.1},  # Very low threshold
        )

        assert response.status_code == 200
        data = response.json()
        assert data["rejected_count"] == 0

    def test_reject_invalid_threshold_returns_error(
        self,
        client: TestClient,
        test_video: Video,
        test_proposals: list[ServeWindowProposal],
    ) -> None:
        """Should return error for invalid threshold values."""
        # Threshold > 1
        response = client.post(
            f"/v0/videos/{test_video.id}/serve-detection/proposals/reject-by-confidence",
            json={"threshold": 1.5},
        )
        assert response.status_code == 422  # Validation error

        # Threshold < 0
        response = client.post(
            f"/v0/videos/{test_video.id}/serve-detection/proposals/reject-by-confidence",
            json={"threshold": -0.1},
        )
        assert response.status_code == 422


class TestBulkWorkflow:
    """Tests for the combined bulk workflow: reject low confidence, then accept all."""

    def test_reject_then_accept_workflow(
        self,
        client: TestClient,
        db_session: Session,
        test_video: Video,
        test_player: Player,
        test_proposals: list[ServeWindowProposal],
    ) -> None:
        """Should be able to reject low confidence, then accept remaining."""
        # Step 1: Reject low confidence proposals
        reject_response = client.post(
            f"/v0/videos/{test_video.id}/serve-detection/proposals/reject-by-confidence",
            json={"threshold": 0.6},
        )
        assert reject_response.status_code == 200
        assert reject_response.json()["rejected_count"] == 2

        # Step 2: Accept all remaining proposals
        accept_response = client.post(
            f"/v0/videos/{test_video.id}/serve-detection/proposals/accept-all",
            json={},
        )
        assert accept_response.status_code == 200
        assert (
            accept_response.json()["accepted_count"] == 2
        )  # Only high confidence ones

        # Verify final state
        serve_attempts = (
            db_session.query(ServeAttempt)
            .filter(ServeAttempt.video_id == test_video.id)
            .all()
        )
        assert len(serve_attempts) == 2

        # Verify all proposals are now reviewed
        pending = (
            db_session.query(ServeWindowProposal)
            .filter(
                ServeWindowProposal.video_id == test_video.id,
                ServeWindowProposal.status == "pending",
            )
            .count()
        )
        assert pending == 0
