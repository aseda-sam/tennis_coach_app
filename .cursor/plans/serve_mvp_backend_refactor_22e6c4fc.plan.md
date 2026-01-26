---
name: Serve MVP Backend Refactor
overview: Refactor the backend from a generic "computer vision platform" to a focused "serve coaching tool" by implementing serve-centric data models, narrowing API scope, and deprecating premature features that distract from the MVP goal of delivering actionable serve feedback.
todos: []
isProject: false
---

# Serve MVP Backend Refactor

## Vision Alignment

This refactor aligns with the **serve-focused MVP vision**:

- **One shot type**: serve
- **One phase**: a single named phase (keep it consistent)
- **3–5 metrics**: simple + coach-meaningful
- **One recommendation**: one high-leverage improvement (not 10)

**Out of scope (for now)**: Ball detection/trajectory, multi-shot rally analysis, complex interaction effects, annotated video generation.

## Architecture Overview

### System Architecture (Current)

```mermaid
graph TB
    subgraph "Frontend"
        UI[React UI]
        Upload[Video Upload]
        Tag[Tag Serve Attempts]
        Dashboard[Analysis Dashboard]
    end

    subgraph "Backend API"
        API[FastAPI /v0]
        VideoRoute[Video Routes]
        ServeRoute[Serve Attempt Routes]
        AnalysisRoute[Analysis Routes]
    end

    subgraph "Background Jobs (RQ)"
        Redis[(Redis Queue)]
        PoseJob[Pose Detection Job]
    end

    subgraph "Services"
        PoseService[Pose Detection Service]
        ServeService[Serve Analysis Service]
        StorageService[Storage Service]
    end

    subgraph "Database"
        DB[(PostgreSQL/SQLite)]
        Videos[videos]
        ServeAttempts[serve_attempts]
        PoseDetections[pose_detections]
        Players[players]
    end

    UI --> Upload
    Upload --> VideoRoute
    UI --> Tag
    Tag --> ServeRoute
    UI --> Dashboard
    Dashboard --> ServeRoute

    VideoRoute --> StorageService
    VideoRoute --> Redis
    ServeRoute --> DB
    AnalysisRoute --> Redis
    VideoRoute --> ServeService

    Redis --> PoseJob

    PoseJob --> PoseService

    PoseService --> DB
    ServeService --> DB

    VideoRoute --> DB
    ServeRoute --> DB
```

### Data Flow: Serve Analysis Loop

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

### Database Schema

```mermaid
erDiagram
    VIDEOS ||--o{ SERVE_ATTEMPTS : "has"
    VIDEOS ||--|| POSE_DETECTIONS : "has"
    PLAYERS ||--o{ SERVE_ATTEMPTS : "performs"

    VIDEOS {
        int id PK
        string filename
        string file_path
        float duration
        float fps
        int width
        int height
        string session_type
        string camera_angle
        datetime recorded_at
        string user_id
    }

    SERVE_ATTEMPTS {
        int id PK
        int video_id FK
        int player_id FK
        string user_id
        float start_timestamp
        float end_timestamp
        float contact_timestamp
        float elbow_angle_at_contact
        string court_side
        int serve_number
        string serve_subtype
        string in_out
        datetime created_at
    }

    POSE_DETECTIONS {
        int id PK
        int video_id FK
        int total_frames
        json pose_data
        string status
    }

    PLAYERS {
        int id PK
        string name
        string dominant_hand
        string backhand_style
        string user_id
    }
```

## Current Status

### ✅ Completed

- Serve attempts schema and CRUD endpoints
- Serve analysis service (calculates elbow angle at contact)
- Pose detection via RQ background jobs
- Video upload with session metadata
- Removed non-MVP features (ball detection, video_players, queue-stats, video-quality)

### 🔄 Remaining Work

1. **Recommendation Engine**: Generate one actionable recommendation per serve attempt
2. **Frontend Integration**: Wire serve attempts + analyze-serves into frontend
3. **API Alignment**: Remove legacy frontend calls (ball contacts, analysis GET endpoints)
4. **End-to-End Testing**: Full flow validation

## Key Endpoints

**Serve Attempts**: `/v0/serve-attempts/*` (CRUD + list by user)

**Analysis**: `POST /v0/analysis/videos/{id}` (pose detection), `POST /v0/videos/{id}/analyze-serves` (serve analysis)

**Videos**: Upload, list, get, stream, analysis-status

**Players**: `/v0/players/*` (kept for future frontend work)

## Design Principles

- **Keep it simple**: Fewer moving parts, fewer features, fewer docs
- **Fast iteration**: Optimize for learning, not perfection
- **Layman terms**: Prefer "outstretched arm" over raw angles in UI
- **Legible metrics**: Explain why metrics matter, not just what they are
- **One recommendation**: Focus on high-leverage improvements, not 10 suggestions
