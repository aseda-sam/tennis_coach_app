# ADR 004: Three-Phase Serve Segmentation

**Status:** Accepted
**Date:** 2026-03-05
**Supersedes:** ADR 003 (phase count only — KTP architecture from 003 is retained)

## Context

ADR 003 redesigned phase segmentation around 4 Key Time Points (KTPs) and 4 user-facing
phases: Toss, Trophy & Load, Acceleration, Follow-Through. The KTP-based architecture
solved the structural problems with the original 8-stage Kovacs implementation (silent
phase drops, unreliable velocity detection, beginner coverage gaps).

However, data analysis across 61 serve windows (two players, 6 videos) reveals that the
**Trophy & Load phase is unreliable as a standalone phase**:

### Finding 1: Trophy & Load collapses to nothing


| Metric                                              | Value                             |
| --------------------------------------------------- | --------------------------------- |
| Serves with trophy == racket_low_point (same frame) | 15/61 (25%)                       |
| Serves with trophy_load < 10% of total frames       | 28/61 (46%)                       |
| Trophy-to-RLP gap distribution                      | Bimodal: 0 frames OR 21-50 frames |


The phase either captures real biomechanical activity (when there's a clear racket drop)
or collapses to a single frame (0.03s). Both players are affected equally.

### Finding 2: Loading is concurrent with tossing, not sequential

Analysis of knee_hip_ratio curves shows that knee bend (the "loading" component) starts
well before trophy position:


| Serve         | Knee bend starts | Trophy at | Loading overlaps toss by |
| ------------- | ---------------- | --------- | ------------------------ |
| SW 5          | frame 8          | frame 89  | 91%                      |
| SW 10         | frame 2          | frame 22  | 91%                      |
| SW 48         | frame 1          | frame 28  | 96%                      |
| SW 32         | frame 3          | frame 18  | 83%                      |
| Typical range |                  |           | 70-90%                   |


Peak knee bend often occurs BEFORE trophy position (e.g., SW 5: min knee at frame 54,
trophy at frame 89). By the time the "Trophy & Load" phase begins, loading is already
complete — the player is extending upward.

### Finding 3: Non-overlapping phases force a false choice

The current model requires each frame to belong to exactly one phase. Since loading and
tossing happen concurrently, this forces loading into either:

- The Toss phase (wrong label — toss is about ball trajectory)
- The Trophy & Load phase (too late — loading is already done)

Neither is accurate. The phase boundary at trophy_position is not a meaningful transition
between distinct biomechanical activities.

### Root cause

This is not a detection bug. The racket low point detector works correctly. The problem
is structural: Kovacs & Ellenbecker (2011) describe Loading and Cocking as **converging
at Trophy Position** — they are parallel activities, not sequential phases. A non-overlapping
model cannot represent this without distortion.

## Decision

### Reduce to 3 user-facing phases

Remove Trophy & Load as a standalone phase. Merge the preparation activities into a single
phase:


| Phase              | Boundaries                     | What it captures                                         |
| ------------------ | ------------------------------ | -------------------------------------------------------- |
| **Toss & Load**    | Start → Racket Low Point       | Toss trajectory, knee loading, body coiling, racket drop |
| **Acceleration**   | Racket Low Point → Ball Impact | Upward swing, kinetic chain, contact                     |
| **Follow-Through** | Ball Impact → End              | Deceleration, landing, recovery                          |


### Retain all 4 KTPs

Trophy Position remains a detected moment marker within the Toss & Load phase. This
preserves:

- Knee flexion measurement at trophy (metric computed at KTP, not phase boundary)
- Trophy filmstrip frame selection
- Timeline annotation showing the trophy moment
- Future metrics that reference trophy position (arm angle, shoulder rotation)

Ball Release also remains — it marks the toss start within the Toss & Load phase.

### Design guard rails for future evolution

The synthesis considered allowing overlapping phases (Option A) vs simplifying to 3
non-overlapping phases (Option B). Option A is biomechanically correct but premature
with only 4 metrics and a 1-person team. These guard rails preserve the path:

1. **KTPs are first-class, independent of phases.** The schema stores KTPs and phases
  separately. Phases are derived from KTPs. A future version can derive overlapping
   phases from the same KTPs without data migration.
2. **Metrics attach to KTPs, not phases.** `knee_flexion_min_deg` is "knee flexion
  near trophy KTP," not "a Toss & Load metric." The `METRIC_META` phase field is for
   display grouping only — metric computation never references phase boundaries. This
   is already the case in the current codebase and must be preserved.
3. **Phase model is versioned.** `phase_segmentation_version` in reports enables
  recomputation. A future `phase-seg-v6` can introduce overlapping phases without
   migrating historical data.
4. **Frontend renders phases from data, not hardcoded slots.** `ServePhaseTimeline`
  already renders from a `PhaseWindow[]` array. `MetricsByPhasePanel` has a hardcoded
   `PHASE_ORDER` that must be updated but already handles arbitrary phase keys via
   fallback formatting.
5. **Store Loading Onset as a future KTP.** When knee flexion trend detection is
  reliable, add a `loading_onset` moment marker. This provides the raw boundary
   needed to retroactively derive overlapping phases.

## Version changes


| Component                  | Old                                               | New                                           |
| -------------------------- | ------------------------------------------------- | --------------------------------------------- |
| Phase segmentation version | `phase-seg-v4`                                    | `phase-seg-v5`                                |
| Analysis version           | `phase-metrics-v7`                                | `phase-metrics-v8`                            |
| Phase enum values          | `toss, trophy_load, acceleration, follow_through` | `toss_and_load, acceleration, follow_through` |
| Phase count                | 4                                                 | 3                                             |
| KTP count                  | 4                                                 | 4 (unchanged)                                 |


## Consequences

### What improves

- No more 0.03s phases shown to users
- Phase boundaries built on the two strongest detected signals (RLP, BI)
- Phase model matches coaching language ("your preparation," "your swing," "your finish")
- Simpler data for LLM coaching prompts

### What changes

- `ServePhase` enum loses `TROPHY_LOAD`, gains `TOSS_AND_LOAD` (replaces `TOSS`)
- `PHASE_ORDER` becomes 3 entries
- Phase derivation logic simplified (2 boundaries instead of 3)
- All phase label maps updated (backend routes, frontend components)
- Tests rewritten for 3-phase assertions
- Analysis version bumps trigger recomputation for existing serves

### What we preserve

- All 4 KTPs detected and stored
- Trophy Position as a moment marker (visible on timeline, used for metrics)
- Metric computation logic unchanged (already KTP-based, not phase-based)
- Path to overlapping phases via guard rails above

### What we defer

- Overlapping phases (until 10+ metrics span multiple concurrent activities)
- Loading Onset KTP detection (until knee flexion trend detection is reliable)
- Camera-angle-aware phase detection

## References

- ADR 003: Phase Segmentation Redesign (KTP architecture, retained)
- Kovacs & Ellenbecker (2011). "An 8-Stage Model for Evaluating the Tennis Serve."
Loading and Cocking described as converging at Trophy Position.
- **Keaney & Reid (2024)**. Systematic review confirming 4 canonical KTPs.
- Internal data analysis: 61 serve windows, 2 players, knee_hip_ratio feature curves
