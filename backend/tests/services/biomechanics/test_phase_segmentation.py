"""Tests for KTP-based serve phase segmentation.

Tests the v3 phase segmentation architecture: 4 Key Time Points (Ball Release,
Trophy Position, Racket Low Point, Ball Impact) detected sequentially, then
4 phases (Toss, Trophy & Load, Acceleration, Follow-Through) always derived
with fallback boundaries when KTPs are missing.
"""

from app.services.biomechanics.phase_segmentation import (
    ANALYSIS_VERSION,
    MomentMarker,
    PhaseSegmentationResult,
    PhaseWindow,
    ServePhase,
    _smooth_velocities,
    segment_serve_phases,
)
from tests.biomechanics_fixtures import (
    _make_asymmetric_serve_sequence,
    _make_serve_sequence,
)

# Standard test params for a right-handed serve
_STANDARD_PARAMS = {
    "fps": 30.0,
    "serve_start": 0.0,
    "serve_end": 2.0,
    "contact_timestamp": 1.3,  # frame 39
    "dominant_hand": "right",
    "video_width": 1280,
    "video_height": 720,
}


def _run_standard():
    return segment_serve_phases(pose_frames=_make_serve_sequence(), **_STANDARD_PARAMS)


class TestContractTests:
    """API contract: result types, field shapes, ordering guarantees."""

    def test_returns_phase_segmentation_result(self):
        result = _run_standard()
        assert isinstance(result, PhaseSegmentationResult)

    def test_returns_list_of_phase_windows(self):
        result = _run_standard()
        assert len(result.phases) > 0
        for phase in result.phases:
            assert isinstance(phase, PhaseWindow)

    def test_phases_are_monotonic(self):
        """Phase start timestamps must be non-decreasing."""
        result = _run_standard()
        timestamps = [p.start_timestamp for p in result.phases]
        assert timestamps == sorted(timestamps)

    def test_phase_frames_are_monotonic(self):
        """Phase start frames must be non-decreasing."""
        result = _run_standard()
        frames = [p.start_frame for p in result.phases]
        assert frames == sorted(frames)

    def test_phases_have_confidence(self):
        result = _run_standard()
        for phase in result.phases:
            assert 0.0 <= phase.confidence <= 1.0

    def test_total_phases_possible_is_four(self):
        result = _run_standard()
        assert result.total_phases_possible == 4

    def test_analysis_version(self):
        result = _run_standard()
        assert result.analysis_version == ANALYSIS_VERSION
        assert result.analysis_version == "phase-seg-v3"

    def test_detection_meta_present(self):
        """detection_meta must be present with ktps, feature_curves, fps, total_frames."""
        result = _run_standard()
        meta = result.detection_meta
        assert meta is not None
        assert "ktps" in meta
        assert "feature_curves" in meta
        assert "fps" in meta
        assert "total_frames" in meta

    def test_detection_meta_ktps_structure(self):
        """detection_meta.ktps must have all 4 KTP keys with frame and method."""
        result = _run_standard()
        ktps = result.detection_meta["ktps"]
        for ktp_name in [
            "ball_release",
            "trophy_position",
            "racket_low_point",
            "ball_impact",
        ]:
            assert ktp_name in ktps, f"Missing KTP: {ktp_name}"
            assert "frame" in ktps[ktp_name]
            assert "method" in ktps[ktp_name]

    def test_detection_meta_feature_curves_structure(self):
        """feature_curves must have 3 arrays matching total_frames length."""
        result = _run_standard()
        curves = result.detection_meta["feature_curves"]
        total = result.detection_meta["total_frames"]
        for key in ["max_wrist_height", "knee_hip_ratio", "max_wrist_velocity"]:
            assert key in curves, f"Missing curve: {key}"
            assert len(curves[key]) == total

    def test_detection_meta_ktp_frames_are_valid(self):
        """Detected KTP frames must be within valid range."""
        result = _run_standard()
        total = result.detection_meta["total_frames"]
        for ktp_name, ktp_data in result.detection_meta["ktps"].items():
            frame = ktp_data.get("frame")
            if frame is not None:
                assert 0 <= frame < total, f"{ktp_name} frame {frame} out of range"

    def test_result_has_moments_list(self):
        """Result must include a moments list with MomentMarker objects."""
        result = _run_standard()
        assert isinstance(result.moments, list)
        assert len(result.moments) == 4
        for m in result.moments:
            assert isinstance(m, MomentMarker)

    def test_ball_impact_moment_detected(self):
        """With contact_timestamp provided, ball_impact moment should be detected."""
        result = _run_standard()
        impact = [m for m in result.moments if m.moment == "ball_impact"]
        assert len(impact) == 1
        assert impact[0].detected is True
        assert impact[0].timestamp is not None
        assert abs(impact[0].timestamp - 1.3) < 0.1


