# Analysis pipeline

From video to serve analysis: we get pose data, then serve windows (from suggestions or from you drawing them), then we run analysis and get a summary. Stored = saved in the database.

```mermaid
flowchart TD
  V[Video uploaded] --> POSE[Pose detection job]
  V --> MANUAL[Add serve window manually]
  POSE --> POSE_DATA[Pose data stored]

  POSE_DATA --> PROPOSE[Suggest serve windows]
  PROPOSE --> REVIEW{You review suggestions}
  REVIEW -->|Accept or edit| SA[Serve windows saved]
  REVIEW -->|Reject| REJ[Suggestion discarded]

  MANUAL --> SA
  SA --> ANALYZE[Run serve analysis]
  ANALYZE --> SUMMARY["Summary (e.g. elbow angle)"]
```

## Notes

- **Serve windows** — Either (1) we suggest windows from pose data and you accept/edit, or (2) you add a window yourself (start/end time) without using suggestions.
- **Stored** — Pose data → `pose_detection` table; serve windows → `serve_attempts` table (one row per window; source can be manual or from a proposal).
- **Serve analysis** — Uses pose data and serve windows to compute metrics (e.g. elbow angle at contact) and return a summary.
