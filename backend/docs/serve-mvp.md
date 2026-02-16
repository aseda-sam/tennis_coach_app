# Serve MVP: scope + workflow

This project is currently optimizing for a **focused serve-analysis loop**:

- **One shot type**: serve
- **One phase**: a single named phase (keep it consistent)
- **3–5 metrics**: simple + coach-meaningful
- **One recommendation**: one high-leverage improvement (not 10)

Out of scope (for now): ball detection/trajectory, multi-shot rally analysis, complex interaction effects.

## The “serve loop” (today)

1. **Upload** a serve drill video
2. **Tag serve windows** (time windows + contact timestamp)
3. Run **pose detection** (background job)
4. Open **biomechanics report** (lazy compute) → stores phases + metrics
5. Render a small set of metrics in the biomechanics panel

## Data model (what matters for MVP)

Core tables (see `app/models/`):

- `videos`: uploaded videos + session metadata (`session_type`, `camera_angle`, etc.)
- `players` and `video_players`: associate players to videos
- `pose_detections`: pose keypoints per video
- `serve_windows`: user-tagged serve windows + contact timing
- `serve_biomechanics_reports`: computed phases + raw metrics per serve

## Design constraints (aligned to the vision)

- Prefer **layman terms** in UI (“outstretched arm”) over raw angles.
- Keep metrics **legible** and **explain why** they matter.
- Keep iteration fast: fewer moving parts, fewer features, fewer docs.
