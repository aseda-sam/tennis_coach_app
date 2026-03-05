"""Frame extraction service — extract KTP frames from videos as JPEG bytes."""

import json
import logging
from pathlib import Path
from typing import Dict

import cv2
import numpy as np
from sqlalchemy.orm import Session

from app.models.serve_biomechanics_report import ServeBiomechanicsReport
from app.models.serve_window import ServeWindow
from app.models.video import Video
from app.services.pose_data_service import (
    _select_best_pose_detection,
    get_pose_at_timestamp,
)
from app.services.storage_service import storage_service

logger = logging.getLogger(__name__)

# Padding ratios for pose-based crop
_PAD_TOP = 0.50  # Extra above highest keypoint (racket headroom)
_PAD_BOTTOM = 0.15  # Below lowest keypoint
_PAD_SIDES = 0.30  # Left/right of bounding box


def _crop_frame_to_pose(
    db: Session,
    video: Video,
    serve_window: ServeWindow,
    fps: float,
    ktp_frame: int,
    frame: np.ndarray,
) -> np.ndarray:
    """Look up pose keypoints for the KTP frame and crop to the player.

    Returns the original frame unchanged if pose data is unavailable.
    """
    try:
        pose_detection = _select_best_pose_detection(db, video.id)
        if not pose_detection:
            return frame

        # Compute absolute timestamp for the KTP frame
        ktp_timestamp = serve_window.start_timestamp + (ktp_frame / fps)

        keypoints = get_pose_at_timestamp(pose_detection, video, ktp_timestamp)
        if not keypoints:
            return frame

        h, w = frame.shape[:2]
        return _crop_to_pose(frame, keypoints, h, w)
    except Exception:  # noqa: BLE001
        logger.debug(
            "Pose crop failed for serve window %s, returning full frame",
            serve_window.id,
            exc_info=True,
        )
        return frame


def _crop_to_pose(
    frame: np.ndarray,
    keypoints: Dict,
    frame_height: int,
    frame_width: int,
) -> np.ndarray:
    """Crop frame to pose bounding box with padding.

    Computes a bounding box from all visible keypoints, adds generous padding
    (especially above the top to keep the racket in frame), and returns the
    cropped region.  Always returns a non-empty image.
    """
    xs = []
    ys = []
    for _name, coords in keypoints.items():
        if isinstance(coords, (list, tuple)) and len(coords) >= 2:
            x, y = float(coords[0]), float(coords[1])
            # Skip clearly invalid points (0,0 or out-of-frame)
            if x <= 0 and y <= 0:
                continue
            xs.append(x)
            ys.append(y)

    if len(xs) < 2:
        # Not enough landmarks — return full frame
        return frame

    min_x, max_x = min(xs), max(xs)
    min_y, max_y = min(ys), max(ys)

    box_w = max_x - min_x
    box_h = max_y - min_y

    # Apply padding
    pad_top = box_h * _PAD_TOP
    pad_bottom = box_h * _PAD_BOTTOM
    pad_side = box_w * _PAD_SIDES

    crop_x1 = int(max(0, min_x - pad_side))
    crop_y1 = int(max(0, min_y - pad_top))
    crop_x2 = int(min(frame_width, max_x + pad_side))
    crop_y2 = int(min(frame_height, max_y + pad_bottom))

    # Sanity check: crop must be at least 50x50
    if (crop_x2 - crop_x1) < 50 or (crop_y2 - crop_y1) < 50:
        return frame

    return frame[crop_y1:crop_y2, crop_x1:crop_x2]


