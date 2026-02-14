# Background jobs (RQ)

We use **Redis Queue (RQ)** for slow work:

- Pose detection (MediaPipe)
- Serve attempt analysis runs synchronously (not via RQ)

## Data Flow: Serve Analysis Loop

```mermaid
sequenceDiagram
    participant User
    participant Frontend
    participant API
    participant RQ
    participant PoseService
    participant ServeService
    participant DB

    User->>Frontend: Upload serve video
    Frontend->>API: POST /v0/videos/upload
    API->>DB: Create video record
    API->>Frontend: Return video_id

    User->>Frontend: Tag serve attempts
    Frontend->>API: POST /v0/serve-attempts/
    API->>DB: Create serve_attempt records
    API->>Frontend: Return serve_attempt_ids

    User->>Frontend: Trigger pose analysis
    Frontend->>API: POST /v0/analysis/videos/{id}
    API->>RQ: Enqueue analyze_pose_detection_rq
    API->>Frontend: Return job_id

    RQ->>PoseService: Run pose detection
    PoseService->>DB: Save pose_detections

    User->>Frontend: Trigger serve analysis
    Frontend->>API: POST /v0/videos/{id}/analyze-serves
    API->>ServeService: Calculate metrics (sync)
    ServeService->>DB: Update serve_attempts (elbow_angle_at_contact)

    Frontend->>API: GET /v0/serve-attempts/me
    API->>DB: Query serve_attempts
    API->>Frontend: Return metrics + recommendations
    Frontend->>User: Display metrics + one recommendation
```

## Local dev (Docker Compose)

```bash
docker compose up -d
docker compose logs -f worker
```

RQ dashboard (if enabled in compose): `http://localhost:9181`

## Key env vars

```bash
REDIS_URL=redis://localhost:6379/0
SERVICE_TYPE=api   # or worker
PROFILE=local      # or production
```

## Where tasks live

- Queue wiring: `app/core/redis_config.py`
- Task functions:
  - `app/services/rq_tasks.py::analyze_pose_detection_rq`

## Operational notes

- The API enqueues; workers must run the **same code + deps**.
- Prefer keeping job payloads small (IDs + paths), write results to DB.
