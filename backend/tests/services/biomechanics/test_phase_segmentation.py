"""Tests for serve phase segmentation.

TDD: Define the contract for phase detection from pose keypoint curves.
"""

from app.services.biomechanics.phase_segmentation import (
    PhaseSegmentationResult,
    PhaseWindow,
    ServePhase,
    segment_serve_phases,
)
from tests.biomechanics_fixtures import _make_serve_sequence


class TestSegmentServePhases:
    def test_returns_phase_segmentation_result(self):
        """Should return a PhaseSegmentationResult."""
        frames = _make_serve_sequence()
        result = segment_serve_phases(
            pose_frames=frames,
            fps=30.0,
            serve_start=0.0,
            serve_end=2.0,
            contact_timestamp=1.3,  # frame 39
            dominant_hand="right",
            video_width=1280,
            video_height=720,
        )
        assert isinstance(result, PhaseSegmentationResult)

    def test_returns_list_of_phase_windows(self):
        frames = _make_serve_sequence()
        result = segment_serve_phases(
            pose_frames=frames,
            fps=30.0,
            serve_start=0.0,
            serve_end=2.0,
            contact_timestamp=1.3,
            dominant_hand="right",
            video_width=1280,
            video_height=720,
        )
        assert len(result.phases) > 0
        for phase in result.phases:
            assert isinstance(phase, PhaseWindow)

    def test_phases_are_monotonic(self):
        """Phase timestamps must be in order."""
        frames = _make_serve_sequence()
        result = segment_serve_phases(
            pose_frames=frames,
            fps=30.0,
            serve_start=0.0,
            serve_end=2.0,
            contact_timestamp=1.3,
            dominant_hand="right",
            video_width=1280,
            video_height=720,
        )
        timestamps = [p.start_timestamp for p in result.phases]
        assert timestamps == sorted(timestamps)

    def test_start_and_contact_phases_always_present(self):
        """Start and contact phases should always be detected when contact_timestamp given."""
        frames = _make_serve_sequence()
        result = segment_serve_phases(
            pose_frames=frames,
            fps=30.0,
            serve_start=0.0,
            serve_end=2.0,
            contact_timestamp=1.3,
            dominant_hand="right",
            video_width=1280,
            video_height=720,
        )
        phase_names = [p.phase for p in result.phases]
        assert ServePhase.START in phase_names
        assert ServePhase.CONTACT in phase_names

    def test_contact_phase_matches_timestamp(self):
        """Contact phase should use the provided contact_timestamp."""
        frames = _make_serve_sequence()
        result = segment_serve_phases(
            pose_frames=frames,
            fps=30.0,
            serve_start=0.0,
            serve_end=2.0,
            contact_timestamp=1.3,
            dominant_hand="right",
            video_width=1280,
            video_height=720,
        )
        contact_phases = [p for p in result.phases if p.phase == ServePhase.CONTACT]
        assert len(contact_phases) == 1
        assert abs(contact_phases[0].start_timestamp - 1.3) < 0.1

    def test_phases_have_confidence(self):
        """Each phase should have a confidence score between 0 and 1."""
        frames = _make_serve_sequence()
        result = segment_serve_phases(
            pose_frames=frames,
            fps=30.0,
            serve_start=0.0,
            serve_end=2.0,
            contact_timestamp=1.3,
            dominant_hand="right",
            video_width=1280,
            video_height=720,
        )
        for phase in result.phases:
            assert 0.0 <= phase.confidence <= 1.0

    def test_analysis_version_present(self):
        frames = _make_serve_sequence()
        result = segment_serve_phases(
            pose_frames=frames,
            fps=30.0,
            serve_start=0.0,
            serve_end=2.0,
            contact_timestamp=1.3,
            dominant_hand="right",
            video_width=1280,
            video_height=720,
        )
        assert result.analysis_version is not None
        assert len(result.analysis_version) > 0

    def test_detects_multiple_phases(self):
        """Should detect more than just start and contact from a good sequence."""
        frames = _make_serve_sequence()
        result = segment_serve_phases(
            pose_frames=frames,
            fps=30.0,
            serve_start=0.0,
            serve_end=2.0,
            contact_timestamp=1.3,
            dominant_hand="right",
            video_width=1280,
            video_height=720,
        )
        assert (
            result.total_phases_detected >= 4
        )  # At least start, trophy, contact, follow-through

    def test_handles_no_contact_timestamp(self):
        """Should still detect some phases without contact timestamp."""
        frames = _make_serve_sequence()
        result = segment_serve_phases(
            pose_frames=frames,
            fps=30.0,
            serve_start=0.0,
            serve_end=2.0,
            contact_timestamp=None,
            dominant_hand="right",
            video_width=1280,
            video_height=720,
        )
        assert isinstance(result, PhaseSegmentationResult)
        assert result.total_phases_detected >= 1

    def test_handles_empty_frames(self):
        """Should handle empty or all-None frames gracefully."""
        result = segment_serve_phases(
            pose_frames=[],
            fps=30.0,
            serve_start=0.0,
            serve_end=1.0,
            contact_timestamp=0.5,
            dominant_hand="right",
            video_width=1280,
            video_height=720,
        )
        assert isinstance(result, PhaseSegmentationResult)
        # Should at least have start and contact from timestamps
        assert result.total_phases_detected >= 1

    def test_handles_none_frames(self):
        """Frames with None (no pose detected) should be skipped."""
        frames = [None] * 10 + _make_serve_sequence()[10:]
        result = segment_serve_phases(
            pose_frames=frames,
            fps=30.0,
            serve_start=0.0,
            serve_end=2.0,
            contact_timestamp=1.3,
            dominant_hand="right",
            video_width=1280,
            video_height=720,
        )
        assert isinstance(result, PhaseSegmentationResult)

    def test_left_handed_player(self):
        """Should work for left-handed dominant hand (toss arm = right)."""
        frames = _make_serve_sequence()
        result = segment_serve_phases(
            pose_frames=frames,
            fps=30.0,
            serve_start=0.0,
            serve_end=2.0,
            contact_timestamp=1.3,
            dominant_hand="left",
            video_width=1280,
            video_height=720,
        )
        assert isinstance(result, PhaseSegmentationResult)
        assert result.total_phases_detected >= 1

    def test_total_phases_possible_is_eight(self):
        frames = _make_serve_sequence()
        result = segment_serve_phases(
            pose_frames=frames,
            fps=30.0,
            serve_start=0.0,
            serve_end=2.0,
            contact_timestamp=1.3,
            dominant_hand="right",
            video_width=1280,
            video_height=720,
        )
        assert result.total_phases_possible == 8
