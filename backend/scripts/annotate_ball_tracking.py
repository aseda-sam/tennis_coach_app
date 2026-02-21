"""Standalone ball tracking annotation script for visual verification.

Runs YOLO or TrackNetV2 on a video and writes an annotated MP4 showing:
  - Yellow circle at each detected ball position
  - Magenta trail (last N positions) showing the trajectory arc
  - Blue circle for interpolated positions (filled by spline)
  - Per-frame text: frame index, timestamp, confidence value
  - Detection stats in the corner

Usage:
    # Inside the worker container (YOLO, default):
    docker compose exec worker python backend/scripts/annotate_ball_tracking.py \
        --video data/videos/raw/sinner_slm_serve.mp4 \
        --out /tmp/annotated_serve.mp4

    # Compare with TrackNet:
    docker compose exec worker python backend/scripts/annotate_ball_tracking.py \
        --video data/videos/raw/sinner_slm_serve.mp4 \
        --detector tracknet

Options:
    --video     Path to input video (required)
    --detector  Detection backend: yolo (default) or tracknet
    --out       Output path (default: <input>_annotated.mp4)
    --model     Model weights path (default depends on --detector)
    --start     Start time in seconds (default: 0 = beginning)
    --end       End time in seconds (default: None = full video)
    --conf      Confidence threshold (default: 0.5)
    --trail     Number of trailing ball positions to draw (default: 15)
    --heatmap   Also save a side-by-side heatmap overlay video (TrackNet only)
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

from app.services.ball_detection.trajectory_smoother import TrajectorySmoother
from app.utils.video_utils import get_video_rotation

# ------------------------------------------------------------------
# Colours (BGR)
# ------------------------------------------------------------------
COLOUR_BALL = (0, 255, 255)  # yellow  — raw detection
COLOUR_INTERP = (255, 0, 255)  # magenta — interpolated
COLOUR_TRAIL = (0, 200, 255)  # amber trail
COLOUR_TEXT = (255, 255, 255)
COLOUR_BG = (0, 0, 0)

TRAIL_RADIUS = 3
BALL_RADIUS = 8
FONT = cv2.FONT_HERSHEY_SIMPLEX


def _rotate_frame(frame: np.ndarray, rotation: int) -> np.ndarray:
    if rotation in (-90, 270):
        return cv2.rotate(frame, cv2.ROTATE_90_CLOCKWISE)
    if rotation in (90, -270):
        return cv2.rotate(frame, cv2.ROTATE_90_COUNTERCLOCKWISE)
    if rotation in (180, -180):
        return cv2.rotate(frame, cv2.ROTATE_180)
    return frame


# ------------------------------------------------------------------
# TrackNet detection helpers (unchanged from original)
# ------------------------------------------------------------------


def _frame_to_tensor(frame: np.ndarray, device: object) -> object:
    """BGR frame -> normalised [3, H, W] tensor on device."""
    import torch

    from app.services.ball_detection.tracknet_model import (
        TRACKNET_HEIGHT,
        TRACKNET_WIDTH,
    )

    rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
    resized = cv2.resize(rgb, (TRACKNET_WIDTH, TRACKNET_HEIGHT))
    arr = resized.astype(np.float32) / 255.0
    return torch.from_numpy(arr).permute(2, 0, 1).to(device)


def _detect_frames_tracknet(
    model: object,
    tensors: list,
    device: object,
    confidence_threshold: float,
    orig_w: int,
    orig_h: int,
) -> list[dict]:
    """Run TrackNet on a list of frame tensors; return raw detection dicts."""
    import torch

    results = []
    with torch.no_grad():
        for k in range(len(tensors)):
            prev_t = tensors[max(0, k - 1)]
            curr_t = tensors[k]
            next_t = tensors[min(len(tensors) - 1, k + 1)]
            inp = torch.cat([prev_t, curr_t, next_t], dim=0).unsqueeze(0)  # [1,9,H,W]
            heatmaps = model(inp)  # [1, 3, H, W]
            mid = heatmaps[0, 1]  # middle frame heatmap [H, W]

            peak_val = float(mid.max().item())
            if peak_val >= confidence_threshold:
                flat_idx = int(mid.argmax().item())
                hmap_h, hmap_w = mid.shape
                hy = flat_idx // hmap_w
                hx = flat_idx % hmap_w
                bx = hx * orig_w / hmap_w
                by = hy * orig_h / hmap_h
            else:
                bx = by = None

            results.append(
                {
                    "ball_x": bx,
                    "ball_y": by,
                    "confidence": peak_val if bx is not None else None,
                    "interpolated": False,
                }
            )
    return results


# ------------------------------------------------------------------
# YOLO detection helpers
# ------------------------------------------------------------------


def _detect_frames_yolo(
    model: object,
    frames: list[np.ndarray],
    confidence_threshold: float,
) -> list[dict]:
    """Run YOLO on a list of BGR frames with ByteTrack; return raw detection dicts.

    Uses ByteTrack to assign persistent track IDs across frames, then selects
    the track with the highest total displacement (the moving ball) and
    discards static background objects.
    """
    import supervision as sv

    from app.services.ball_detection.yolo_detection_service import _select_ball_track

    # Detect ball class index from model
    model_names = getattr(model, "names", {})
    ball_class = 0 if len(model_names) <= 10 else 32  # fine-tuned vs COCO

    # Run YOLO + ByteTrack on all frames
    tracker = sv.ByteTrack()
    tracked_frames: list[tuple[int, sv.Detections]] = []

    for i, frame in enumerate(frames):
        yolo_results = model(frame, verbose=False)
        detections = sv.Detections.from_ultralytics(yolo_results[0])

        # Filter to ball class only, above confidence threshold
        mask = (detections.class_id == ball_class) & (
            detections.confidence >= confidence_threshold
        )
        detections = detections[mask]

        tracked = tracker.update_with_detections(detections)
        tracked_frames.append((i, 0.0, tracked))  # timestamp not needed here

    # Select the ball track
    ball_track_id = _select_ball_track(tracked_frames)
    if ball_track_id is not None:
        print(f"ByteTrack: selected track {ball_track_id} as ball (most displaced)")

    # Build output dicts from the selected track
    results = []
    for _i, _ts, tracked in tracked_frames:
        bx, by, conf = None, None, None
        if ball_track_id is not None and tracked.tracker_id is not None:
            track_mask = tracked.tracker_id == ball_track_id
            if track_mask.any():
                bbox = tracked.xyxy[track_mask][0]
                bx = float((bbox[0] + bbox[2]) / 2.0)
                by = float((bbox[1] + bbox[3]) / 2.0)
                conf = float(tracked.confidence[track_mask][0])

        results.append(
            {
                "ball_x": bx,
                "ball_y": by,
                "confidence": conf,
                "interpolated": False,
            }
        )
    return results


# ------------------------------------------------------------------
# Drawing overlay (shared)
# ------------------------------------------------------------------


def _draw_overlay(
    frame: np.ndarray,
    det: dict,
    trail: list[tuple[float, float, bool]],
    frame_idx: int,
    timestamp_ms: float,
    stats: dict,
    detector_name: str,
) -> np.ndarray:
    """Draw ball position, trail, and stats onto a copy of frame."""
    out = frame.copy()
    h, _w = out.shape[:2]

    # Trail
    for i, (tx, ty, interp) in enumerate(trail):
        alpha = (i + 1) / len(trail)
        colour = COLOUR_INTERP if interp else COLOUR_TRAIL
        # Dim older positions
        r = max(1, int(TRAIL_RADIUS * alpha))
        cv2.circle(out, (int(tx), int(ty)), r, colour, -1)

    # Current ball
    bx, by = det.get("ball_x"), det.get("ball_y")
    if bx is not None and by is not None:
        colour = COLOUR_INTERP if det.get("interpolated") else COLOUR_BALL
        cv2.circle(out, (int(bx), int(by)), BALL_RADIUS, colour, 2)
        cv2.circle(out, (int(bx), int(by)), 2, colour, -1)

    # Frame info (top-left)
    conf = det.get("confidence")
    conf_str = f"conf={conf:.3f}" if conf is not None else "conf=--"
    interp_str = " [interp]" if det.get("interpolated") else ""
    lines = [
        f"[{detector_name}] frame {frame_idx}  t={timestamp_ms / 1000:.2f}s",
        conf_str + interp_str,
    ]
    y = 20
    for line in lines:
        (tw, th), _ = cv2.getTextSize(line, FONT, 0.45, 1)
        cv2.rectangle(out, (8, y - th - 3), (8 + tw + 4, y + 3), COLOUR_BG, -1)
        cv2.putText(out, line, (10, y), FONT, 0.45, COLOUR_TEXT, 1, cv2.LINE_AA)
        y += th + 8

    # Stats (bottom-left)
    stat_lines = [
        f"detected: {stats['detected']}/{stats['total']} ({stats['detected'] / max(1, stats['total']) * 100:.0f}%)",
        f"interp:   {stats['interp']}",
        "legend: O=detected  O=interpolated",
    ]
    y = h - 10
    for line in reversed(stat_lines):
        (tw, th), _ = cv2.getTextSize(line, FONT, 0.4, 1)
        cv2.rectangle(out, (8, y - th - 2), (8 + tw + 4, y + 2), COLOUR_BG, -1)
        cv2.putText(out, line, (10, y), FONT, 0.4, COLOUR_TEXT, 1, cv2.LINE_AA)
        y -= th + 6

    return out


# ------------------------------------------------------------------
# Main annotate entry point
# ------------------------------------------------------------------


def annotate(
    video_path: Path,
    out_path: Path,
    model_path: Path,
    detector: str = "yolo",
    start_sec: float = 0.0,
    end_sec: float | None = None,
    confidence: float = 0.5,
    trail_length: int = 15,
    save_heatmap: bool = False,
) -> None:
    """Main entry point: detect balls and write annotated video."""
    t0 = time.time()

    # --- Load model ---
    if detector == "tracknet":
        import torch

        from app.services.ball_detection.tracknet_model import load_tracknet_model

        print(f"Loading TrackNetV2 from {model_path}...")
        model = load_tracknet_model(model_path)
        device = next(model.parameters()).device
        print(f"Model ready ({time.time() - t0:.1f}s) on {device}")
    else:
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
    frame_indices: list[int] = []
    idx = start_frame
    while idx <= end_frame:
        ret, frame = cap.read()
        if not ret:
            break
        if rotation != 0:
            frame = _rotate_frame(frame, rotation)
        raw_frames.append(frame)
        frame_indices.append(idx)
        idx += 1
    cap.release()

    if not raw_frames:
        print("ERROR: no frames read")
        return

    orig_h, orig_w = raw_frames[0].shape[:2]
    print(f"Read {len(raw_frames)} frames ({orig_w}x{orig_h})")

    # --- Run detection ---
    if detector == "tracknet":
        print("Converting to tensors...")
        tensors = [_frame_to_tensor(f, device) for f in raw_frames]
        print("Running TrackNetV2 inference...")
        t1 = time.time()
        raw_dets = _detect_frames_tracknet(
            model, tensors, device, confidence, orig_w, orig_h
        )
    else:
        print("Running YOLO inference...")
        t1 = time.time()
        raw_dets = _detect_frames_yolo(model, raw_frames, confidence)

    det_time = time.time() - t1
    raw_detected = sum(1 for d in raw_dets if d["ball_x"] is not None)
    print(
        f"Raw detection: {raw_detected}/{len(raw_dets)} frames ({raw_detected / len(raw_dets) * 100:.1f}%) in {det_time:.1f}s ({len(raw_dets) / det_time:.1f} fps)"
    )

    # Add timestamps for smoother
    for _i, (d, fi) in enumerate(zip(raw_dets, frame_indices)):
        d["frame_index"] = fi
        d["timestamp_ms"] = fi * 1000.0 / fps

    # --- Post-process ---
    print("Applying trajectory smoother...")
    smoother = TrajectorySmoother()
    dets = smoother.smooth(raw_dets)
    final_detected = sum(1 for d in dets if d["ball_x"] is not None)
    interp_count = sum(1 for d in dets if d.get("interpolated"))
    print(
        f"After smoothing: {final_detected}/{len(dets)} frames with ball ({interp_count} interpolated)"
    )

    # --- Write annotated video ---
    out_path.parent.mkdir(parents=True, exist_ok=True)
    fourcc = cv2.VideoWriter_fourcc(*"mp4v")
    writer = cv2.VideoWriter(str(out_path), fourcc, fps, (orig_w, orig_h))

    # Heatmap video writer (TrackNet only)
    hm_writer = None
    hm_path = None
    if save_heatmap and detector == "tracknet":
        from app.services.ball_detection.tracknet_model import (
            TRACKNET_HEIGHT,
            TRACKNET_WIDTH,
        )

        hm_path = out_path.with_name(out_path.stem + "_heatmap.mp4")
        hm_writer = cv2.VideoWriter(
            str(hm_path), fourcc, fps, (TRACKNET_WIDTH * 2, TRACKNET_HEIGHT)
        )
    elif save_heatmap and detector == "yolo":
        print(
            "WARNING: --heatmap is only supported with --detector tracknet, ignoring."
        )

    print(f"Writing annotated video to {out_path}...")
    trail: list[tuple[float, float, bool]] = []
    stats = {"total": len(dets), "detected": final_detected, "interp": interp_count}
    detector_label = "YOLO" if detector == "yolo" else "TrackNet"

    for i, (frame, det, fi) in enumerate(zip(raw_frames, dets, frame_indices)):
        ts_ms = fi * 1000.0 / fps

        # Update trail
        if det["ball_x"] is not None:
            trail.append((det["ball_x"], det["ball_y"], det.get("interpolated", False)))
            if len(trail) > trail_length:
                trail.pop(0)

        annotated = _draw_overlay(frame, det, trail, fi, ts_ms, stats, detector_label)
        writer.write(annotated)

        # Optional heatmap frame (TrackNet only)
        if hm_writer is not None:
            import torch

            from app.services.ball_detection.tracknet_model import (
                TRACKNET_HEIGHT,
                TRACKNET_WIDTH,
            )

            with torch.no_grad():
                k = i
                prev_t = tensors[max(0, k - 1)]
                curr_t = tensors[k]
                next_t = tensors[min(len(tensors) - 1, k + 1)]
                inp = torch.cat([prev_t, curr_t, next_t], dim=0).unsqueeze(0)
                hm = model(inp)[0, 1].cpu().numpy()
            hm_bgr = cv2.applyColorMap((hm * 255).astype(np.uint8), cv2.COLORMAP_HOT)
            small_frame = cv2.resize(frame, (TRACKNET_WIDTH, TRACKNET_HEIGHT))
            side_by_side = np.concatenate([small_frame, hm_bgr], axis=1)
            hm_writer.write(side_by_side)

        if (i + 1) % 50 == 0:
            print(f"  {i + 1}/{len(raw_frames)} frames written...")

    writer.release()
    if hm_writer is not None:
        hm_writer.release()

    total_time = time.time() - t0
    print(f"\nDone in {total_time:.1f}s")
    print(f"Output: {out_path}")
    if hm_path:
        print(f"Heatmap: {hm_path}")
    print(
        f"Summary: {final_detected}/{len(dets)} frames tracked ({final_detected / len(dets) * 100:.1f}%), {interp_count} interpolated"
    )


# ------------------------------------------------------------------
# CLI
# ------------------------------------------------------------------

DEFAULT_MODELS = {
    "yolo": "ml_models/yolo_tennis_ball.pt",
    "tracknet": "ml_models/tracknet_v2.pt",
}


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Ball tracking annotation (YOLO or TrackNet)"
    )
    parser.add_argument("--video", required=True, help="Input video path")
    parser.add_argument(
        "--detector",
        choices=["yolo", "tracknet"],
        default="yolo",
        help="Detection backend (default: yolo)",
    )
    parser.add_argument("--out", default=None, help="Output annotated video path")
    parser.add_argument(
        "--model",
        default=None,
        help="Model weights path (default depends on --detector)",
    )
    parser.add_argument(
        "--start", type=float, default=0.0, help="Start time in seconds"
    )
    parser.add_argument("--end", type=float, default=None, help="End time in seconds")
    parser.add_argument("--conf", type=float, default=0.5, help="Confidence threshold")
    parser.add_argument("--trail", type=int, default=15, help="Trail length (frames)")
    parser.add_argument(
        "--heatmap",
        action="store_true",
        help="Also write heatmap debug video (TrackNet only)",
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

    model_path = Path(args.model) if args.model else Path(DEFAULT_MODELS[args.detector])

    annotate(
        video_path=video_path,
        out_path=out_path,
        model_path=model_path,
        detector=args.detector,
        start_sec=args.start,
        end_sec=args.end,
        confidence=args.conf,
        trail_length=args.trail,
        save_heatmap=args.heatmap,
    )


if __name__ == "__main__":
    main()
