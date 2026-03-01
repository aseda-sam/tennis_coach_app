# ADR 003: Phase Segmentation Redesign — KTP-Based Detection

**Status:** Accepted
**Date:** 2026-02-22
**Implemented:** 2026-02-28 — Reduced from 8 Kovacs phases to 4 user-facing phases
(Toss, Trophy & Load, Acceleration, Follow-Through) + 4 moment markers.
Version: `phase-seg-v3` / `phase-metrics-v6`.

## Context

Our current phase segmentation (`phase_segmentation.py`, version `phase-seg-v1`) implements
the Kovacs & Ellenbecker (2011) 8-stage serve model using independent heuristic detectors
for each phase, followed by a monotonic ordering filter that discards out-of-order phases.

This approach has fundamental problems:

1. **Loading and Cocking are detected independently, but Kovacs defines them as converging
   at the same event (Trophy Position).** The monotonic filter silently drops whichever
   one is detected second — which is often Loading, since knee bend timing varies by player.

2. **Acceleration is detected by velocity spike (2x mean), but Kovacs defines it as starting
   at Racket Low Point — a spatial position.** Velocity is noisy from pose jitter and can
   spike during the toss, causing false early detection.

3. **The monotonic filter masks detection failures instead of fixing them.** Users see 3 of
   8 phases with no explanation of what went wrong.

4. **Cocking requires both arms raised.** Beginners with asymmetric form never trigger the
   trophy pose detector, so Cocking is never detected at all.

5. **No contact = no post-contact phases.** If contact_timestamp is missing, Contact,
   Deceleration, and Finish can't be detected (3 of 8 phases gone).

For recreational and beginner players — our primary audience — these issues combine to
produce incomplete, unreliable phase breakdowns.

## Key Insight: 4 Key Time Points, Not 8 Independent Detections

A 2024 systematic review of tennis serve kinematics (Frontiers in Sports and Active Living,
PMC11260724) found that the research literature converges on **4 canonical Key Time Points
(KTPs)** as the practical landmarks for serve segmentation:

| KTP | Definition | What marks it |
|-----|-----------|---------------|
| **Ball Release (BR)** | Ball leaves the toss hand | Toss arm extends upward |
| **Trophy Position (TP)** | Peak arm height + near-peak knee flexion | Composite body pose |
| **Racket Low Point (RLP)** | Racket tip points down behind back | Dominant wrist at lowest Y after trophy |
| **Ball Impact (BI)** | Racket-ball contact | Ball tracking or user tag |

The 8 Kovacs stages are intervals between these 4 KTPs plus start/end:

```
Start ──► BR ──► TP ──► RLP ──► BI ──► end
  │         │      │      │       │      │
  1.Start   2.Rel  3-4.   5.Acc   6.Con  7-8.
                   Load         tact  Decel/
                   +Cock               Finish
```

Detecting 4 KTPs and deriving 8 stages is fundamentally more robust than detecting 8
independent events and hoping they fall in order.

## Decision

### Phase 1: Restructure heuristics around 4 KTPs

Replace the current 8-independent-detector + monotonic-filter architecture with sequential
KTP detection using search windows:

**1. Ball Release (BR)** — Keep current heuristic (toss arm wrist above shoulder), but
search only in first 40% of serve window. Confidence: 0.8.

**2. Trophy Position (TP)** — Detect as a **composite event** after BR:
- Find frames where *any* wrist is above its shoulder (relax from *both*).
- Among those, find peak `max_wrist_height`.
- Validate: `knee_hip_ratio` at that frame must be within 80% of the max observed
  knee bend (within a ±5 frame window). This captures that Loading and Cocking
  co-occur at trophy, rather than treating them as separate events.
- Search window: after BR, first 70% of remaining serve.

**3. Racket Low Point (RLP)** — New detector, replaces velocity-based acceleration:
- After TP, find the frame where dominant wrist Y is at its maximum (lowest point
  in screen coords = racket behind back).
- This is a spatial check — far more robust than velocity thresholds.
- Search window: after TP, before BI (or before 85% of serve if no BI).

**4. Ball Impact (BI)** — Keep current approach (user-tagged or ball tracking).
- Future: auto-detect from ball trajectory apex + wrist proximity.

**Post-BI phases** (Deceleration, Finish) derived from BI using existing heuristics,
but only searched after BI.

**Key architectural change:** Each KTP detector receives the previous KTP's frame as
its search start. Ordering is guaranteed by construction — no monotonic filter needed.

### Phase 2: Manual annotation for validation and tuning

Build a lightweight annotation workflow:

