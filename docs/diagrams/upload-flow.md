# Upload flow

What happens when you upload a video: we check the file, save it, save info about it, and optionally start transcode and/or pose analysis (scout/refine pipeline). Solid = request; dashed = reply. Stored = saved in the database.

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
    API->>DB: Create job(s) (queued)
    alt file size >= 20MB
      API->>RQ: Queue transcode job
      RQ-->>Worker: Run transcode (720p, 30fps)
      Worker->>Storage: Get file, transcode, replace
      Worker->>DB: Update video (path, size), then queue scout/refine
      RQ-->>Worker: Run scout then refine (pose pipeline)
    else file size < 20MB
      API->>RQ: Queue scout/refine job
      RQ-->>Worker: Run scout then refine (pose pipeline)
    end
    Worker->>Storage: Get file (temp if cloud)
    Worker->>DB: Save pose data, update job (stage, etc.)
  end
  API-->>Client: Upload result (video id, etc.)
```

## Notes

- **Check file and limits** — File type, size, content type; after reading the file, we also check dimensions/fps. Daily upload limits and demo permission apply.
- **Save file** — Local disk or Supabase; we then read length/fps from the file (using a temp file when using cloud).
- **Transcode** — If file ≥ 20MB we transcode to 720p/30fps H.264 before analysis; smaller files skip transcode. Transcode job chains to scout/refine on completion.
- **Scout/refine** — Two-pass pose pipeline: scout (lite model, frame skip) → detect serve windows → refine (full model on windows only). Job stages (transcoding, scout, detecting_serves, refining, complete) are stored for UI progress.
- **Stored in DB** — Video row in `videos`; if auto-enqueue is on, rows in `video_jobs` and pose output in `pose_detections`. If auto-enqueue is off, you still get the upload result and can start analysis later (e.g. POST analysis API).
