# ADR 005: Static-Distractor Filter for Ball Detection

**Status:** Accepted
**Date:** 2026-05-08
**Amends:** ADR 002 (extends YOLO + ByteTrack pipeline; assumption that
"ByteTrack alone handles static separation" no longer holds)

## Context

ADR 002 chose YOLO + ByteTrack (with a fine-tuned, court-specific model)
because per-frame YOLO produces a stream of detections without persistent
identities, and ByteTrack's tracker IDs are what let us pick the moving
serve ball out of a noisy frame. The reasoning: a *moving* ball forms a
track with high displacement, while *static* objects (court markings,
fence posts, sponsor logos) form low-displacement tracks that lose the
selection battle. Track selection ranks by sliding-window peak displacement.

That assumption breaks in real-world video footage when **multiple actual
tennis balls are present on the court** during a session — a common case
when warming up alone with a basket of balls. Video 39
(`PXL_20260427_122519582_1.mp4`, 4 serves, Royal Victoria, 2026-04-27)
exhibited 100% reported detection rate but the stick-figure view rendered
no ball: every serve window's "ball" was the same static cluster at
~(32, 564) — a real tennis ball lying on the left edge of the court.

Two layered failures produced the wrong answer:

1. **Selection by default.** When the moving serve ball was detected only
   on isolated 1-frame fragments (no consecutive frames → no peak-window
   displacement), the static ball was the only multi-frame track. Track
   selection picked it because *something* had to win, even with a peak
   of ~1 px from sub-pixel jitter.
2. **Safety-net miscalibration.** When the moving ball *was* tracked
   correctly (3–5 consecutive frames at the toss apex), the chosen track
   represented <25% of total YOLO detections (because the static balls
   produced 80–90% of detections). A guard in `analyze_serve_windows`
   interpreted low retention as "ByteTrack is dropping the real ball" and
   fell back to per-frame `argmax(confidence)` — which always picked the
   high-confidence static ball over the lower-confidence moving ball.

The 25% retention rule was tuned for an earlier regime where YOLO had
moderate recall and most detections per frame were the (one) real ball.
Three things changed since: imgsz raised to 1280, video transcoded at
1080p/CRF 18, and weights replaced by a court-specific fine-tuned model.
The denominator (total YOLO detections) grew faster than the numerator
(chosen-track frames), so the ratio dropped without reflecting any actual
quality regression.

## Decision

Add an explicit concept of "static distractor" to the pipeline, with two
layered safeguards in `_select_ball_track` and one structural change in
`analyze_serve_windows`.

### 1. Pooled static-distractor scan

A new function `_identify_static_distractors` runs after all serve
windows have been processed by YOLO + ByteTrack. It pools tracks across
all windows by spatial proximity (mean centroid within 5 px) and flags
any pooled cluster as a **static distractor** if:

- the cluster's tracks collectively cover ≥ 30 frames *across the pool*, AND
- no track in the cluster has displacement > 3 px (bbox-diagonal proxy for
  max pairwise centroid distance).

Pooling is intentional: the same physical ball is present in multiple
serve windows of a single session, so cross-window evidence is more
robust than per-window thresholds. Track IDs are not shared across
windows (fresh ByteTrack per window), so spatial position is the
clustering key.

### 2. Minimum peak-displacement gate in track selection

`_select_ball_track` returns `None` if no remaining track's
sliding-window peak displacement exceeds **5 px / 5 frames** (real toss
arcs span tens to hundreds of px in a 5-frame window; sub-pixel jitter
accumulates to ~1–2 px). This is independent of #1 and prevents the
"least-bad track wins by default" failure even when distractor filtering
has nothing to filter.

When `_select_ball_track` returns `None`, the window's frames are
emitted with `ball_x = ball_y = None` rather than a confidently-placed
distractor. Spline interpolation already handles missing data downstream.

### 3. Drop the 25% retention safety net

The `bt_kept / yolo_detected >= 0.25` check and the `argmax(confidence)`
fallback path are removed. The fine-tuned model + ByteTrack +
distractor filter are the trusted path; if that combination yields no
qualifying track, the window has no usable ball data.

### 4. Auto-pipeline opt-out: `AUTO_BALL_DETECTION_ON_UPLOAD`

Default `False`. The auto-pipeline runs once after upload, on the
heuristic-generated serve windows — but cleanup (deleting accidental
tosses, opponent returns, etc.) almost always invalidates that snapshot.
Skipping the auto-run avoids ~90s of wasted compute per upload and forces
detection to happen *after* cleanup. A "Re-run ball detection" button in
`ServeWindowsPanel` is the canonical entry point. The
`get_video_analysis_status` endpoint now returns
`is_ball_detection_stale` so the UI can surface a stale indicator when
windows have been edited since the last run.

## Consequences

### Positive

- Video 39 produces correct output: serve 1 returns no ball data (no
  qualifying moving track existed); serves 2–4 select the toss-arc burst
  rather than the static distractor.
- The pipeline degrades gracefully on hard frames: missing data is
  honest, splines fill short gaps, the UI can show "no ball detected"
  rather than a phantom static position.
- Cross-window pooling makes distractor identification more robust than
  any per-window threshold.

### Negative / risks

- The displacement gate (5 px / 5 frames) and the distractor thresholds
  (3 px / 30 frames / 5 px radius) are calibrated against video 39 and a
  small set of known-good videos. Edge cases (very slow tosses; tracks
  that briefly intersect a static cluster) may need re-tuning. Tests in
  `backend/tests/services/ball_detection/test_yolo_detection_service.py`
  pin the v39 behaviour as a regression fixture.
- The fallback `argmax(confidence)` path is gone, so any future scenario
  where ByteTrack genuinely drops a real ball mid-window (without forming
  a multi-frame track at all) will produce empty output. This is the
  right default given current data, but if future videos show this
  pattern we revisit.

### Neutral

- Track selection now has two gates (excluded IDs from #1, displacement
  threshold from #2). Both are optional kwargs on `_select_ball_track`,
  so unit tests for the existing behaviour continue to pass with the
  defaults.

## References

- `backend/app/services/ball_detection/yolo_detection_service.py` —
  implementation of `_identify_static_distractors`, the displacement
  gate, and the refactored `analyze_serve_windows` two-pass flow.
- `backend/tests/services/ball_detection/test_yolo_detection_service.py`
  + `v39_fixture.py` — regression tests pinning v39 behaviour.
- `backend/docs/ball-detection-fine-tuning.md` — operational guide; its
  "Known issue: static false-positive" section is updated to point here.
- ADR 002 — original YOLO + ByteTrack decision (still load-bearing for
  the rest of the pipeline; this ADR amends only the assumption about
  static separation).
