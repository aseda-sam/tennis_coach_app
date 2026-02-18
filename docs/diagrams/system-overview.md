# System overview

Single-diagram context loader for AI conversations. Paste this into any AI session to orient the model on the full Tennis Coach App architecture in one shot.

```mermaid
flowchart TD
  subgraph CLIENT ["React / TypeScript :3000"]
    UI[Upload & Review UI]
  end

  subgraph API ["FastAPI /v0 :8000"]
    AUTH[Auth middleware]
    ROUTES[Routes]
    SERVICES[Services]
  end

  subgraph BACKGROUND ["Background workers"]
    RQ[Redis Queue]
    WORKER[RQ Worker]
  end

  subgraph STORAGE ["Persistence"]
    DB[(PostgreSQL)]
    FILES[(File storage)]
  end

  subgraph PIPELINE ["Pose & biomechanics pipeline"]
    TRANSCODE[Transcode 720p/30fps]
    SCOUT[Scout pass — lite model]
    DETECT[Detect serve windows]
    REFINE[Refine pass — full model]
    ANALYZE[Biomechanics report — phases + metrics]
  end

  %% Client → API
  UI -->|upload video / review results| AUTH
  AUTH -->|authn + authz| ROUTES
  ROUTES --> SERVICES

  %% API → persistence
  SERVICES --> DB
  SERVICES --> FILES

  %% API → background
  SERVICES -->|enqueue job| RQ
  RQ --> WORKER

  %% Worker pipeline
  WORKER --> TRANSCODE
  TRANSCODE --> SCOUT
  WORKER --> SCOUT
  SCOUT --> DETECT
  DETECT --> REFINE
  REFINE --> ANALYZE

  %% Worker → persistence
  WORKER --> DB
  WORKER --> FILES

  %% Results back to client
  SERVICES -->|JSON responses| UI

  classDef client fill:#e3f2fd,stroke:#1976d2,color:#0d47a1
  classDef api fill:#fff8e1,stroke:#ff8f00,color:#e65100
  classDef bg fill:#f3e5f5,stroke:#7b1fa2,color:#4a148c
  classDef store fill:#e8f5e9,stroke:#388e3c,color:#1b5e20
  classDef pipe fill:#fce4ec,stroke:#c62828,color:#b71c1c

  class UI client
  class AUTH,ROUTES,SERVICES api
  class RQ,WORKER bg
  class DB,FILES store
  class TRANSCODE,SCOUT,DETECT,REFINE,ANALYZE pipe
```

## How to use this diagram

- **AI context loading** — Copy the raw Mermaid block (or the whole file) into the start of any AI conversation about this project. It gives the model the full architecture map in ~40 lines.
- **Orientation** — New contributors can read this before diving into the per-flow diagrams (`auth-flow.md`, `upload-flow.md`, `analysis-pipeline.md`, `data-flow.md`, `db-relationships.md`).

## Key layers

| Layer | Tech | What it does |
|-------|------|--------------|
| Client | React, TypeScript, React Query | Upload videos, review biomechanics reports |
| API | FastAPI, Pydantic v2 | Auth, routes, services — all under `/v0/` |
| Background | Redis Queue (RQ) | Long-running pose detection and transcode jobs |
| Storage | PostgreSQL + local disk / Supabase bucket | Structured data + video files |
| Pipeline | MediaPipe (lite + full) | Transcode → scout → detect windows → refine → analyze |
