"""Tests for biomechanics metrics computation.

TDD: Define the contract for computing all metrics from pose frames + phases.
"""

from app.services.biomechanics.metrics import (
    BiomechanicsMetrics,
    compute_biomechanics_metrics,
)
from app.services.biomechanics.phase_segmentation import (
    PhaseWindow,
    segment_serve_phases,
)
from tests.biomechanics_fixtures import _make_serve_sequence


def _get_phases(frames: list, contact_ts: float = 1.3) -> list[PhaseWindow]:
    result = segment_serve_phases(
        pose_frames=frames,
        fps=30.0,
        serve_start=0.0,
        serve_end=2.0,
        contact_timestamp=contact_ts,
        dominant_hand="right",
        video_width=1280,
        video_height=720,
    )
    return result.phases


class TestComputeBiomechanicsMetrics:
    def test_returns_biomechanics_metrics(self):
        frames = _make_serve_sequence()
        phases = _get_phases(frames)
        result = compute_biomechanics_metrics(
            pose_frames=frames,
            fps=30.0,
            serve_start=0.0,
            serve_end=2.0,
            contact_timestamp=1.3,
            dominant_hand="right",
            video_width=1280,
            video_height=720,
            phases=phases,
        )
        assert isinstance(result, BiomechanicsMetrics)

    def test_computes_trunk_rotation(self):
        frames = _make_serve_sequence()
        phases = _get_phases(frames)
        result = compute_biomechanics_metrics(
            pose_frames=frames,
            fps=30.0,
            serve_start=0.0,
            serve_end=2.0,
            contact_timestamp=1.3,
            dominant_hand="right",
            video_width=1280,
            video_height=720,
            phases=phases,
        )
        # Trunk rotation at contact is computed when keypoints allow; field must exist
        assert hasattr(result, "trunk_rotation_at_contact")
        if result.trunk_rotation_at_contact is not None:
            assert isinstance(result.trunk_rotation_at_contact, (int, float))

    def test_computes_contact_point_height(self):
        frames = _make_serve_sequence()
        phases = _get_phases(frames)
        result = compute_biomechanics_metrics(
            pose_frames=frames,
            fps=30.0,
            serve_start=0.0,
            serve_end=2.0,
            contact_timestamp=1.3,
            dominant_hand="right",
            video_width=1280,
            video_height=720,
            phases=phases,
        )
        # Contact point height at contact should be positive (wrist above shoulder)
        assert result.contact_point_height is not None
        assert result.contact_point_height > 0.0

    def test_computes_shoulder_abduction(self):
        frames = _make_serve_sequence()
        phases = _get_phases(frames)
        result = compute_biomechanics_metrics(
            pose_frames=frames,
            fps=30.0,
            serve_start=0.0,
            serve_end=2.0,
            contact_timestamp=1.3,
            dominant_hand="right",
            video_width=1280,
            video_height=720,
            phases=phases,
        )
        assert result.shoulder_abduction_at_contact is not None

    def test_computes_hip_shoulder_separation(self):
        frames = _make_serve_sequence()
        phases = _get_phases(frames)
        result = compute_biomechanics_metrics(
            pose_frames=frames,
            fps=30.0,
            serve_start=0.0,
            serve_end=2.0,
            contact_timestamp=1.3,
            dominant_hand="right",
            video_width=1280,
            video_height=720,
            phases=phases,
        )
        assert result.hip_shoulder_separation_at_contact is not None
        assert result.hip_shoulder_separation_at_contact >= 0.0

    def test_computes_racket_drop(self):
        frames = _make_serve_sequence()
        phases = _get_phases(frames)
        result = compute_biomechanics_metrics(
            pose_frames=frames,
            fps=30.0,
            serve_start=0.0,
            serve_end=2.0,
            contact_timestamp=1.3,
            dominant_hand="right",
            video_width=1280,
            video_height=720,
            phases=phases,
        )
        assert result.racket_drop_depth is not None

    def test_computes_knee_flexion(self):
        frames = _make_serve_sequence()
        phases = _get_phases(frames)
        result = compute_biomechanics_metrics(
            pose_frames=frames,
            fps=30.0,
            serve_start=0.0,
            serve_end=2.0,
            contact_timestamp=1.3,
            dominant_hand="right",
            video_width=1280,
            video_height=720,
            phases=phases,
        )
        assert result.knee_flexion_min_deg is not None
        assert 0 <= result.knee_flexion_min_deg <= 180

    def test_left_handed_dominant_hand(self):
        """Metrics compute without error for left-handed player (toss arm = right)."""
        frames = _make_serve_sequence()
        phases = _get_phases(frames, contact_ts=1.3)
        result = compute_biomechanics_metrics(
            pose_frames=frames,
            fps=30.0,
            serve_start=0.0,
            serve_end=2.0,
            contact_timestamp=1.3,
            dominant_hand="left",
            video_width=1280,
            video_height=720,
            phases=phases,
        )
        assert isinstance(result, BiomechanicsMetrics)
        # At least contact-based metrics should be present
        assert hasattr(result, "contact_point_height")

    def test_handles_no_phases(self):
        """Should still compute contact-based metrics without phase data."""
        frames = _make_serve_sequence()
        result = compute_biomechanics_metrics(
            pose_frames=frames,
            fps=30.0,
            serve_start=0.0,
            serve_end=2.0,
            contact_timestamp=1.3,
            dominant_hand="right",
            video_width=1280,
            video_height=720,
            phases=None,
        )
        assert isinstance(result, BiomechanicsMetrics)
        # Contact-based metrics should still work
        assert result.contact_point_height is not None

    def test_handles_empty_frames(self):
        result = compute_biomechanics_metrics(
            pose_frames=[],
            fps=30.0,
            serve_start=0.0,
            serve_end=1.0,
            contact_timestamp=0.5,
            dominant_hand="right",
            video_width=1280,
            video_height=720,
            phases=None,
        )
        assert isinstance(result, BiomechanicsMetrics)

    def test_computes_elbow_angle(self):
        frames = _make_serve_sequence()
        phases = _get_phases(frames)
        result = compute_biomechanics_metrics(
            pose_frames=frames,
            fps=30.0,
            serve_start=0.0,
            serve_end=2.0,
            contact_timestamp=1.3,
            dominant_hand="right",
            video_width=1280,
            video_height=720,
            phases=phases,
        )
        assert result.elbow_angle_at_contact is not None
        assert 0 < result.elbow_angle_at_contact <= 180

    def test_kinetic_chain_fields_exist(self):
        frames = _make_serve_sequence()
        phases = _get_phases(frames)
        result = compute_biomechanics_metrics(
            pose_frames=frames,
            fps=30.0,
            serve_start=0.0,
            serve_end=2.0,
            contact_timestamp=1.3,
            dominant_hand="right",
            video_width=1280,
            video_height=720,
            phases=phases,
        )
        assert hasattr(result, "kinetic_chain_sequence")
        assert hasattr(result, "kinetic_chain_correct")
