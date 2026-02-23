"""Standalone ball tracking annotation script for visual verification.

Runs YOLO + ByteTrack on a video and writes an annotated MP4 showing
bounding boxes and track IDs on all detected tennis balls.

Usage:
    # Inside the worker container:
    docker compose exec worker python backend/scripts/annotate_ball_tracking.py \
        --video data/videos/raw/sinner_slm_serve.mp4 \
        --out /tmp/annotated_serve.mp4

    # With trajectory trails per track:
    docker compose exec worker python backend/scripts/annotate_ball_tracking.py \
        --video data/videos/raw/sinner_slm_serve.mp4 \
        --trail 15

Options:
    --video     Path to input video (required)
    --out       Output path (default: <input>_annotated.mp4)
    --model     Model weights path (default: ml_models/yolo_tennis_ball.pt)
    --start     Start time in seconds (default: 0 = beginning)
    --end       End time in seconds (default: None = full video)
    --conf      Confidence threshold (default: 0.5)
    --trail     Trail length per track (default: 0 = no trails)
"""

from __future__ import annotations

import argparse
import sys
import time
from pathlib import Path

# Ensure backend app is importable
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import cv2
import numpy as np

from app.utils.video_utils import get_video_rotation


def _rotate_frame(frame: np.ndarray, rotation: int) -> np.ndarray:
    if rotation in (-90, 270):
        return cv2.rotate(frame, cv2.ROTATE_90_CLOCKWISE)
    if rotation in (90, -270):
        return cv2.rotate(frame, cv2.ROTATE_90_COUNTERCLOCKWISE)
    if rotation in (180, -180):
        return cv2.rotate(frame, cv2.ROTATE_180)
    return frame


# ------------------------------------------------------------------
# Main annotate entry point
# ------------------------------------------------------------------


