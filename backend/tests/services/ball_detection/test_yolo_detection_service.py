"""Tests for YoloBallDetectionService (mocked model -- no ultralytics required at test time)."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock, patch

import numpy as np

from app.services.ball_detection.yolo_detection_service import (
    DEFAULT_CONFIDENCE,
    YoloBallDetectionService,
    _identify_static_distractors,
    _rotate_frame,
    _select_ball_track,
)
from tests.services.ball_detection import v39_fixture

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_boxes(
    xyxy: list[list[float]],
    confs: list[float],
    classes: list[int],
) -> MagicMock:
    """Create a mock YOLO Boxes object."""
    boxes = MagicMock()
    boxes.__len__ = lambda self: len(confs)

    xyxy_tensor = MagicMock()
    xyxy_tensor.cpu.return_value.numpy.return_value = np.array(xyxy, dtype=np.float32)
    boxes.xyxy = xyxy_tensor

    conf_tensor = MagicMock()
    conf_tensor.cpu.return_value.numpy.return_value = np.array(confs, dtype=np.float32)
    boxes.conf = conf_tensor

    cls_tensor = MagicMock()
    cls_tensor.cpu.return_value.numpy.return_value = np.array(classes, dtype=np.float32)
    boxes.cls = cls_tensor

    return boxes


def _make_yolo_result(
    xyxy: list[list[float]],
    confs: list[float],
    classes: list[int],
) -> MagicMock:
    """Create a mock YOLO Results object."""
    result = MagicMock()
    result.boxes = _make_boxes(xyxy, confs, classes)
    return result


def _make_empty_yolo_result() -> MagicMock:
    """Create a mock YOLO Results with no detections."""
    result = MagicMock()
    boxes = MagicMock()
    boxes.__len__ = lambda self: 0
    result.boxes = boxes
    return result


class _MockDetections:
    """Lightweight mock for sv.Detections that supports boolean numpy indexing."""

    def __init__(
        self,
        xyxy: np.ndarray,
        confidence: np.ndarray,
        class_id: np.ndarray,
        tracker_id: np.ndarray | None = None,
    ) -> None:
        self.xyxy = xyxy
        self.confidence = confidence
        self.class_id = class_id
        self.tracker_id = tracker_id

    def __len__(self) -> int:
        return len(self.xyxy)

    def __getitem__(self, mask):
        return _MockDetections(
            xyxy=self.xyxy[mask],
            confidence=self.confidence[mask],
            class_id=self.class_id[mask],
            tracker_id=self.tracker_id[mask] if self.tracker_id is not None else None,
        )


def _make_sv_detections(
    xyxy: list[list[float]],
    confs: list[float],
    class_ids: list[int],
    tracker_ids: list[int] | None = None,
) -> _MockDetections:
    """Create a mock sv.Detections object with tracker_id support."""
    return _MockDetections(
        xyxy=np.array(xyxy, dtype=np.float32)
        if xyxy
        else np.empty((0, 4), dtype=np.float32),
        confidence=np.array(confs, dtype=np.float32)
        if confs
        else np.empty(0, dtype=np.float32),
        class_id=np.array(class_ids, dtype=np.int32)
        if class_ids
        else np.empty(0, dtype=np.int32),
        tracker_id=np.array(tracker_ids, dtype=np.int32)
        if tracker_ids is not None
        else None,
    )


def _fake_video_capture(
    width: int = 640,
    height: int = 360,
    fps: float = 30.0,
    frame_count: int = 90,
) -> MagicMock:
    """Mock cv2.VideoCapture that returns black frames."""
    cap = MagicMock()
    cap.isOpened.return_value = True
    cap.get.side_effect = lambda prop: {
        3: width,  # CAP_PROP_FRAME_WIDTH
        4: height,  # CAP_PROP_FRAME_HEIGHT
        5: fps,  # CAP_PROP_FPS
        7: frame_count,  # CAP_PROP_FRAME_COUNT
    }.get(prop, 0)

    black_frame = np.zeros((height, width, 3), dtype=np.uint8)

    def read_side_effect():
        return True, black_frame.copy()

    cap.read.side_effect = read_side_effect
    return cap


# ---------------------------------------------------------------------------
# _select_ball_track
# ---------------------------------------------------------------------------


class TestSelectBallTrack:
    def test_picks_track_with_most_displacement(self) -> None:
        """The moving ball track should be selected over static tracks."""
        # Track 1: static object at (100, 100) across 5 frames
        # Track 2: moving ball from (200, 200) to (200, 400) across 5 frames
        tracked_frames = []
        for i in range(5):
            det = MagicMock()
            det.tracker_id = np.array([1, 2], dtype=np.int32)
            det.xyxy = np.array(
                [
                    [90, 90, 110, 110],  # track 1: static at ~(100, 100)
                    [190, 190 + i * 50, 210, 210 + i * 50],  # track 2: moving
                ],
                dtype=np.float32,
            )
            tracked_frames.append((i, i * 33.3, det))

        result = _select_ball_track(tracked_frames)
        assert result == 2

    def test_returns_none_when_no_tracks(self) -> None:
        """No tracker_id means no tracks to select."""
        tracked_frames = []
        for i in range(3):
            det = MagicMock()
            det.tracker_id = None
            det.xyxy = np.empty((0, 4), dtype=np.float32)
            tracked_frames.append((i, i * 33.3, det))

        result = _select_ball_track(tracked_frames)
        assert result is None

    def test_returns_none_for_empty_frames(self) -> None:
        assert _select_ball_track([]) is None

    def test_single_track_selected(self) -> None:
        """When only one track exists, it's selected regardless of displacement."""
        tracked_frames = []
        for i in range(3):
            det = MagicMock()
            det.tracker_id = np.array([5], dtype=np.int32)
            det.xyxy = np.array(
                [[100, 100 + i * 10, 120, 120 + i * 10]], dtype=np.float32
            )
            tracked_frames.append((i, i * 33.3, det))

        result = _select_ball_track(tracked_frames)
        assert result == 5

    def test_multiple_moving_tracks_picks_fastest(self) -> None:
        """With two moving tracks, pick the one with higher peak displacement."""
        tracked_frames = []
        for i in range(5):
            det = MagicMock()
            det.tracker_id = np.array([1, 2], dtype=np.int32)
            det.xyxy = np.array(
                [
                    [90, 90 + i * 20, 110, 110 + i * 20],  # track 1: slow mover
                    [190, 190 + i * 80, 210, 210 + i * 80],  # track 2: fast mover
                ],
                dtype=np.float32,
            )
            tracked_frames.append((i, i * 33.3, det))

        result = _select_ball_track(tracked_frames)
        assert result == 2

    def test_short_fast_track_beats_long_jittery_track(self) -> None:
        """A short ball toss (high mean displacement) beats a long-lived static
        object (low mean displacement but high total from jitter accumulation).
        This is the real-world scenario: background objects appear in 100+ frames
        with 1-2px jitter, while the toss arc is 20-30 frames at 30+ px/frame.
        """
        tracked_frames = []
        # Track 1: static object, 50 frames, ~1px jitter per frame
        for i in range(50):
            det = MagicMock()
            jitter = (i % 3) - 1  # -1, 0, 1 pattern
            det.tracker_id = np.array([1], dtype=np.int32)
            det.xyxy = np.array(
                [[100 + jitter, 200 + jitter, 120 + jitter, 220 + jitter]],
                dtype=np.float32,
            )
            tracked_frames.append((i, i * 33.3, det))

        # Track 2: ball toss, 15 frames, ~40px displacement per frame
        for i in range(15):
            det = MagicMock()
            det.tracker_id = np.array([2], dtype=np.int32)
            det.xyxy = np.array(
                [[190, 400 - i * 40, 210, 420 - i * 40]],  # moving upward fast
                dtype=np.float32,
            )
            tracked_frames.append((50 + i, (50 + i) * 33.3, det))

        result = _select_ball_track(tracked_frames)
        assert result == 2

    def test_ball_in_hand_then_toss_beats_jittery_track(self) -> None:
        """A track with 100 stationary frames (ball-in-hand) followed by 15 fast
        frames (toss arc) should still be selected over a jittery background track.
        This is the real-world scenario where ByteTrack gives ball-in-hand and
        toss arc the same track ID.
        """
        tracked_frames = []
        # Track 1: jittery background object, 80 frames, ~2px per frame
        for i in range(80):
            det = MagicMock()
            jitter = (i % 3) - 1
            det.tracker_id = np.array([1], dtype=np.int32)
            det.xyxy = np.array(
                [[100 + jitter, 200 + jitter, 120 + jitter, 220 + jitter]],
                dtype=np.float32,
            )
            tracked_frames.append((i, i * 33.3, det))

        # Track 2: ball-in-hand (stationary) for 100 frames, then toss arc for 15
        for i in range(100):
            det = MagicMock()
            det.tracker_id = np.array([2], dtype=np.int32)
            det.xyxy = np.array(
                [[300, 500, 320, 520]],  # stationary at hand level
                dtype=np.float32,
            )
            tracked_frames.append((i, i * 33.3, det))

        for i in range(15):
            det = MagicMock()
            det.tracker_id = np.array([2], dtype=np.int32)
            det.xyxy = np.array(
                [[300, 500 - i * 40, 320, 520 - i * 40]],  # toss arc moving upward
                dtype=np.float32,
            )
            tracked_frames.append((100 + i, (100 + i) * 33.3, det))

        result = _select_ball_track(tracked_frames)
        assert result == 2

    def test_returns_none_when_all_tracks_below_displacement_gate(self) -> None:
        """v39 serve 1 scenario: only a static track exists. Without the
        min-displacement gate, today's code returns this track by default
        (peak ≈ 1 px from sub-pixel jitter). With the gate, returns None."""
        tracked_frames = []
        for i in range(85):
            det = MagicMock()
            det.tracker_id = np.array([1], dtype=np.int32)
            jitter = ((i % 3) - 1) * 0.1  # sub-pixel only
            det.xyxy = np.array(
                [[24 + jitter, 556 + jitter, 40 + jitter, 572 + jitter]],
                dtype=np.float32,
            )
            tracked_frames.append((i, i * 33.3, det))

        result = _select_ball_track(tracked_frames)
        assert result is None

    def test_excluded_track_ids_are_skipped(self) -> None:
        """Tracks in `excluded_track_ids` are ignored during selection."""
        tracked_frames = []
        # Track 1: moving fast (would normally win)
        # Track 2: moving slowly
        for i in range(5):
            det = MagicMock()
            det.tracker_id = np.array([1, 2], dtype=np.int32)
            det.xyxy = np.array(
                [
                    [90, 90 + i * 80, 110, 110 + i * 80],  # fast (excluded)
                    [190, 190 + i * 20, 210, 210 + i * 20],  # slow (winner)
                ],
                dtype=np.float32,
            )
            tracked_frames.append((i, i * 33.3, det))

        result = _select_ball_track(tracked_frames, excluded_track_ids={1})
        assert result == 2


