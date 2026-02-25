# Background jobs (RQ)

We use **Redis Queue (RQ)** for slow work:

- Pose detection (MediaPipe)
- Ball detection (YOLO + ByteTrack)

## Data Flow: Biomechanics Loop

```mermaid
sequenceDiagram
    participant User
    participant Frontend
    participant API
    participant RQ
    participant PoseService
    participant BiomechService
    participant DB

    User->>Frontend: Upload serve video
    Frontend->>API: POST /v0/videos/upload
    API->>DB: Create video record
    API->>Frontend: Return video_id

    User->>Frontend: Tag serve windows
    Frontend->>API: POST /v0/serve-windows/
    API->>DB: Create serve_window records
    API->>Frontend: Return serve_window_ids

    User->>Frontend: Trigger pose analysis
    Frontend->>API: POST /v0/analysis/videos/{id}
    API->>RQ: Enqueue analyze_pose_detection_scout_refine_rq (via enqueue_pose_analysis helper)
    API->>Frontend: Return job_id

    RQ->>PoseService: Run pose detection
    PoseService->>DB: Save pose_detections

    User->>Frontend: Open biomechanics panel
    Frontend->>API: GET /v0/serve-windows/{id}/biomechanics
    API->>BiomechService: Compute phases + metrics (lazy if missing)
    BiomechService->>DB: Store serve_biomechanics_reports
    API->>Frontend: Return biomechanics report
    Frontend->>User: Display phases + metrics
```

## Local dev (Docker Compose)

```bash
docker compose up -d
docker compose logs -f worker
```

RQ dashboard (if enabled in compose): `http://localhost:9181`

## Host worker setup (recommended for ball detection)

Ball detection loads torch + YOLO + ByteTrack (~2-3 GB). On macOS, running the worker on the host gives MPS GPU acceleration and avoids Docker VM memory limits.

```bash
# Start Docker services WITHOUT the worker container
docker compose up --build backend frontend postgres redis rq-dashboard

# Start worker on host — MUST run from backend/ directory
cd backend && source .venv/bin/activate
REDIS_URL=redis://localhost:6379/0 \
DATABASE_URL=postgresql://tennis:tennis_dev@localhost:5432/tennis_coach \
python scripts/start_rq_worker.py
```

**Critical:** The worker must run from `backend/` because config uses relative paths:
- `ML_MODELS_DIR = "ml_models"` resolves to `backend/ml_models/`
- `UPLOAD_DIR = "../data/videos/raw"` resolves to `data/videos/raw/`

YOLO defaults to auto device selection on macOS. For backfill jobs, you can now force a device with `--device` (for example, `mps`). Check worker logs for `YOLO inference device: ...`.

## Key env vars

```bash
REDIS_URL=redis://localhost:6379/0
DATABASE_URL=postgresql://tennis:tennis_dev@localhost:5432/tennis_coach
SERVICE_TYPE=api   # or worker
PROFILE=local      # or production
```

`REDIS_URL` must be set explicitly for the host worker — `redis_config.py` does not auto-detect localhost like `config.py` does for `DATABASE_URL`.

## Where tasks live

- Queue wiring: `app/core/redis_config.py`
- Task functions:
  - `app/services/rq_tasks.py::analyze_pose_detection_scout_refine_rq` — full pipeline (pose + ball + biomechanics)
  - `app/services/rq_tasks.py::run_ball_detection_rq` — standalone ball detection for existing videos
  - `app/services/rq_tasks.py::transcode_video_rq`

## Backfilling ball detection

For videos analyzed before ball detection was integrated:

```bash
# Preview what would be queued
cd backend && python scripts/backfill_ball_detection.py --dry-run

# Enqueue ball detection jobs
cd backend && python scripts/backfill_ball_detection.py

# Enqueue and force Apple Metal (MPS) on host worker
cd backend && python scripts/backfill_ball_detection.py --device mps
```

## Operational notes

- The API enqueues; workers must run the **same code + deps**.
- Prefer keeping job payloads small (IDs + paths), write results to DB.