1. Annotate the 4 KTPs on 20-30 serves across skill levels (beginner, club, advanced).
2. Compare heuristic output vs. annotations — compute per-KTP error in frames.
3. Tune thresholds (e.g., wrist height threshold, knee bend validation window) on
   annotated data.
4. Store annotations as ground truth for future ML training.

**Annotation format:** JSON per serve window with frame indices for each KTP.

### Phase 3: ML transition (only if heuristics plateau)

If heuristic error after tuning remains >5 frames on beginners:

- Train a 1D temporal model (MS-TCN or 1D CNN) over MediaPipe joint coordinate
  sequences, with heuristic outputs as additional input features.
- Use the annotated KTPs as training labels.
- The golf swing segmentation literature (PMC7472298) showed this transition reduced
  phase boundary error from 11-79% (heuristic) to 4-9% (BLSTM) with modest data.

## Do We Need All 8 Phases?

**For the user-facing product: probably not initially.** The 8-stage model is a clinical
analysis tool. For a recreational player trying to improve their serve, what matters is:

- **Toss quality** (Start → BR): Was the toss high enough? Consistent placement?
- **Trophy position quality** (BR → TP): Knee bend depth? Arm position?
- **Acceleration mechanics** (TP → BI): Did they use the kinetic chain?
- **Follow-through** (BI → end): Did they decelerate safely?

This maps to **5 user-facing phases** (Start, Toss, Trophy/Load, Acceleration, Follow-Through)
built on top of the 4 KTPs. We can always expose the full 8-stage breakdown as an advanced
view later — progressive disclosure.

However, we should still **detect and store all 4 KTPs internally**, since the granularity
is needed for accurate metrics computation (e.g., knee flexion at trophy, shoulder rotation
at RLP, contact height at BI).

## Racket Tracking

**Should we add racket detection?**

COCO class 38 is "tennis racket," so YOLOv8 can detect it. However:

- Off-the-shelf COCO detection is **unreliable for close-up serve footage** (same domain
  mismatch we hit with ball detection before fine-tuning — see ADR 002).
- We'd need either a fine-tuned multi-class model (ball + racket) or a separate
  `YoloRacketDetectionService`.
- **Racket tracking needs different selection logic** than ball tracking. Ball tracking
  uses peak displacement (moving ball vs. static balls). Racket is always attached to the
  player — you'd track by proximity to dominant wrist instead.

**The case for racket tracking:**
- RLP detection becomes trivial (actual racket tip position instead of wrist proxy).
- Contact detection becomes possible without user tags (racket-ball proximity).
- Racket head speed is a meaningful metric for players.

**The case against (for now):**
- Wrist position is a reasonable proxy for racket position in phase detection.
- Fine-tuning a racket model adds training data collection overhead.
- Ball tracking + wrist position may be sufficient for auto-contact detection.

**Recommendation:** Defer racket tracking until after KTP-based heuristics are validated.
If wrist-based RLP detection proves insufficient, racket tracking becomes the clear next
step. When we do add it, fine-tune a multi-class YOLO model (ball + racket together) rather
than running two separate models.

## Consequences

### What improves
- Phase detection becomes structurally sound (sequential search, no silent drops)
- Beginner serves get better coverage (relaxed trophy pose, composite detection)
- Clear path from heuristic tuning → ML if needed
- User-facing phases are simpler and more actionable

### What changes
- `phase_segmentation.py` gets a significant rewrite (KTP-based architecture)
- Phase output schema gains KTP timestamps alongside phase windows
- Loading and Cocking become sub-aspects of Trophy Position, not independent phases
- Monotonic enforcement is removed entirely

### What we defer
- ML phase classifier (until annotation data exists and heuristics plateau)
- Racket tracking (until wrist-based RLP proves insufficient)
- Camera-angle-aware thresholds (known gap, lower priority than structural fix)

### Risks
- Composite trophy detection is more complex than current independent detectors
- "Near-peak knee bend" validation window (80% of max) needs tuning on real data
- Reducing to 5 user-facing phases means redesigning the phase UI components

## References

- Kovacs & Ellenbecker (2011). "An 8-Stage Model for Evaluating the Tennis Serve."
  Sports Health. PMC3445225.
- Keaney & Reid (2024). Systematic review of tennis serve kinematics.
  Frontiers in Sports and Active Living. PMC11260724.
- Holleczek et al. (2020). Golf swing phase segmentation: BLSTM vs heuristic.
  Sensors. PMC7472298.
- Lea et al. (2017). Temporal Convolutional Networks for Action Segmentation. CVPR.
- Abu Farha & Gall (2019). MS-TCN: Multi-Stage TCN for Action Segmentation. CVPR.
- Google. "Rules of Machine Learning." developers.google.com/machine-learning/guides/rules-of-ml.