# ---------------------------------------------------------------------------
# _identify_static_distractors  — pooled cross-window distractor scan
# ---------------------------------------------------------------------------


class TestIdentifyStaticDistractors:
    @staticmethod
    def _static_track_frames(
        track_id: int, n_frames: int, *, x: float = 100.0, y: float = 200.0
    ) -> list[tuple]:
        """Build tracked_frames for a single static track with sub-pixel jitter."""
        out = []
        for i in range(n_frames):
            det = MagicMock()
            det.tracker_id = np.array([track_id], dtype=np.int32)
            jitter = ((i % 3) - 1) * 0.1
            det.xyxy = np.array(
                [
                    [
                        x - 8 + jitter,
                        y - 8 + jitter,
                        x + 8 + jitter,
                        y + 8 + jitter,
                    ]
                ],
                dtype=np.float32,
            )
            out.append((i, i * 33.3, det))
        return out

    @staticmethod
    def _moving_track_frames(
        track_id: int, n_frames: int, *, dx: float = 30.0, dy: float = 0.0
    ) -> list[tuple]:
        """Build tracked_frames for a single moving track."""
        out = []
        for i in range(n_frames):
            det = MagicMock()
            det.tracker_id = np.array([track_id], dtype=np.int32)
            cx = 100.0 + dx * i
            cy = 200.0 + dy * i
            det.xyxy = np.array([[cx - 8, cy - 8, cx + 8, cy + 8]], dtype=np.float32)
            out.append((i, i * 33.3, det))
        return out

    def test_flags_persistent_low_displacement_track(self) -> None:
        """A 50-frame static track should be flagged as a distractor."""
        window = self._static_track_frames(track_id=42, n_frames=50)
        distractors = _identify_static_distractors([window])
        assert distractors == [{42}]

    def test_does_not_flag_moving_track(self) -> None:
        """A track that moves significantly is not a distractor."""
        window = self._moving_track_frames(track_id=42, n_frames=30)
        distractors = _identify_static_distractors([window])
        assert distractors == [set()]

    def test_does_not_flag_short_static_track(self) -> None:
        """A static track that appears in too few pooled frames is not flagged."""
        window = self._static_track_frames(track_id=42, n_frames=5)
        distractors = _identify_static_distractors([window])
        assert distractors == [set()]

    def test_pools_evidence_across_windows(self) -> None:
        """A static ball seen across multiple windows at the same location is
        flagged even if no single window has enough frames alone."""
        w1 = self._static_track_frames(track_id=7, n_frames=15, x=200, y=500)
        w2 = self._static_track_frames(track_id=3, n_frames=15, x=200, y=500)
        distractors = _identify_static_distractors([w1, w2])
        assert distractors == [{7}, {3}]

    def test_does_not_pool_distant_tracks(self) -> None:
        """Tracks at different spatial locations are not pooled together."""
        w1 = self._static_track_frames(track_id=7, n_frames=15, x=200, y=500)
        w2 = self._static_track_frames(track_id=3, n_frames=15, x=500, y=200)
        distractors = _identify_static_distractors([w1, w2])
        assert distractors == [set(), set()]

    def test_empty_input_returns_empty_per_window(self) -> None:
        assert _identify_static_distractors([]) == []
        assert _identify_static_distractors([[]]) == [set()]


