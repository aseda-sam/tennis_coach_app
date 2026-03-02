"""Unit tests for frame extraction service — cropping logic."""

import numpy as np

from app.services.frame_extraction_service import _crop_to_pose


class TestCropToPose:
    """Tests for _crop_to_pose bounding-box crop."""

    def _make_frame(self, h: int = 720, w: int = 1280) -> np.ndarray:
        return np.zeros((h, w, 3), dtype=np.uint8)

    def test_crops_to_keypoints_with_padding(self):
        frame = self._make_frame(720, 1280)
        keypoints = {
            "left_shoulder": [400, 200],
            "right_shoulder": [600, 200],
            "left_hip": [400, 400],
            "right_hip": [600, 400],
        }
        cropped = _crop_to_pose(frame, keypoints, 720, 1280)
        # Cropped should be smaller than the full frame
        assert cropped.shape[0] < 720
        assert cropped.shape[1] < 1280
        # Should include the keypoints plus padding
        assert cropped.shape[0] > 200  # box_h=200, plus top/bottom padding
        assert cropped.shape[1] > 200  # box_w=200, plus side padding

    def test_returns_full_frame_if_too_few_keypoints(self):
        frame = self._make_frame(720, 1280)
        keypoints = {"left_shoulder": [400, 200]}
        result = _crop_to_pose(frame, keypoints, 720, 1280)
        assert result.shape == (720, 1280, 3)

    def test_returns_full_frame_if_keypoints_empty(self):
        frame = self._make_frame(720, 1280)
        result = _crop_to_pose(frame, {}, 720, 1280)
        assert result.shape == (720, 1280, 3)

    def test_skips_zero_zero_keypoints(self):
        frame = self._make_frame(720, 1280)
        keypoints = {
            "left_shoulder": [0, 0],  # invalid, should skip
            "right_shoulder": [600, 200],
            "left_hip": [500, 400],
        }
        cropped = _crop_to_pose(frame, keypoints, 720, 1280)
        # Should still crop (2 valid points)
        assert cropped.shape[0] < 720

    def test_clamps_to_frame_bounds(self):
        frame = self._make_frame(720, 1280)
        # Keypoints near edges
        keypoints = {
            "left_shoulder": [10, 10],
            "right_shoulder": [1270, 10],
            "left_hip": [10, 710],
            "right_hip": [1270, 710],
        }
        cropped = _crop_to_pose(frame, keypoints, 720, 1280)
        # Should not exceed frame bounds
        assert cropped.shape[0] <= 720
        assert cropped.shape[1] <= 1280

    def test_generous_top_padding_for_racket(self):
        frame = self._make_frame(720, 1280)
        keypoints = {
            "left_shoulder": [400, 300],
            "right_shoulder": [600, 300],
            "left_hip": [400, 500],
            "right_hip": [600, 500],
        }
        cropped = _crop_to_pose(frame, keypoints, 720, 1280)
        # Top padding should be generous (50% of box_h = 100px above min_y=300)
        # So crop_y1 = max(0, 300 - 100) = 200
        # Bottom padding = 15% of box_h = 30px below max_y=500 → crop_y2 = 530
        # Total height ≈ 330
        assert cropped.shape[0] >= 300  # generous enough for racket
