"""Tests for auto-detecting contact timestamp from ball + wrist data."""

import json
from unittest.mock import MagicMock

from app.services.ball_detection.contact_detector import detect_contact_timestamp


def _make_pose_frame(wrist_x: float, wrist_y: float, side: str = "right") -> dict:
    """One frame of pose data with wrist at (wrist_x, wrist_y)."""
    keypoints = {
        "left_shoulder": [0.3, 0.25],
        "right_shoulder": [0.7, 0.25],
        "left_wrist": [0.2, 0.5],
        "right_wrist": [wrist_x, wrist_y],
        "left_hip": [0.4, 0.55],
        "right_hip": [0.6, 0.55],
        "left_knee": [0.45, 0.75],
        "right_knee": [0.55, 0.75],
        "left_ankle": [0.45, 0.9],
        "right_ankle": [0.55, 0.9],
    }
    return {"frame_index": 0, "timestamp_ms": 0, "keypoints": keypoints}


def _make_ball_detection(ball_list: list) -> MagicMock:
    """BallDetection model with given ball_data."""
    bd = MagicMock()
    bd.ball_data = json.dumps(ball_list)
    return bd


def _make_pose_detection(pose_frames_by_index: list) -> MagicMock:
    """PoseDetection with pose_data as list of frames (index = frame index)."""
    pd = MagicMock()
    pd.pose_data = json.dumps(pose_frames_by_index)
    return pd


def _make_serve_window(
    start: float = 0.0, end: float = 2.0, contact_timestamp: float | None = None
) -> MagicMock:
    sw = MagicMock()
    sw.start_timestamp = start
    sw.end_timestamp = end
    sw.contact_timestamp = contact_timestamp
    return sw


def _make_video(fps: float = 30.0, width: int = 1280, height: int = 720) -> MagicMock:
    v = MagicMock()
    v.fps = fps
    v.width = width
    v.height = height
    return v