# ---------------------------------------------------------------------------
# Video-39 regression: full pipeline on frozen ByteTrack output
# ---------------------------------------------------------------------------


class TestV39Regression:
    """End-to-end check on frozen v39 data — confirms the static-distractor
    filter + min-displacement gate combine correctly to produce the right
    track ID for each serve window. See `v39_fixture.py` for diagnosis."""

    def test_static_balls_a_and_b_are_flagged_as_distractors(self) -> None:
        windows = v39_fixture.build_all_windows()
        distractors = _identify_static_distractors(windows)
        # Static ball A (track id 1) is present and flagged in every window
        assert 1 in distractors[0], "static A missing in serve1"
        assert 1 in distractors[1], "static A missing in serve2"
        assert 1 in distractors[2], "static A missing in serve3"
        assert 1 in distractors[3], "static A missing in serve4"
        # Static ball B (track id 20 in serve3, track id 2 in serve4) is
        # also flagged because pooled coverage exceeds the threshold.
        assert 20 in distractors[2], "static B missing in serve3"
        assert 2 in distractors[3], "static B missing in serve4"

    def test_serve1_returns_none(self) -> None:
        """Only a static ball + 1-frame fragments — no qualifying moving track."""
        windows = v39_fixture.build_all_windows()
        distractors = _identify_static_distractors(windows)
        result = _select_ball_track(windows[0], excluded_track_ids=distractors[0])
        assert result is None

    def test_serve2_returns_moving_track(self) -> None:
        windows = v39_fixture.build_all_windows()
        distractors = _identify_static_distractors(windows)
        result = _select_ball_track(windows[1], excluded_track_ids=distractors[1])
        assert result == 20  # 5-frame moving toss arc

    def test_serve3_returns_moving_track(self) -> None:
        windows = v39_fixture.build_all_windows()
        distractors = _identify_static_distractors(windows)
        result = _select_ball_track(windows[2], excluded_track_ids=distractors[2])
        assert result == 34  # 5-frame moving toss arc

    def test_serve4_returns_moving_track(self) -> None:
        windows = v39_fixture.build_all_windows()
        distractors = _identify_static_distractors(windows)
        result = _select_ball_track(windows[3], excluded_track_ids=distractors[3])
        assert result == 28  # 3-frame moving toss arc


