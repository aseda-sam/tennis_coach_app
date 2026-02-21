"""Tests for biomechanics metrics computation.

TDD: Define the contract for computing all metrics from pose frames + phases.
"""

from app.services.biomechanics.metrics import (
    METRIC_META,
    BiomechanicsMetrics,
    compute_biomechanics_metrics,
    metrics_to_flat_list,
)
from app.services.biomechanics.phase_segmentation import (
    PhaseWindow,
    segment_serve_phases,
)
from tests.biomechanics_fixtures import _make_pose, _make_serve_sequence


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
        assert 80 <= result.knee_flexion_min_deg <= 180

    def test_knee_flexion_outlier_gate(self):
        """Values below 80° should be rejected as pose artifacts."""
        # Build frames where knees are impossibly bent (very high knee_y = deep bend)
        frames = [_make_pose(knee_y=0.95) for _ in range(10)]
        result = compute_biomechanics_metrics(
            pose_frames=frames,
            fps=30.0,
            serve_start=0.0,
            serve_end=0.33,
            contact_timestamp=None,
            dominant_hand="right",
            video_width=1280,
            video_height=720,
        )
        # The extremely deep bend produces an angle < 80° → should be gated to None
        if result.knee_flexion_min_deg is not None:
            assert result.knee_flexion_min_deg >= 80.0

    def test_left_handed_dominant_hand(self):
        """Metrics compute without error for left-handed player."""
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
        # Active metrics should still be present
        assert result.knee_flexion_min_deg is not None

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

    def test_handles_no_phases(self):
        """Should still compute metrics without phase data."""
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
        # Knee flexion doesn't depend on phases
        assert result.knee_flexion_min_deg is not None


class TestMetricsToFlatList:
    def test_only_includes_meta_entries(self):
        """metrics_to_flat_list should only include metrics present in METRIC_META."""
        metrics = BiomechanicsMetrics(
            knee_flexion_min_deg=95.0,
            toss_peak_height=1.8,
            toss_laterality=0.15,
        )
        flat = metrics_to_flat_list(metrics)
        names = {m["metric_name"] for m in flat}

        assert names == set(METRIC_META.keys())
        assert "knee_flexion_min_deg" in names
        assert "toss_peak_height" in names
        assert "toss_laterality" in names

    def test_flat_list_has_correct_structure(self):
        """Each entry in flat list should have metric_name, value, unit, phase."""
        metrics = BiomechanicsMetrics(knee_flexion_min_deg=100.0)
        flat = metrics_to_flat_list(metrics)
        for entry in flat:
            assert "metric_name" in entry
            assert "value" in entry
            assert "unit" in entry
            assert "phase" in entry

    def test_flat_list_includes_none_values(self):
        """Metrics with None values should still appear in flat list."""
        metrics = BiomechanicsMetrics()  # all None
        flat = metrics_to_flat_list(metrics)
        assert len(flat) == len(METRIC_META)
        for entry in flat:
            assert entry["value"] is None
