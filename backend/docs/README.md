# Backend docs

This folder is for **single-topic** docs that are easy to keep accurate.

- For API details, prefer **FastAPI OpenAPI** at `http://localhost:8000/docs`.
- For "what exists", prefer the **code** (models + routes) over long docs.

## What to read

- [`docs/serve-mvp.md`](../../docs/serve-mvp.md): MVP scope + serve workflow — lives in root docs (relevant to all contributors).
- `phase-detection-heuristics.md`: How serve phases are detected from pose keypoints (heuristics, features, confidence scores). Documents the original 8-phase Kovacs model; the app now uses a simplified 4-phase model (see ADR 003).
- `config.md`: `PROFILE`-based config (local vs production).
- `background-jobs.md`: RQ worker + queues (pose detection + biomechanics on demand).
- `observability.md`: OpenTelemetry + structured logs plan (traces, IDs, Grafana Cloud).
- `deploy-flyio.md`: Fly.io deploy notes (optional, only if you deploy).
- `demo-videos.md`: Demo video setup/rotation (optional).