def extract_frame_at_timestamp(
    db: Session, serve_window_id: int, timestamp: float
) -> bytes:
    """Extract a JPEG frame at an absolute video timestamp from a serve window's video.

    Args:
        db: Database session.
        serve_window_id: ID of the serve window.
        timestamp: Absolute timestamp in seconds (within the serve window).

    Returns:
        JPEG image bytes (cropped to pose bounding box).

    Raises:
        ValueError: If serve window, video, or frame is missing/unreadable.
    """
    serve_window = (
        db.query(ServeWindow).filter(ServeWindow.id == serve_window_id).first()
    )
    if not serve_window:
        raise ValueError(f"Serve window {serve_window_id} not found")

    video = serve_window.video
    if not video:
        video = db.query(Video).filter(Video.id == serve_window.video_id).first()
    if not video:
        raise ValueError(f"Video {serve_window.video_id} not found")

    fps = video.fps or 30.0
    absolute_frame = int(timestamp * fps)

    # Relative frame within serve window (for pose crop)
    relative_frame = int((timestamp - serve_window.start_timestamp) * fps)

    temp_path = None
    try:
        local_path = storage_service.get_local_file_path(video.file_path)
        if storage_service.storage_type == "supabase":
            temp_path = local_path

        cap = cv2.VideoCapture(str(local_path))
        cap.set(cv2.CAP_PROP_POS_FRAMES, absolute_frame)
        ret, frame = cap.read()
        cap.release()

        if not ret or frame is None:
            raise ValueError(
                f"Could not read frame {absolute_frame} from video {video.id}"
            )

        frame = _crop_frame_to_pose(db, video, serve_window, fps, relative_frame, frame)

        success, buffer = cv2.imencode(".jpg", frame, [cv2.IMWRITE_JPEG_QUALITY, 85])
        if not success:
            raise ValueError(f"Failed to encode frame as JPEG for video {video.id}")

        return buffer.tobytes()
    finally:
        if temp_path and Path(temp_path).exists():
            try:
                Path(temp_path).unlink()
            except OSError:
                logger.warning("Failed to clean up temp file: %s", temp_path)


def extract_ktp_frame(db: Session, serve_window_id: int, ktp_name: str) -> bytes:
    """Extract a single JPEG frame for a Key Time Point from a serve window's video.

    Looks up the latest biomechanics report, finds the KTP frame index,
    calculates the absolute frame in the video, and returns JPEG bytes.

    Args:
        db: Database session.
        serve_window_id: ID of the serve window.
        ktp_name: KTP name (e.g. "trophy_position").

    Returns:
        JPEG image bytes.

    Raises:
        ValueError: If serve window, report, KTP, or video frame is missing/unreadable.
    """
    # Look up latest report for this serve window
    report = (
        db.query(ServeBiomechanicsReport)
        .filter(ServeBiomechanicsReport.serve_window_id == serve_window_id)
        .order_by(ServeBiomechanicsReport.created_at.desc())
        .first()
    )
    if not report:
        raise ValueError(f"No biomechanics report for serve window {serve_window_id}")

    # Parse phase_segmentation_json to find KTP
    seg_data = {}
    if report.phase_segmentation_json:
        seg_data = json.loads(report.phase_segmentation_json)

    meta = seg_data.get("detection_meta", {})
    ktp_info = meta.get("ktps", {}).get(ktp_name)
    if not ktp_info or ktp_info.get("frame") is None:
        raise ValueError(
            f"KTP '{ktp_name}' not found in report for serve window {serve_window_id}"
        )

    ktp_frame = ktp_info["frame"]

    # Get serve window and video via ORM relationships
    serve_window = report.serve_window
    if not serve_window:
        serve_window = (
            db.query(ServeWindow).filter(ServeWindow.id == serve_window_id).first()
        )
    if not serve_window:
        raise ValueError(f"Serve window {serve_window_id} not found")

    video = serve_window.video
    if not video:
        video = db.query(Video).filter(Video.id == serve_window.video_id).first()
    if not video:
        raise ValueError(f"Video {serve_window.video_id} not found")

    # Calculate absolute frame
    fps = meta.get("fps") or video.fps or 30.0
    start_frame = int(serve_window.start_timestamp * fps)
    absolute_frame = start_frame + ktp_frame

    # Get local file path and extract frame
    temp_path = None
    try:
        local_path = storage_service.get_local_file_path(video.file_path)
        # Track whether this is a temp file (cloud storage)
        if storage_service.storage_type == "supabase":
            temp_path = local_path

        cap = cv2.VideoCapture(str(local_path))
        cap.set(cv2.CAP_PROP_POS_FRAMES, absolute_frame)
        ret, frame = cap.read()
        cap.release()

        if not ret or frame is None:
            raise ValueError(
                f"Could not read frame {absolute_frame} from video {video.id}"
            )

        # Crop to pose bounding box (graceful fallback to full frame)
        frame = _crop_frame_to_pose(db, video, serve_window, fps, ktp_frame, frame)

        # Encode as JPEG
        success, buffer = cv2.imencode(".jpg", frame, [cv2.IMWRITE_JPEG_QUALITY, 85])
        if not success:
            raise ValueError(f"Failed to encode frame as JPEG for video {video.id}")

        return buffer.tobytes()
    finally:
        # Clean up temp file from cloud storage download
        if temp_path and Path(temp_path).exists():
            try:
                Path(temp_path).unlink()
            except OSError:
                logger.warning("Failed to clean up temp file: %s", temp_path)
