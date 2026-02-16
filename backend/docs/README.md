# Backend docs

This folder is for **single-topic** docs that are easy to keep accurate.

- For API details, prefer **FastAPI OpenAPI** at `http://localhost:8000/docs`.
- For “what exists”, prefer the **code** (models + routes) over long docs.

## What to read

- `serve-mvp.md`: MVP scope + “serve loop” workflow (what we’re building now).
- `config.md`: `PROFILE`-based config (local vs production).
- `background-jobs.md`: RQ worker + queues (pose detection + biomechanics on demand).
- `observability.md`: OpenTelemetry + structured logs plan (traces, IDs, Grafana Cloud).
- `deploy-flyio.md`: Fly.io deploy notes (optional, only if you deploy).
- `demo-videos.md`: Demo video setup/rotation (optional).
- `magic_link_email_template.md`: Magic link email template (optional).
