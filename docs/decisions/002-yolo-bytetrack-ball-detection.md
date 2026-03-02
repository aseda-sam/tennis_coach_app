# ADR 002: Fine-tuned YOLOv8 + ByteTrack for Ball Detection

**Status:** Accepted
**Date:** 2026-02-22
**Supersedes:** [ADR 001](001-tracknet-v2-ball-detection.md) (TrackNetV2)

## What this is

We use a YOLO model (trained specifically on tennis balls) to spot the ball in each
frame, then ByteTrack to follow it across frames. ByteTrack gives every detected
object a persistent ID — so if there are three balls visible (one in the player's hand,
two on the court), each gets its own track. We then pick the track that moves the most
(the tossed ball) and ignore the rest.

This replaced several earlier attempts that couldn't reliably tell the moving ball
apart from static ones on the court.

## Why this approach

The core problem was always the same: YOLO detects the ball fine, but it also detects
every other ball-shaped thing in the frame. We needed a way to separate "the ball the
player is serving" from background noise.

We tried four things before this worked:

| What we tried | What went wrong |
|---|---|
| Off-the-shelf YOLO (not trained on tennis) | Barely recognised tennis balls. 11/12 serves had no contact detected. |
| TrackNetV2 (a model built for tracking balls in badminton broadcasts) | Built for tiny balls in wide shots. Our close-up phone footage confused it — it detected body edges instead. |
| Fine-tuned YOLO without tracking | Found the ball, but also found 3-4 static balls per frame at similar confidence. No way to tell which was the serve ball. |
| Fine-tuned YOLO + a static calibration map | Filtered out most static balls by memorising their positions in the first few frames. Fragile — missed balls that appeared intermittently. |

ByteTrack made it simple: instead of trying to suppress false positives, just track
everything and pick the one that moves like a tossed ball.

---

## Technical details

### Pipeline flow (per serve window)

1. YOLO inference on each frame
2. ByteTrack assigns persistent track IDs (fresh tracker per serve window)
3. **Track selection:** pick the track with the highest peak displacement in any
   5-frame sliding window (`PEAK_WINDOW = 5`, ~0.17s at 30fps)
4. Build per-frame detection dicts from the selected track's positions
5. After all windows: cubic spline interpolation fills short gaps (≤15 frames)

### Why peak-window displacement (not mean)

ByteTrack often assigns the same track ID to the ball while it's in the player's hand
(stationary) and during the toss (fast movement). If you average displacement across
all frames, those stationary ball-in-hand frames drag the average down. Peak-window
looks at the best 5-frame burst instead — the toss arc's burst (~150-200px) easily
beats any background jitter (~5-10px).

### Why we removed the velocity filter

We originally had a filter that suppressed any run of frames where the ball didn't
move. This made sense before ByteTrack (it caught static false positives), but
afterwards it was doing more harm than good — it was killing the ball-in-hand frames,
which are genuinely the ball, just stationary. Detection rate went from 4.1% to 39.4%
after removing it.

### Per-window scoping

Each serve window gets a fresh ByteTrack instance so track IDs don't leak across
windows. Spline interpolation runs once across all windows combined.

## Known limitations

- **Post-contact track break:** After racket contact the ball changes direction sharply
  and ByteTrack loses it (assigns a new ID). Fine for now — we only need toss through
  contact. Would need track stitching if we ever measure post-contact ball flight.
- **Single-track assumption:** We pick one track per window. If two balls are moving
  simultaneously, we pick the fastest. Not a problem for typical serve footage.

## Key files

- `backend/app/services/ball_detection/yolo_detection_service.py` — production service
- `backend/app/services/ball_detection/trajectory_smoother.py` — spline interpolation
- `backend/app/services/ball_detection/contact_detector.py` — ball-racket contact
- `backend/scripts/annotate_ball_tracking.py` — visual debugging (`--trail N` for trajectories)
- `ml_models/yolo_tennis_ball.pt` — fine-tuned weights (lazy-loaded)
- `backend/docs/ball-detection-fine-tuning.md` — training guide

## Consequences

- **Dependencies:** `ultralytics` (YOLO), `supervision` (ByteTrack), `scipy` (spline)
  in `[worker]` extras.
- **Model:** Fine-tuned `yolo_tennis_ball.pt` at `ml_models/`.
- **Schema:** Per-frame dicts include `interpolated: bool` (True if filled by spline).
- **Version:** `ANALYSIS_VERSION = "phase-metrics-v4"`.