# ---------------------------------------------------------------------------
# _rotate_frame
# ---------------------------------------------------------------------------


class TestRotateFrame:
    def test_no_rotation_returns_same_frame(self) -> None:
        frame = np.zeros((100, 200, 3), dtype=np.uint8)
        result = _rotate_frame(frame, 0)
        assert result.shape == frame.shape

    def test_90_cw_rotation(self) -> None:
        frame = np.zeros((100, 200, 3), dtype=np.uint8)
        result = _rotate_frame(frame, -90)
        assert result.shape == (200, 100, 3)

    def test_90_ccw_rotation(self) -> None:
        frame = np.zeros((100, 200, 3), dtype=np.uint8)
        result = _rotate_frame(frame, 90)
        assert result.shape == (200, 100, 3)

    def test_180_rotation(self) -> None:
        frame = np.zeros((100, 200, 3), dtype=np.uint8)
        result = _rotate_frame(frame, 180)
        assert result.shape == (100, 200, 3)


# ---------------------------------------------------------------------------
# YoloBallDetectionService.analyze_serve_windows -- with mocked model
# ---------------------------------------------------------------------------

_CAP_PATH = "app.services.ball_detection.yolo_detection_service.cv2.VideoCapture"
_ROT_PATH = "app.services.ball_detection.yolo_detection_service.get_video_rotation"
_SMOOTHER_PATH = (
    "app.services.ball_detection.yolo_detection_service.TrajectorySmoother.smooth"
)
_SV_PATH = "app.services.ball_detection.yolo_detection_service.sv"