class TestKTPDetection:
    """Key Time Point sequential detection and phase derivation."""

    def test_all_four_phases_always_present(self):
        """A well-formed serve should produce exactly 4 phases."""
        result = _run_standard()
        phase_names = [p.phase for p in result.phases]
        for phase in list(ServePhase):
            assert phase in phase_names, f"Missing phase: {phase.value}"
        assert result.total_phases_detected == 4

    def test_ktp_sequential_ordering(self):
        """KTP-derived phases must appear in order: Toss < Trophy & Load < Acceleration < Follow-Through."""
        result = _run_standard()
        phase_map = {p.phase: p for p in result.phases}

        assert (
            phase_map[ServePhase.TOSS].start_frame
            < phase_map[ServePhase.TROPHY_LOAD].start_frame
        )
        assert (
            phase_map[ServePhase.TROPHY_LOAD].start_frame
            < phase_map[ServePhase.ACCELERATION].start_frame
        )
        assert (
            phase_map[ServePhase.ACCELERATION].start_frame
            < phase_map[ServePhase.FOLLOW_THROUGH].start_frame
        )

    def test_follow_through_starts_near_contact(self):
        """Follow-through should start at or near the contact timestamp."""
        result = _run_standard()
        ft_phases = [p for p in result.phases if p.phase == ServePhase.FOLLOW_THROUGH]
        assert len(ft_phases) == 1
        assert abs(ft_phases[0].start_timestamp - 1.3) < 0.1

    def test_toss_phase_begins_at_frame_zero(self):
        result = _run_standard()
        assert result.phases[0].phase == ServePhase.TOSS
        assert result.phases[0].start_frame == 0


class TestTrophyDetection:
    """Trophy position composite detector tests."""

    def test_trophy_detects_with_any_wrist_above_shoulder(self):
        """Asymmetric trophy (only dominant arm raised) should still produce Trophy & Load."""
        frames = _make_asymmetric_serve_sequence()
        result = segment_serve_phases(pose_frames=frames, **_STANDARD_PARAMS)
        phase_names = [p.phase for p in result.phases]
        assert ServePhase.TROPHY_LOAD in phase_names

    def test_asymmetric_trophy_produces_full_phases(self):
        """Beginner serve with one-arm trophy should still produce all 4 phases."""
        frames = _make_asymmetric_serve_sequence()
        result = segment_serve_phases(pose_frames=frames, **_STANDARD_PARAMS)
        assert result.total_phases_detected == 4


class TestRacketLowPoint:
    """Racket low point spatial detection tests."""

    def test_rlp_detected_after_trophy(self):
        """RLP should be after trophy position."""
        result = _run_standard()
        phase_map = {p.phase: p for p in result.phases}
        assert (
            phase_map[ServePhase.ACCELERATION].start_frame
            > phase_map[ServePhase.TROPHY_LOAD].start_frame
        )

    def test_rlp_detected_before_contact(self):
        """RLP should be before ball impact."""
        result = _run_standard()
        phase_map = {p.phase: p for p in result.phases}
        assert (
            phase_map[ServePhase.ACCELERATION].start_frame
            < phase_map[ServePhase.FOLLOW_THROUGH].start_frame
        )


class TestMissingData:
    """Edge cases: missing contact, empty frames, None frames."""

    def test_no_contact_still_has_all_four_phases(self):
        """Without contact timestamp, all 4 phases should still exist.
        Follow-through should have detected=False and low confidence."""
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
        phase_names = [p.phase for p in result.phases]
        assert len(result.phases) == 4
        for phase in list(ServePhase):
            assert phase in phase_names
        # Follow-through should use fallback
        ft = next(p for p in result.phases if p.phase == ServePhase.FOLLOW_THROUGH)
        assert ft.detected is False
        assert ft.confidence <= 0.5

    def test_handles_empty_frames(self):
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
        assert len(result.phases) == 4
        assert result.total_phases_detected == 4

    def test_handles_none_frames(self):
        """Frames with None (no pose detected) should be skipped gracefully."""
        frames = [None] * 10 + _make_serve_sequence()[10:]
        result = segment_serve_phases(pose_frames=frames, **_STANDARD_PARAMS)
        assert isinstance(result, PhaseSegmentationResult)
        assert len(result.phases) == 4

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
        assert len(result.phases) == 4


class TestFallbackBoundaries:
    """All-None frames or missing KTPs should still produce 4 phases."""

    def test_all_none_frames_produce_four_phases(self):
        """Even with no pose data at all, 4 fallback phases are returned."""
        frames = [None] * 60
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
        assert len(result.phases) == 4
        # Toss always starts at frame 0, so it's always detected.
        # The other 3 phases should use fallbacks (low confidence, not detected).
        for p in result.phases:
            if p.phase != ServePhase.TOSS:
                assert p.confidence <= 0.5
                assert p.detected is False

    def test_fallback_phases_are_monotonic(self):
        frames = [None] * 60
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
        starts = [p.start_frame for p in result.phases]
        assert starts == sorted(starts)
        # Strictly increasing
        for i in range(1, len(starts)):
            assert starts[i] > starts[i - 1]

    def test_fallback_phases_cover_full_window(self):
        frames = [None] * 60
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
        assert result.phases[0].start_frame == 0
        assert result.phases[-1].end_frame == 59


class TestVelocitySmoothing:
    """Velocity smoothing helper tests."""

    def test_smooth_velocities_reduces_spikes(self):
        """A single-frame velocity spike should be dampened by smoothing."""
        features = [
            {"max_wrist_velocity": 10.0},
            {"max_wrist_velocity": 10.0},
            {"max_wrist_velocity": 100.0},  # Spike
            {"max_wrist_velocity": 10.0},
            {"max_wrist_velocity": 10.0},
        ]
        smoothed = _smooth_velocities(features, window=3)
        # Spike frame should be averaged with neighbors
        assert smoothed[2]["max_wrist_velocity"] < 100.0
        assert smoothed[2]["max_wrist_velocity"] == (10.0 + 100.0 + 10.0) / 3

    def test_smooth_velocities_preserves_length(self):
        features = [{"max_wrist_velocity": float(i)} for i in range(10)]
        smoothed = _smooth_velocities(features, window=3)
        assert len(smoothed) == len(features)
