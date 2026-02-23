# Analysis pipeline

From video to biomechanics: every upload is transcoded to 720p/30fps H.264, then a two-pass pose pipeline (scout → detect windows → refine), then serve windows are auto-detected and saved; biomechanics reports are computed lazily when requested. Stored = saved in the database.

```mermaid
flowchart TD
  V[Video uploaded] --> T[Transcode to 720p/30fps H.264]
  T --> SCOUT[Scout pass - MediaPipe Lite, every 4th frame]
  SCOUT --> DETECT[Detect serve windows]
  DETECT --> REFINE[Refine pass - MediaPipe Heavy, every frame in windows]
  REFINE --> POSE_DATA[Pose data stored]

  POSE_DATA --> AUTO[Auto-detect serve windows]
  AUTO --> SA[Serve windows saved]

  SA --> REPORT[Compute biomechanics report (lazy)]
  REPORT --> SUMMARY["Phases + raw metrics"]
```

## Notes

- **Transcode** — Every upload is transcoded to 720p/30fps H.264, giving pose detection a consistent input regardless of the original codec (AV1, VP9, HEVC, etc.) or resolution. This avoids OpenCV decoding failures and keeps frame processing fast.
- **Scout/refine** — Two different MediaPipe Pose Landmarker model weights (same 33 keypoints, different accuracy/speed). Scout uses `pose_landmarker_lite` on every 4th frame (~15fps) to quickly find serve windows. Refine uses `pose_landmarker_heavy` on every frame within those windows for maximum accuracy. Resulting pose data is merged and stored.
- **Serve windows** — Auto-detected from pose data and saved directly. If detection misses a serve, re-detection can be triggered from the UI.
- **Stored** — Pose data → `pose_detections` table (detection_mode: scout or refine); serve windows → `serve_windows` table (one row per window).
- **Biomechanics report** — Uses pose data and serve windows to compute phases + metrics (elbow angle at contact, knee flexion min, etc.) on first request. Selects best pose detection (refine > full > scout).