def annotate(
    video_path: Path,
    out_path: Path,
    model_path: Path,
    start_sec: float = 0.0,
    end_sec: float | None = None,
    confidence: float = 0.5,
    trail_length: int = 0,
) -> None:
    """Main entry point: detect balls and write annotated video."""
    t0 = time.time()

    from ultralytics import YOLO

    print(f"Loading YOLO from {model_path}...")
    model = YOLO(str(model_path))
    print(f"Model ready ({time.time() - t0:.1f}s)")

    # --- Read video metadata ---
    cap = cv2.VideoCapture(str(video_path))
    if not cap.isOpened():
        print(f"ERROR: cannot open {video_path}")
        return

    fps = cap.get(cv2.CAP_PROP_FPS) or 30.0
    total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
    rotation = get_video_rotation(video_path)
    cap.release()

    start_frame = max(0, int(start_sec * fps))
    end_frame = min(
        total_frames - 1,
        int(end_sec * fps) if end_sec is not None else total_frames - 1,
    )
    n_frames = end_frame - start_frame + 1
    print(
        f"Video: {video_path.name}  fps={fps:.1f}  frames {start_frame}-{end_frame} ({n_frames} frames)  rotation={rotation}"
    )

    # --- Read all frames ---
    print("Reading frames...")
    cap = cv2.VideoCapture(str(video_path))
    cap.set(cv2.CAP_PROP_ORIENTATION_AUTO, 0)
    cap.set(cv2.CAP_PROP_POS_FRAMES, start_frame)

    raw_frames: list[np.ndarray] = []
    idx = start_frame
    while idx <= end_frame:
        ret, frame = cap.read()
        if not ret:
            break
        if rotation != 0:
            frame = _rotate_frame(frame, rotation)
        raw_frames.append(frame)
        idx += 1
    cap.release()

    if not raw_frames:
        print("ERROR: no frames read")
        return

    orig_h, orig_w = raw_frames[0].shape[:2]
    print(f"Read {len(raw_frames)} frames ({orig_w}x{orig_h})")

    # --- YOLO + ByteTrack + supervision annotators ---
    import supervision as sv

    model_names = getattr(model, "names", {})
    ball_class = 0 if len(model_names) <= 10 else 32

    tracker = sv.ByteTrack()
    box_annotator = sv.BoxAnnotator()
    label_annotator = sv.LabelAnnotator()

    out_path.parent.mkdir(parents=True, exist_ok=True)
    fourcc = cv2.VideoWriter_fourcc(*"mp4v")
    writer = cv2.VideoWriter(str(out_path), fourcc, fps, (orig_w, orig_h))

    # Per-track trail positions: {track_id: deque of (cx, cy)}
    trail_positions: dict[int, list[tuple[int, int]]] = {}

    # Colour palette for trails (BGR)
    trail_palette = [
        (0, 255, 255),  # yellow
        (255, 0, 255),  # magenta
        (0, 200, 255),  # amber
        (255, 200, 0),  # cyan-ish
        (0, 255, 0),  # green
        (255, 100, 100),  # light blue
        (100, 100, 255),  # salmon
        (200, 200, 0),  # teal
    ]

    print("Running YOLO + ByteTrack inference and annotating...")
    t1 = time.time()
    frames_with_ball = 0

    for i, frame in enumerate(raw_frames):
        result = model(frame, verbose=False)[0]
        detections = sv.Detections.from_ultralytics(result)

        # Filter to ball class, above confidence threshold
        mask = (detections.class_id == ball_class) & (
            detections.confidence >= confidence
        )
        detections = detections[mask]

        if len(detections) > 0:
            detections = tracker.update_with_detections(detections)
            frames_with_ball += 1

        # Build labels: "#<track_id> <conf>"
        labels = []
        if detections.tracker_id is not None:
            for j in range(len(detections.tracker_id)):
                tid = detections.tracker_id[j]
                conf = detections.confidence[j]
                labels.append(f"#{tid} {conf:.2f}")

        annotated = box_annotator.annotate(scene=frame.copy(), detections=detections)
        annotated = label_annotator.annotate(
            scene=annotated, detections=detections, labels=labels
        )

        # Optional per-track trajectory trails
        if trail_length > 0 and detections.tracker_id is not None:
            for j in range(len(detections.tracker_id)):
                tid = int(detections.tracker_id[j])
                bbox = detections.xyxy[j]
                cx = int((bbox[0] + bbox[2]) / 2.0)
                cy = int((bbox[1] + bbox[3]) / 2.0)
                trail_positions.setdefault(tid, []).append((cx, cy))
                # Trim to trail_length
                if len(trail_positions[tid]) > trail_length:
                    trail_positions[tid] = trail_positions[tid][-trail_length:]

            # Draw trails
            for tid, positions in trail_positions.items():
                if len(positions) < 2:
                    continue
                colour = trail_palette[tid % len(trail_palette)]
                for k in range(1, len(positions)):
                    alpha = k / len(positions)
                    thickness = max(1, int(3 * alpha))
                    cv2.line(
                        annotated, positions[k - 1], positions[k], colour, thickness
                    )

        writer.write(annotated)

        if (i + 1) % 50 == 0:
            print(f"  {i + 1}/{len(raw_frames)} frames processed...")

    writer.release()
    det_time = time.time() - t1
    total_time = time.time() - t0

    print(f"\nDone in {total_time:.1f}s")
    print(f"Output: {out_path}")
    print(
        f"Summary: {frames_with_ball}/{len(raw_frames)} frames with detections "
        f"({frames_with_ball / len(raw_frames) * 100:.1f}%) "
        f"in {det_time:.1f}s ({len(raw_frames) / det_time:.1f} fps)"
    )


# ------------------------------------------------------------------
# CLI
# ------------------------------------------------------------------

DEFAULT_MODEL = "ml_models/yolo_tennis_ball.pt"


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Ball tracking annotation (YOLO + ByteTrack)"
    )
    parser.add_argument("--video", required=True, help="Input video path")
    parser.add_argument("--out", default=None, help="Output annotated video path")
    parser.add_argument(
        "--model",
        default=None,
        help=f"Model weights path (default: {DEFAULT_MODEL})",
    )
    parser.add_argument(
        "--start", type=float, default=0.0, help="Start time in seconds"
    )
    parser.add_argument("--end", type=float, default=None, help="End time in seconds")
    parser.add_argument("--conf", type=float, default=0.5, help="Confidence threshold")
    parser.add_argument(
        "--trail",
        type=int,
        default=0,
        help="Trail length per track in frames (0 = no trails)",
    )
    args = parser.parse_args()

    video_path = Path(args.video)
    if not video_path.exists():
        print(f"ERROR: video not found: {video_path}")
        sys.exit(1)

    if args.out:
        out_path = Path(args.out)
    else:
        out_path = video_path.parent / (video_path.stem + "_annotated.mp4")

    model_path = Path(args.model) if args.model else Path(DEFAULT_MODEL)

    annotate(
        video_path=video_path,
        out_path=out_path,
        model_path=model_path,
        start_sec=args.start,
        end_sec=args.end,
        confidence=args.conf,
        trail_length=args.trail,
    )


if __name__ == "__main__":
    main()
