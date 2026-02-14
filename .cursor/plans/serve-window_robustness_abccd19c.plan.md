---
name: serve-window robustness
overview: Design and implement a robust serve-window detector that handles slow-motion clips automatically and uses camera-angle-aware heuristics without requiring new mandatory user input.
todos:
  - id: adaptive-thresholds
    content: Implement motion-normalized thresholds and bounded dynamic duration/velocity logic in heuristic detection
    status: done
  - id: angle-profiles
    content: Add camera-angle profile selection and apply profile-specific detection parameters
    status: done
  - id: fallback-pass
    content: Add one-step fallback detection pass when initial proposals are empty
    status: done
  - id: tests-detector
    content: Expand detector unit tests for slow-motion-like and angle-specific scenarios
    status: done
  - id: metadata-phase2
    content: Optionally add original-vs-transcoded metadata persistence with migration and API exposure
    status: pending
isProject: false
---

# Serve Window Detection Robustness Plan

## What We Learned

- Current failure mode is not missing pose: the detector finds many raised-arm frames, merges them into one long cluster, then drops it when duration exceeds `MAX_SERVE_DURATION`.
- Upload/transcode currently normalizes videos to 720p/30fps, which is good for model consistency but can hide original capture cadence semantics.
- Camera angle metadata already exists and is collected in upload/update flows, but serve-window proposal detection is still angle-agnostic.

## Proposed Product Decisions

- **Slow-motion UX:** keep **auto-only** (no required new user field), per your preference.
- **Camera angle strategy:** implement angle-aware detection profiles now (`behind`, `profile`, `unknown`) with safe fallback behavior.

## Solution Design

### 1) Make detection speed-invariant (auto slow-motion handling)

- Replace fixed time-only assumptions with **motion-normalized logic**:
  - Build per-video motion stats from pose features (e.g., wrist velocity percentiles, arm-raise density, cluster persistence).
  - Derive dynamic thresholds from those stats instead of fixed absolute thresholds only.
- Keep hard duration guards, but add robust splitting/fallback for overlong clusters (already started) and a second-pass recovery path if zero proposals are produced.
- Preserve deterministic behavior by capping dynamic values inside bounded ranges.

### 2) Add camera-angle-aware serve-window profiles

- Use video metadata `camera_angle` to choose profile:
  - `behind`: stricter horizontal stability + arm-raise persistence.
  - `profile`: more tolerant to apparent vertical/horizontal motion changes and longer visible toss setup.
  - `unknown`: blended conservative defaults + lower confidence output.
- Keep one shared detector core with profile configs, not separate codepaths.

### 3) Add automatic fallback cascade when no windows are found

- If pass 1 returns zero proposals:
  - Rerun detection once with relaxed, bounded thresholds (and if `unknown`, try both behind/profile profiles and merge).
- Return proposals with lower confidence tags rather than hard zero where plausible.
- Log which pass/profile succeeded for debugging and future tuning.

### 4) Improve metadata for diagnostics and future modeling (non-UX)

- Persist both **original upload metadata** and **post-transcode metadata** (fps/duration/frame_count), so we can reason about timing transformations and evaluate detector behavior.
- Keep API response backward-compatible; expose additional fields as optional.

### 5) Observability and safety checks

- Add structured logs for:
  - selected profile, dynamic threshold values, fallback stage, reason for window rejection.
- Add “detection diagnostics” counters in logs for quick support triage.

## Files To Touch

- Detection logic and profiles:
  - [/Users/aseda/tennis_coach_app/backend/app/services/serve_detection/heuristic_detector.py](/Users/aseda/tennis_coach_app/backend/app/services/serve_detection/heuristic_detector.py)
  - [/Users/aseda/tennis_coach_app/backend/app/services/serve_detection/feature_extractor.py](/Users/aseda/tennis_coach_app/backend/app/services/serve_detection/feature_extractor.py)
  - [/Users/aseda/tennis_coach_app/backend/app/services/serve_detection/proposal_service.py](/Users/aseda/tennis_coach_app/backend/app/services/serve_detection/proposal_service.py)
- Video metadata persistence (if approved in scope):
  - [/Users/aseda/tennis_coach_app/backend/app/models/video.py](/Users/aseda/tennis_coach_app/backend/app/models/video.py)
  - [/Users/aseda/tennis_coach_app/backend/app/services/video_service.py](/Users/aseda/tennis_coach_app/backend/app/services/video_service.py)
  - [/Users/aseda/tennis_coach_app/backend/app/api/schemas/video.py](/Users/aseda/tennis_coach_app/backend/app/api/schemas/video.py)
- Tests:
  - [/Users/aseda/tennis_coach_app/backend/tests/test_serve_detection_heuristic_detector.py](/Users/aseda/tennis_coach_app/backend/tests/test_serve_detection_heuristic_detector.py)
  - [/Users/aseda/tennis_coach_app/backend/tests/test_serve_detection_api.py](/Users/aseda/tennis_coach_app/backend/tests/test_serve_detection_api.py)
  - [/Users/aseda/tennis_coach_app/backend/tests/test_video_api.py](/Users/aseda/tennis_coach_app/backend/tests/test_video_api.py)

## Implementation Sequence

1. Add profile config + dynamic threshold helpers; refactor detector to consume profile + adaptive thresholds.
2. Add fallback cascade in proposal generation path.
3. Add/expand unit tests for slow-mo-like long-arm sequences, low-motion clips, and angle-specific scenarios.
4. Add API/service tests for zero-to-recovered proposal flow.
5. (Optional phase 2) Persist original-vs-transcoded metadata and add migration/docs updates.

## Risks and Mitigations

- **Risk:** over-detection on non-serve overhead movement.
  - **Mitigation:** require multi-signal agreement (arm raise + velocity burst + bounded duration) and confidence penalties in fallback pass.
- **Risk:** profile complexity drifts.
  - **Mitigation:** config-driven profile map + shared core functions + regression test matrix.

## Validation

- Unit: detector behavior under synthetic slow/normal/profile/behind scenarios.
- Integration: upload -> analysis -> propose path returns non-zero windows for known fixtures.
- Runtime: verify logs show profile selection and fallback usage on difficult clips.
