"""Frame extraction service — extract KTP frames from videos as JPEG bytes."""

import json
import logging
from pathlib import Path

import cv2
from sqlalchemy.orm import Session

from app.models.serve_biomechanics_report import ServeBiomechanicsReport
from app.models.serve_window import ServeWindow
from app.models.video import Video
from app.services.storage_service import storage_service

logger = logging.getLogger(__name__)


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
