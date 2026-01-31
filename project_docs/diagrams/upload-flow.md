# Upload flow

What happens when you upload a video: we check the file, save it, save info about it, and optionally start pose detection. Solid = request; dashed = reply. Stored = saved in the database.

```mermaid
%%{init: {'theme':'base', 'themeVariables': {'primaryColor':'#fff8e1', 'primaryBorderColor':'#ff8f00'} }%%
sequenceDiagram
  participant Client
  participant API as POST /v0/videos/upload
  participant Storage as Save files
  participant DB as Database
  participant RQ as Job queue
  participant Worker as Background worker

  Client->>API: Video file + optional info (session, camera angle, …)
  API->>API: Check file and limits
  API->>Storage: Save file (disk or cloud)
  Storage-->>API: path where saved
  API->>API: Read video info (length, fps, size)
  API->>DB: Save video info
  alt AUTO_ENQUEUE_ON_UPLOAD
    API->>DB: Create job (queued)
    API->>RQ: Queue pose-detection job
    RQ-->>Worker: Run pose detection
    Worker->>Storage: Get file (temp if cloud)
    Worker->>DB: Save pose data, update job
  end
  API-->>Client: Upload result (video id, etc.)
```

## Notes

- **Check file and limits** — File type, size, content type; after reading the file, we also check dimensions/fps. Daily upload limits and demo permission apply.
- **Save file** — Local disk or Supabase; we then read length/fps from the file (using a temp file when using cloud).
- **Stored in DB** — Video row in `videos`; if auto-enqueue is on, a row in `video_jobs` and pose output in `pose_detection`. If auto-enqueue is off, you still get the upload result and can start analysis later (e.g. POST analysis API).
