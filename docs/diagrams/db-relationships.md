# DB relationships

How the main pieces connect: one user has players and videos; videos have pose data, serve windows, and jobs; serve windows can be manual or auto-detected with workflow status. Conceptual only—see migrations for full schema.

## Relationship overview

```mermaid
erDiagram
  USER ||--o{ PLAYER : owns
  USER ||--o{ VIDEO : uploads
  USER ||--o{ VIDEO_JOB : runs
  USER ||--o{ SERVE_WINDOW : tags_or_reviews

  VIDEO ||--o{ POSE_DETECTION : has
  VIDEO ||--o{ SERVE_WINDOW : contains
  VIDEO ||--o{ VIDEO_JOB : queues

  PLAYER ||--o{ SERVE_WINDOW : for
```

## Tables and key properties

Same relationships with a few key fields per table (Mermaid allows attributes on entities). Omitted fields (e.g. timestamps, nullable columns) are in migrations.

```mermaid
erDiagram
  USER {
    string id "UUID from auth"
    string email
  }

  PLAYER {
    int id PK
    string name
    string dominant_hand
    float height_cm
    string age_group
    string gender
    string user_id FK
  }

  VIDEO {
    int id PK
    string filename
    string file_path
    float duration
    float fps
    string status
    string user_id FK
  }

  VIDEO_JOB {
    uuid id PK
    int video_id FK
    string user_id FK
    string job_type
    string status
  }

  POSE_DETECTION {
    int id PK
    int video_id FK
    int total_frames
    string status
    text pose_data
  }

  SERVE_WINDOW {
    int id PK
    int video_id FK
    int player_id FK
    float start_timestamp
    float end_timestamp
    float contact_timestamp
    string source
    string status
    float confidence
  }

  USER ||--o{ PLAYER : owns
  USER ||--o{ VIDEO : uploads
  USER ||--o{ VIDEO_JOB : runs
  USER ||--o{ SERVE_WINDOW : tags_or_reviews

  VIDEO ||--o{ POSE_DETECTION : has
  VIDEO ||--o{ SERVE_WINDOW : contains
  VIDEO ||--o{ VIDEO_JOB : queues

  PLAYER ||--o{ SERVE_WINDOW : for
```

## Notes

- **Relationship overview** — High-level only; no attributes. `||--o{` = one-to-many; `||--o|` = one-to-zero-or-one.
- **Tables and key properties** — Entity names match table names (`players`, `videos`, `video_jobs`, `serve_windows`, `pose_detections`). USER is conceptual (no table; id/email from auth). PK = primary key, FK = foreign key; key fields listed for comprehension only.
- **source/status** on SERVE_WINDOW — `source` is `auto` (auto-detected) or `manual`. Auto-detected windows are saved directly as accepted; `status` field exists in the schema but the review workflow (pending → accepted/rejected) is no longer surfaced in the UI.