class TestYoloBallDetectionService:
    def _build_service_with_mock_model(
        self, yolo_result: MagicMock
    ) -> YoloBallDetectionService:
        """Return a service whose model always returns [yolo_result]."""
        service = YoloBallDetectionService()
        mock_model = MagicMock()
        # YOLO model returns a list of Results, one per image
        mock_model.return_value = [yolo_result]
        mock_model.names = {0: "tennis-ball"}
        service._model = mock_model
        service._ball_class = 0
        return service

    def _make_mock_sv(
        self,
        tracked_detections: MagicMock | None = None,
    ) -> MagicMock:
        """Create a mock supervision module.

        Args:
            tracked_detections: If provided, ByteTrack.update_with_detections
                returns this for every frame. If None, returns a detection with
                no tracker_id.
        """
        mock_sv = MagicMock()

        if tracked_detections is None:
            # Default: return empty tracked detections
            default_tracked = MagicMock()
            default_tracked.tracker_id = None
            default_tracked.xyxy = np.empty((0, 4), dtype=np.float32)
            default_tracked.confidence = np.empty(0, dtype=np.float32)
            tracked_detections = default_tracked

        mock_tracker = MagicMock()
        mock_tracker.update_with_detections.return_value = tracked_detections
        mock_sv.ByteTrack.return_value = mock_tracker

        # from_ultralytics returns a Detections-like object that supports indexing
        def from_ultralytics_fn(result):
            boxes = result.boxes
            if boxes is None or len(boxes) == 0:
                return _make_sv_detections([], [], [])

            xyxy = boxes.xyxy.cpu().numpy()
            confs = boxes.conf.cpu().numpy()
            classes = boxes.cls.cpu().numpy().astype(np.int32)
            return _make_sv_detections(xyxy.tolist(), confs.tolist(), classes.tolist())

        mock_sv.Detections.from_ultralytics.side_effect = from_ultralytics_fn
        return mock_sv

    def test_output_dict_has_required_keys(self) -> None:
        yolo_result = _make_yolo_result(
            xyxy=[[100.0, 200.0, 120.0, 220.0]],
            confs=[0.9],
            classes=[0],
        )
        service = self._build_service_with_mock_model(yolo_result)
        fake_cap = _fake_video_capture(frame_count=30)

        # ByteTrack returns a tracked detection with a moving ball
        tracked = MagicMock()
        tracked.tracker_id = np.array([1], dtype=np.int32)
        tracked.xyxy = np.array([[100.0, 200.0, 120.0, 220.0]], dtype=np.float32)
        tracked.confidence = np.array([0.9], dtype=np.float32)
        mock_sv = self._make_mock_sv(tracked)

        with (
            patch(_CAP_PATH, return_value=fake_cap),
            patch(_ROT_PATH, return_value=0),
            patch(_SV_PATH, mock_sv),
        ):
            result = service.analyze_serve_windows(
                video_path=Path("/fake/video.mp4"),
                windows=[{"start_ms": 0, "end_ms": 500}],
            )

        required_keys = {
            "ball_detections",
            "total_frames",
            "frames_with_ball",
            "detection_rate",
            "processing_time_seconds",
            "frame_processing_rate",
            "status",
            "video_path",
        }
        assert required_keys.issubset(result.keys())
        assert result["status"] == "completed"

    def test_per_frame_dict_has_interpolated_key(self) -> None:
        yolo_result = _make_yolo_result(
            xyxy=[[100.0, 200.0, 120.0, 220.0]],
            confs=[0.9],
            classes=[0],
        )
        service = self._build_service_with_mock_model(yolo_result)
        fake_cap = _fake_video_capture(frame_count=10)
        mock_sv = self._make_mock_sv()

        with (
            patch(_CAP_PATH, return_value=fake_cap),
            patch(_ROT_PATH, return_value=0),
            patch(_SV_PATH, mock_sv),
        ):
            result = service.analyze_serve_windows(
                video_path=Path("/fake/video.mp4"),
                windows=[{"start_ms": 0, "end_ms": 300}],
            )

        for det in result["ball_detections"]:
            assert "interpolated" in det, (
                "Every frame dict must have 'interpolated' key"
            )

    def test_frames_below_threshold_have_none_position(self) -> None:
        """When YOLO confidence < threshold, ball_x/y should be None."""
        yolo_result = _make_yolo_result(
            xyxy=[[100.0, 200.0, 120.0, 220.0]],
            confs=[0.1],  # Below DEFAULT_CONFIDENCE of 0.25
            classes=[0],
        )
        service = self._build_service_with_mock_model(yolo_result)
        fake_cap = _fake_video_capture(frame_count=5)
        mock_sv = self._make_mock_sv()  # No tracked detections (below threshold)

        with (
            patch(_CAP_PATH, return_value=fake_cap),
            patch(_ROT_PATH, return_value=0),
            patch(_SV_PATH, mock_sv),
        ):
            result = service.analyze_serve_windows(
                video_path=Path("/fake/video.mp4"),
                windows=[{"start_ms": 0, "end_ms": 160}],
                confidence=DEFAULT_CONFIDENCE,
            )

        for det in result["ball_detections"]:
            assert det["ball_x"] is None
            assert det["ball_y"] is None

    def test_rotation_applied_to_frames(self) -> None:
        """Rotation != 0 should trigger frame rotation without errors."""
        yolo_result = _make_yolo_result(
            xyxy=[[100.0, 200.0, 120.0, 220.0]],
            confs=[0.9],
            classes=[0],
        )
        service = self._build_service_with_mock_model(yolo_result)
        fake_cap = _fake_video_capture(width=360, height=640, frame_count=10)
        mock_sv = self._make_mock_sv()

        with (
            patch(_CAP_PATH, return_value=fake_cap),
            patch(_ROT_PATH, return_value=-90),
            patch(_SV_PATH, mock_sv),
        ):
            result = service.analyze_serve_windows(
                video_path=Path("/fake/video.mp4"),
                windows=[{"start_ms": 0, "end_ms": 300}],
            )

        assert result["status"] == "completed"

    def test_detection_rate_computed_correctly(self) -> None:
        """detection_rate = frames_with_ball / total_frames."""
        yolo_result = _make_yolo_result(
            xyxy=[[100.0, 200.0, 120.0, 220.0]],
            confs=[0.9],
            classes=[0],
        )
        service = self._build_service_with_mock_model(yolo_result)
        fake_cap = _fake_video_capture(frame_count=30)

        tracked = MagicMock()
        tracked.tracker_id = np.array([1], dtype=np.int32)
        tracked.xyxy = np.array([[100.0, 200.0, 120.0, 220.0]], dtype=np.float32)
        tracked.confidence = np.array([0.9], dtype=np.float32)
        mock_sv = self._make_mock_sv(tracked)

        # Disable smoother so we can reason about raw counts
        with (
            patch(_CAP_PATH, return_value=fake_cap),
            patch(_ROT_PATH, return_value=0),
            patch(_SV_PATH, mock_sv),
            patch(_SMOOTHER_PATH, side_effect=lambda dets: dets),
        ):
            result = service.analyze_serve_windows(
                video_path=Path("/fake/video.mp4"),
                windows=[{"start_ms": 0, "end_ms": 200}],
            )

        total = result["total_frames"]
        with_ball = result["frames_with_ball"]
        if total > 0:
            assert abs(result["detection_rate"] - with_ball / total) < 1e-6

    def test_error_result_on_file_not_found(self) -> None:
        """Service returns an error dict when the model file does not exist."""
        service = YoloBallDetectionService()

        with patch(
            "app.services.ball_detection.yolo_detection_service.settings"
        ) as mock_settings:
            mock_settings.ML_MODELS_DIR = "/nonexistent"
            result = service.analyze_serve_windows(
                video_path=Path("/fake/video.mp4"),
                windows=[{"start_ms": 0, "end_ms": 500}],
            )

        assert result["status"] == "failed"
        assert "error" in result
        assert result["ball_detections"] == []

    def test_no_detections_gives_none_values(self) -> None:
        """When YOLO finds no boxes at all, ball_x/y should be None."""
        yolo_result = _make_empty_yolo_result()
        service = self._build_service_with_mock_model(yolo_result)
        fake_cap = _fake_video_capture(frame_count=5)
        mock_sv = self._make_mock_sv()

        with (
            patch(_CAP_PATH, return_value=fake_cap),
            patch(_ROT_PATH, return_value=0),
            patch(_SV_PATH, mock_sv),
            patch(_SMOOTHER_PATH, side_effect=lambda dets: dets),
        ):
            result = service.analyze_serve_windows(
                video_path=Path("/fake/video.mp4"),
                windows=[{"start_ms": 0, "end_ms": 160}],
            )

        assert result["frames_with_ball"] == 0
        for det in result["ball_detections"]:
            assert det["ball_x"] is None
            assert det["ball_y"] is None
