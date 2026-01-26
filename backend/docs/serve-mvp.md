# Serve MVP: scope + workflow

This project is currently optimizing for a **focused serve-analysis loop**:

- **One shot type**: serve
- **One phase**: a single named phase (keep it consistent)
- **3–5 metrics**: simple + coach-meaningful
- **One recommendation**: one high-leverage improvement (not 10)

Out of scope (for now): ball detection/trajectory, multi-shot rally analysis, complex interaction effects.

## The “serve loop” (today)

1. **Upload** a serve drill video
2. **Tag serve attempts** (time windows + contact timestamp)
3. Run **pose detection** (background job)
4. Run **serve analysis** (background job) → writes metrics onto `serve_attempts`
5. Render a small set of metrics + a single recommendation in the UI

## Data model (what matters for MVP)

Core tables (see `app/models/`):

- `videos`: uploaded videos + session metadata (`session_type`, `camera_angle`, etc.)
- `players` and `video_players`: associate players to videos
- `pose_detections`: pose keypoints per video
- `serve_attempts`: user-tagged serve windows + derived metrics (e.g., elbow angle at contact)

## Design constraints (aligned to the vision)

- Prefer **layman terms** in UI (“outstretched arm”) over raw angles.
- Keep metrics **legible** and **explain why** they matter.
- Keep iteration fast: fewer moving parts, fewer features, fewer docs.

