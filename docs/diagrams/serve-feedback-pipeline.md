# Serve biomechanics pipeline

From serve window to phase segmentation and raw metrics. Triggered lazily on the
first GET request for biomechanics, not during the analysis pipeline. No scoring
or coaching — phases + metrics only.

```mermaid
flowchart TD
  REQ["GET /serve-windows/{id}/biomechanics"] --> CACHE{Cached report?}
  CACHE -->|Yes| RET[Return stored report]
  CACHE -->|No| LOAD[Load serve window + video + player + pose data]

  LOAD --> FRAMES["Extract pose frames in serve window"]

  FRAMES --> SEG["Phase segmentation (8 Kovacs stages)"]
  SEG --> SEG_OUT["PhaseSegmentationResult\n8 phases with timestamps + confidence"]

  FRAMES --> METRICS["Compute biomechanics metrics"]
  SEG_OUT --> METRICS
  METRICS --> MET_OUT["BiomechanicsMetrics\nknee flexion, elbow angle,\ncontact height, trunk rotation, etc."]

  MET_OUT --> STORE["Store ServeBiomechanicsReport\n(phase_segmentation_json + metrics_json)"]
  STORE --> RET

  subgraph seg_detail ["Phase Detection Heuristics"]
    S1["Start: first frame"]
    S2["Wind-up: toss arm rises above shoulder"]
    S3["Cocking: both arms raised (trophy position)"]
    S4["Loading: deepest knee bend (max knee-hip ratio)"]
    S5["Acceleration: wrist velocity > 2x mean"]
    S6["Contact: from tagged contact_timestamp"]
    S7["Deceleration: velocity drops < 50% peak"]
    S8["Finish: wrist drops below shoulder"]
    S1 --> S2 --> S3 --> S4 --> S5 --> S6 --> S7 --> S8
  end

  subgraph core_metrics ["Core Metrics (MVP)"]
    M1["knee_flexion_min_deg (loading)"]
    M2["elbow_angle_at_contact (contact)"]
    M3["contact_point_height (contact)"]
  end
```

## Data dependencies

| Input | Source | Table |
|-------|--------|-------|
| Serve window (start/end/contact) | User-tagged or auto-suggested | `serve_windows` |
| Pose keypoints per frame | MediaPipe (scout or refine pass) | `pose_detections` |
| Player dominant hand | User-entered | `players` |
| Video FPS and dimensions | From transcode metadata | `videos` |

## Output

| Field | Storage | Use |
|-------|---------|-----|
| Phase windows (8 stages) | `phase_segmentation_json` | Timeline UI |
| Raw metric values | `metrics_json` | Data table / charts |

## Key design decisions

- **Lazy computation**: Biomechanics computed on first request, not during pose pipeline.
  Avoids wasted work if user never views report.
- **Phases + metrics only**: No scoring, ratings, or coaching text. Focus on
  "identify phases, compute metrics at key moments."
- **Phase-independent knee flexion**: Knee flexion is searched from frame 0 to contact,
  not constrained to loading phase, because phase detection can miss loading.
