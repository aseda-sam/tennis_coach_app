# Analysis pipeline

From video to serve analysis: we optionally transcode, run a two-pass pose pipeline (scout → detect windows → refine), then serve windows come from suggestions or from you; finally we run serve analysis and get a summary. Stored = saved in the database.

```mermaid
flowchart TD
  V[Video uploaded] --> TRANSCODE{file >= 20MB?}
  TRANSCODE -->|Yes| T[Transcode to 720p/30fps]
  TRANSCODE -->|No| SCOUT[Scout pass - lite model]
  T --> SCOUT
  SCOUT --> DETECT[Detect serve windows]
  DETECT --> REFINE[Refine pass - full model on windows]
  REFINE --> POSE_DATA[Pose data stored]

  V --> MANUAL[Add serve window manually]
  POSE_DATA --> PROPOSE[Suggest serve windows]
  PROPOSE --> REVIEW{You review suggestions}
  REVIEW -->|Accept or edit| SA[Serve windows saved]
  REVIEW -->|Reject| REJ[Suggestion discarded]

  MANUAL --> SA
  SA --> ANALYZE[Run serve analysis]
  ANALYZE --> SUMMARY["Summary (e.g. elbow angle)"]
```

## Notes

- **Transcode** — Large uploads (≥ 20MB) are transcoded first; smaller files go straight to scout.
- **Scout/refine** — Scout pass uses a lite pose model and frame skip to find serve windows; refine pass runs the full model only on those windows. Resulting pose data is stored (scout + refine records).
- **Serve windows** — Either (1) we suggest windows from pose data and you accept/edit, or (2) you add a window yourself (start/end time) without using suggestions.
- **Stored** — Pose data → `pose_detections` table (detection_mode: scout or refine); serve windows → `serve_attempts` table (one row per window; source can be manual or from a proposal).
- **Serve analysis** — Uses pose data and serve windows to compute metrics (e.g. elbow angle at contact) and return a summary.
