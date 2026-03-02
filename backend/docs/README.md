# Backend docs

This folder is for **single-topic** docs that are easy to keep accurate.

- For API details, prefer **FastAPI OpenAPI** at `http://localhost:8000/docs`.
- For "what exists", prefer the **code** (models + routes) over long docs.

## What to read

- `config.md`: `PROFILE`-based config (local vs production).
- `background-jobs.md`: RQ worker + queues (pose detection + biomechanics on demand).
- `database_schema.md`: Core tables and fields that affect behavior and feature contracts.
- `ball-detection-fine-tuning.md`: YOLOv8 fine-tuning guide for the tennis ball detector.
- `deploy-flyio.md`: Fly.io deploy notes (optional, only if you deploy).
- `demo-videos.md`: Demo video setup/rotation (optional).
