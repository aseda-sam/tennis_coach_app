# ADR 001: Replace YOLOv11n with TrackNetV2 for Ball Detection

**Status:** Superseded
**Date:** 2026-02-21
**Superseded:** 2026-02-22 — Replaced by fine-tuned YOLOv8 + ByteTrack. TrackNet was
never deployed to production; real-world testing showed the fine-tuned YOLO model with
ByteTrack object tracking handled static-ball separation more simply and effectively.

## Decision

Replace YOLOv11n (COCO class 32 "sports ball") with TrackNetV2 as the tennis ball
detector in the video analysis pipeline.

## Context

YOLOv11n was used as an expedient MVP detector. It has proven inadequate for serve analysis:

- **Not trained on tennis:** COCO "sports ball" covers footballs, basketballs, etc.
  Tennis balls in motion blur look nothing like the training distribution.
- **No temporal context:** Single-frame inference means one missed frame breaks the
  detection chain entirely. Fast serves produce severe motion blur that YOLO cannot
  handle.
- **Contact NULL rate:** 11 of 12 serve window rows have `contact_timestamp = NULL`
  — the detector simply fails to find the ball when it matters most.
- **Static ball bug:** `toss_peak_height = 0` because YOLO locks onto a static ball on
  the court floor rather than the tossed ball. This corrupts toss height metrics.

TrackNetV2 was designed specifically for this problem:

- Trained on tennis ball trajectories (Taiwan Open dataset + augmented synthetic data)
- Takes 3 consecutive frames as input (9-channel tensor), producing a heatmap per frame
- Temporal context makes it robust to motion blur and short occlusions
- Heatmap response is naturally biased toward *moving* objects — static floor balls
  produce near-zero response, eliminating the toss_peak_height bug

## Alternatives Considered

| Alternative | Reason rejected |
|---|---|
| Fine-tune YOLO on Roboflow tennis dataset | Static image fine-tuning cannot teach temporal motion robustness. Would address class mismatch but not the blur/occlusion problem. |
| TrackNetV3 (with InpaintNet) | InpaintNet is trained on badminton rally footage and may not generalise to serve clips. Adds complexity with uncertain benefit. TrackNetV2 gives us full control over interpolation. |
| Kalman filter (post-YOLO smoothing) | Garbage in, garbage out. Smoothing cannot recover frames where YOLO never detected a ball. Deferred as future enhancement if TrackNetV2 gaps require it. |

## Implementation

- **Model:** TrackNetV2 VGG-16 encoder + U-Net decoder. Input `[B, 9, H, W]` (3 RGB
  frames concatenated). Output `[B, 3, H, W]` heatmaps. We use the middle frame's heatmap.
- **Resolution:** 512×288 (standard TrackNetV2 inference resolution).
- **Post-processing:** Two-stage — velocity filter (suppress static balls) then cubic
  spline interpolation (fill short gaps ≤8 frames).
- **Weights:** Downloaded from TrackNetV2 authors' release at container start; placed at
  `ml_models/tracknet_v2.pt`.
- **BN train-mode workaround:** The `track.pt` checkpoint (TF→PyTorch conversion by
  ChgygLin) has scrambled BatchNorm running stats — buffer sizes were not remapped
  correctly during conversion. In eval mode, BN uses these corrupted frozen stats,
  producing a flat heatmap (~0.46–0.47, range ~0.012) with no detectable peaks.
  Fix: after loading, call `model.eval()` then set all `BatchNorm2d` layers back to
  `train()` mode. This makes BN use live per-batch statistics rather than frozen running
  stats, restoring full heatmap range (0.0–1.0). Conv and output layers remain in eval
  mode for deterministic behaviour.

## Consequences

- **Remove:** `ultralytics` dependency, YOLO env vars and cache dirs in Dockerfile.
- **Add:** `torch`, `torchvision`, `scipy` to `[worker]` extras in `pyproject.toml`.
- **Bump:** `ANALYSIS_VERSION` to `"phase-metrics-v4"` to invalidate cached reports.
- **Update:** `contact_detector.py` — raise `UPPER_FRAME_Y_FRACTION` to 0.65, adjust
  confidence gate for interpolated vs non-interpolated frames.
- **Schema change:** Ball detection per-frame dicts gain an `"interpolated": bool` field.

## Hardware and production considerations

**Local (Apple Silicon):** `load_tracknet_model` selects CUDA → MPS → CPU in order.
On an M1/M2/M3 Mac the MPS backend (Metal GPU) gives 5–20× speedup over CPU.
TrackNetV2 is still ~2–5s per 30-frame serve window on M1 CPU; with MPS this drops
to a few hundred milliseconds.

**Production (Fly.io, no GPU):** Ball detection is the most compute-intensive step in
the pipeline and not viable on shared CPU workers without dedicated GPU infra.
To disable it in production without code changes, set this env var on the Fly.io worker:

```
BALL_DETECTION_ENABLED=false
```

Then add an early-exit guard in `rq_tasks.py` where `TrackNetBallDetectionService` is
called — the job already wraps it in `try/except` so it degrades gracefully; a missing
env var just means `contact_timestamp` stays NULL until GPU infra is available.
The rest of the pipeline (pose, phase segmentation, biomechanics) is unaffected.