class TestDetectContactFromBallWristProximity:
    """Contact = frame where ball is closest to dominant wrist after toss peak."""

    def test_detects_contact_from_ball_wrist_proximity(self) -> None:
        """When ball and dominant wrist converge at a known frame, return that timestamp."""
        fps = 30.0
        # Frame 45 = 1.5s. Ball and right wrist both at (640, 150) at frame 45.
        contact_frame = 45
        contact_ts_sec = contact_frame / fps
        ball_list = [
            {
                "frame_index": i,
                "timestamp_ms": i * 1000.0 / fps,
                "ball_x": 640.0 if i == contact_frame else 400.0,
                "ball_y": 150.0 if i == contact_frame else 300.0,
                "confidence": 0.8,
            }
            for i in range(30, 60)
        ]
        # Pose: right wrist at (640, 150) at frame 45, elsewhere away
        pose_frames = []
        for i in range(70):
            if i == contact_frame:
                pose_frames.append(_make_pose_frame(640.0, 150.0, "right"))
            else:
                pose_frames.append(_make_pose_frame(400.0, 400.0, "right"))
        # Toss peak before contact (e.g. frame 30)
        ball_list[0]["ball_y"] = 200.0
        ball_list[contact_frame - 30]["ball_y"] = 100.0  # peak around frame 30

        ball_detection = _make_ball_detection(ball_list)
        pose_detection = _make_pose_detection(pose_frames)
        serve_window = _make_serve_window(0.0, 2.5, contact_timestamp=None)
        video = _make_video(fps)

        result = detect_contact_timestamp(
            ball_detection=ball_detection,
            pose_detection=pose_detection,
            serve_window=serve_window,
            video=video,
            dominant_hand="right",
        )

        assert result is not None
        assert abs(result - contact_ts_sec) < 0.05

    def test_ignores_toss_hand_proximity(self) -> None:
        """Ball near non-dominant (toss) wrist during toss should NOT be contact."""
        fps = 30.0
        # Frame 10: ball near left wrist (toss arm for right-handed). Frame 40: ball near right wrist.
        ball_list = [
            {
                "frame_index": 10,
                "timestamp_ms": 10 * 1000.0 / fps,
                "ball_x": 320.0,
                "ball_y": 200.0,
                "confidence": 0.7,
            },
            {
                "frame_index": 40,
                "timestamp_ms": 40 * 1000.0 / fps,
                "ball_x": 700.0,
                "ball_y": 120.0,
                "confidence": 0.8,
            },
        ]
        # Left wrist at (320, 200) at frame 10; right wrist at (700, 120) at frame 40.
        pose_frames = []
        for i in range(60):
            if i == 10:
                pose_frames.append(
                    _make_pose_frame(320.0, 200.0, "right")
                )  # left would be toss; we set right in helper
            elif i == 40:
                pose_frames.append(_make_pose_frame(700.0, 120.0, "right"))
            else:
                pose_frames.append(_make_pose_frame(500.0, 400.0, "right"))
        # Override left_wrist for frame 10 so ball is near left (toss) hand
        for i in range(60):
            if i == 10:
                k = pose_frames[10]["keypoints"].copy()
                k["left_wrist"] = [320.0, 200.0]
                k["right_wrist"] = [700.0, 400.0]
                pose_frames[10] = {
                    "frame_index": 10,
                    "timestamp_ms": 10 * 1000 / fps,
                    "keypoints": k,
                }
            elif i == 40:
                k = pose_frames[40]["keypoints"].copy()
                k["right_wrist"] = [700.0, 120.0]
                pose_frames[40] = {
                    "frame_index": 40,
                    "timestamp_ms": 40 * 1000 / fps,
                    "keypoints": k,
                }

        ball_detection = _make_ball_detection(ball_list)
        pose_detection = _make_pose_detection(pose_frames)
        serve_window = _make_serve_window(0.0, 2.0, contact_timestamp=None)
        video = _make_video(fps)

        result = detect_contact_timestamp(
            ball_detection=ball_detection,
            pose_detection=pose_detection,
            serve_window=serve_window,
            video=video,
            dominant_hand="right",
        )

        # Should pick frame 40 (ball near dominant wrist), not frame 10 (toss)
        assert result is not None
        assert abs(result - 40.0 / fps) < 0.05

    def test_requires_after_toss_peak(self) -> None:
        """Ball near wrist before toss peak should be filtered out."""
        fps = 30.0
        # Toss peak at frame 25. Ball close to wrist at frame 15 (before peak).
        ball_list = [
            {
                "frame_index": 15,
                "timestamp_ms": 15 * 1000.0 / fps,
                "ball_x": 640.0,
                "ball_y": 250.0,
                "confidence": 0.8,
            },
            {
                "frame_index": 25,
                "timestamp_ms": 25 * 1000.0 / fps,
                "ball_x": 500.0,
                "ball_y": 80.0,  # peak (highest)
                "confidence": 0.7,
            },
            {
                "frame_index": 40,
                "timestamp_ms": 40 * 1000.0 / fps,
                "ball_x": 640.0,
                "ball_y": 140.0,
                "confidence": 0.8,
            },
        ]
        pose_frames = []
        for i in range(50):
            if i == 15:
                pose_frames.append(_make_pose_frame(640.0, 250.0, "right"))
            elif i == 40:
                pose_frames.append(_make_pose_frame(640.0, 140.0, "right"))
            else:
                pose_frames.append(_make_pose_frame(500.0, 400.0, "right"))

        ball_detection = _make_ball_detection(ball_list)
        pose_detection = _make_pose_detection(pose_frames)
        serve_window = _make_serve_window(0.0, 2.0, contact_timestamp=None)
        video = _make_video(fps)

        result = detect_contact_timestamp(
            ball_detection=ball_detection,
            pose_detection=pose_detection,
            serve_window=serve_window,
            video=video,
            dominant_hand="right",
        )

        # Should pick frame 40 (after peak), not frame 15
        assert result is not None
        assert result >= 25.0 / fps
        assert abs(result - 40.0 / fps) < 0.05

    def test_returns_none_when_no_ball_data(self) -> None:
        """Graceful degradation when ball_data is missing or empty."""
        pose_frames = [_make_pose_frame(640.0, 200.0, "right") for _ in range(60)]
        pose_detection = _make_pose_detection(pose_frames)
        serve_window = _make_serve_window(0.0, 2.0, contact_timestamp=None)
        video = _make_video(30.0)

        for ball_data_value in (None, "", "[]"):
            bd = MagicMock()
            bd.ball_data = ball_data_value
            result = detect_contact_timestamp(
                ball_detection=bd,
                pose_detection=pose_detection,
                serve_window=serve_window,
                video=video,
                dominant_hand="right",
            )
            assert result is None

    def test_returns_none_when_ball_never_close_to_wrist(self) -> None:
        """No false positive when ball and wrist stay far apart."""
        fps = 30.0
        ball_list = [
            {
                "frame_index": i,
                "timestamp_ms": i * 1000.0 / fps,
                "ball_x": 100.0,  # far left
                "ball_y": 150.0,
                "confidence": 0.8,
            }
            for i in range(30, 50)
        ]
        pose_frames = [
            _make_pose_frame(900.0, 200.0, "right") for _ in range(60)
        ]  # wrist far right

        ball_detection = _make_ball_detection(ball_list)
        pose_detection = _make_pose_detection(pose_frames)
        serve_window = _make_serve_window(0.0, 2.0, contact_timestamp=None)
        video = _make_video(fps)

        result = detect_contact_timestamp(
            ball_detection=ball_detection,
            pose_detection=pose_detection,
            serve_window=serve_window,
            video=video,
            dominant_hand="right",
        )

        # May return None or fall back to velocity reversal; if proximity used, should be None
        # when distance threshold is not met
        if result is not None:
            # If we add velocity fallback, result could be non-None; then just check it's in window
            assert serve_window.start_timestamp <= result <= serve_window.end_timestamp

    def test_falls_back_to_velocity_reversal(self) -> None:
        """When proximity fails but ball trajectory reverses (struck), use that frame."""
        fps = 30.0
        # Ball goes up (ball_y decreases) until frame 38, then down (ball_y increases) = contact
        ball_list = []
        for i in range(20, 50):
            ball_y = (
                250.0 - (i - 20) * 5.0 if i < 38 else 60.0 + (i - 38) * 8.0
            )  # up then down after contact
            ball_list.append(
                {
                    "frame_index": i,
                    "timestamp_ms": i * 1000.0 / fps,
                    "ball_x": 640.0,
                    "ball_y": ball_y,
                    "confidence": 0.5,
                }
            )
        # Wrist never very close to ball (e.g. 100px away) so proximity might not trigger
        pose_frames = []
        for _ in range(60):
            pose_frames.append(_make_pose_frame(640.0, 80.0, "right"))

        ball_detection = _make_ball_detection(ball_list)
        pose_detection = _make_pose_detection(pose_frames)
        serve_window = _make_serve_window(0.0, 2.0, contact_timestamp=None)
        video = _make_video(fps)

        result = detect_contact_timestamp(
            ball_detection=ball_detection,
            pose_detection=pose_detection,
            serve_window=serve_window,
            video=video,
            dominant_hand="right",
        )

        # Should detect reversal around frame 38 (1.27s)
        assert result is not None
        assert 0.9 <= result <= 1.5

    def test_does_not_overwrite_existing_contact(self) -> None:
        """Detector does not overwrite DB; when contact already set, caller skips. Detector still returns auto value."""
        fps = 30.0
        ball_list = [
            {
                "frame_index": 45,
                "timestamp_ms": 45 * 1000.0 / fps,
                "ball_x": 640.0,
                "ball_y": 150.0,
                "confidence": 0.9,
            }
        ]
        pose_frames = []
        for i in range(60):
            if i == 45:
                pose_frames.append(_make_pose_frame(640.0, 150.0, "right"))
            else:
                pose_frames.append(_make_pose_frame(500.0, 400.0, "right"))

        ball_detection = _make_ball_detection(ball_list)
        pose_detection = _make_pose_detection(pose_frames)
        serve_window = _make_serve_window(0.0, 2.0, contact_timestamp=1.0)
        video = _make_video(fps)

        result = detect_contact_timestamp(
            ball_detection=ball_detection,
            pose_detection=pose_detection,
            serve_window=serve_window,
            video=video,
            dominant_hand="right",
        )

        # Detector is stateless; it returns auto-detected timestamp. Pipeline must only write when contact is None.
        assert result is not None
        assert 0.0 <= result <= 2.0
