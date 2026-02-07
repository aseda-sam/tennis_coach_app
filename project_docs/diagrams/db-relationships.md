# DB relationships

How the main pieces connect: one user has players and videos; videos have pose data, serve windows, and jobs; serve windows can come from suggestions or from you. Conceptual only—see migrations for full schema.

## Relationship overview

```mermaid
erDiagram
  USER ||--o{ PLAYER : owns
  USER ||--o{ VIDEO : uploads
  USER ||--o{ VIDEO_JOB : runs
  USER ||--o{ SERVE_ATTEMPT : tags
  USER ||--o{ SERVE_WINDOW_PROPOSAL : reviews

  VIDEO ||--o{ POSE_DETECTION : has
  VIDEO ||--o{ SERVE_ATTEMPT : contains
  VIDEO ||--o{ SERVE_WINDOW_PROPOSAL : generates
  VIDEO ||--o{ VIDEO_JOB : queues

  PLAYER ||--o{ SERVE_ATTEMPT : for
  SERVE_WINDOW_PROPOSAL ||--o| SERVE_ATTEMPT : source
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

  SERVE_WINDOW_PROPOSAL {
    int id PK
    int video_id FK
    float start_timestamp
    float end_timestamp
    string status
  }

  SERVE_ATTEMPT {
    int id PK
    int video_id FK
    int player_id FK
    float start_timestamp
    float end_timestamp
    float elbow_angle_at_contact
    bool knee_bend_detected
    float knee_bend_confidence
    float knee_hip_ratio_min
    string source
    int source_proposal_id FK
  }

  USER ||--o{ PLAYER : owns
  USER ||--o{ VIDEO : uploads
  USER ||--o{ VIDEO_JOB : runs
  USER ||--o{ SERVE_ATTEMPT : tags
  USER ||--o{ SERVE_WINDOW_PROPOSAL : reviews

  VIDEO ||--o{ POSE_DETECTION : has
  VIDEO ||--o{ SERVE_ATTEMPT : contains
  VIDEO ||--o{ SERVE_WINDOW_PROPOSAL : generates
  VIDEO ||--o{ VIDEO_JOB : queues

  PLAYER ||--o{ SERVE_ATTEMPT : for
  SERVE_WINDOW_PROPOSAL ||--o| SERVE_ATTEMPT : source
```

## Notes

- **Relationship overview** — High-level only; no attributes. `||--o{` = one-to-many; `||--o|` = one-to-zero-or-one.
- **Tables and key properties** — Entity names match table names (`players`, `videos`, `video_jobs`, `serve_attempts`, `serve_window_proposals`, `pose_detections`). USER is conceptual (no table; id/email from auth). PK = primary key, FK = foreign key; key fields listed for comprehension only.
- **source** on SERVE_ATTEMPT — A serve window can link to a proposal (accepted/edited suggestion) or be created manually (no proposal).
