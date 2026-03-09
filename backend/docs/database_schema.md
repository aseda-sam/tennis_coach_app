# Database Schema (Selected Tables)

This document summarizes the core tables and fields used by the API. It is not
an exhaustive list of every column, but highlights fields that affect behavior
and feature contracts.

## videos

Stores uploaded videos and metadata.

- `id` (PK)
- `user_id` (owner)
- `filename`, `file_path`, `file_size`, `content_type`
- `duration`, `fps`, `width`, `height`, `frame_count`
- `status`, `error_message`
- `is_demo`, `is_active_demo`, `original_user_id`
- `session_type`, `camera_angle`, `recorded_at`
- `title VARCHAR(200)` (nullable) — user-defined label; fallback to filename in UI
- `notes TEXT` (nullable) — free-form session memo
- `primary_player_id` (FK -> `players.id`, nullable)
  - Default player attribution for serves created from this video.
  - Used when a serve window or proposal acceptance does not specify `player_id`.
- Indexes used by timeline/progress queries:
  - `ix_videos_recorded_at` on `recorded_at`
  - `ix_videos_user_recorded_at` on (`user_id`, `recorded_at`)

## players

Stores player profiles (one default per user, with optional additional players).

- `id` (PK)
- `user_id` (owner)
- `name` (required)
- `dominant_hand` (required)
- `backhand_style`, `height_cm`, `age_group`, `gender`, `notes`

## ball_detections

Stores ball detection results for a video (serve windows only). Uses YOLO + ByteTrack.

- `id` (PK)
- `video_id` (FK -> `videos.id`, CASCADE)
- `total_frames`, `frames_with_ball`, `detection_rate`
- `ball_data` (JSON text: list of per-frame detections with frame_index, timestamp_ms, ball_x, ball_y, confidence, interpolated)
  - `interpolated: bool` — True if position was filled by cubic spline post-processing
- `processing_time_seconds`, `frame_processing_rate`
- `status`, `error_message`
- `time_windows` (JSON: [{"start_ms", "end_ms"}, ...])
- `created_at`, `completed_at`

## serve_windows

Stores serve windows (manual or auto-detected) and review metadata.

- `id` (PK)
- `video_id` (FK -> `videos.id`)
- `user_id` (owner)
- `player_id` (FK -> `players.id`, nullable while pending)
- `start_timestamp`, `end_timestamp`, `contact_timestamp`, `contact_source`
  - `contact_source`: `"manual"` (user-tagged via API) or `"auto"` (set by ball detection pipeline or lazy fallback). Legacy rows with `contact_timestamp` were backfilled to `"auto"` in migration `2cf2e7b95cd1`.
- `court_side`, `serve_number`, `serve_subtype`, `in_out`
- `source` (`manual` or `auto`)
- `status` (`pending`, `accepted`, `rejected`, `edited`)
- `model_version`, `confidence`, `detection_features` (nullable; for auto detection)
- `reviewed_at`, `original_start_timestamp`, `original_end_timestamp`
- `is_active` (Boolean, NOT NULL, DEFAULT TRUE) — `False` when this window has been superseded by a split operation. All listing queries filter by `is_active = True`.
- `parent_window_id` (FK -> `serve_windows.id`, nullable, ON DELETE SET NULL) — set on child windows created by a split; `None` for original/manually-created windows.
- Indexes:
  - `ix_serve_windows_video_active` on (`video_id`, `is_active`) — for active-window queries

## serve_biomechanics_reports

Computed phase segmentation and raw biomechanics metrics for a single serve
window. Separate from `serve_windows` because it's a computed artifact.
No scoring, ratings, or coaching text — phases + metrics only.

- `id` (PK)
- `serve_window_id` (FK -> `serve_windows.id`, CASCADE)
- `user_id` (owner)
- `player_id` (FK -> `players.id`, CASCADE)
- `phase_segmentation_json` (TEXT, JSON-serialized phase boundaries + moment markers; `phase-seg-v5` uses 3 phases: toss_and_load, acceleration, follow_through)
- `metrics` (JSONB, nested by phase: `{"toss_and_load": {"knee_flexion_min_deg": 95.5, "toss_peak_height": 1.8, "toss_drop": 0.25}}`)
- `analysis_version`
- `created_at`
- Indexes:
  - `ix_biomechanics_reports_player_created` on (`player_id`, `created_at`)
  - `ix_biomechanics_reports_user_player` on (`user_id`, `player_id`)
