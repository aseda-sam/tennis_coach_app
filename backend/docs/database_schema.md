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
- `primary_player_id` (FK -> `players.id`, nullable)
  - Default player attribution for serves created from this video.
  - Used when a serve attempt or proposal acceptance does not specify `player_id`.
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

Stores YOLO ball detection results for a video (serve windows only).

- `id` (PK)
- `video_id` (FK -> `videos.id`, CASCADE)
- `total_frames`, `frames_with_ball`, `detection_rate`
- `ball_data` (JSON text: list of per-frame detections with frame_index, timestamp_ms, ball_x, ball_y, confidence)
- `processing_time_seconds`, `frame_processing_rate`
- `status`, `error_message`
- `time_windows` (JSON: [{"start_ms", "end_ms"}, ...])
- `created_at`, `completed_at`

## serve_attempts

Stores serve attempts and metrics derived from video analysis.

- `id` (PK)
- `video_id` (FK -> `videos.id`)
- `user_id` (owner)
- `player_id` (FK -> `players.id`, required)
- `start_timestamp`, `end_timestamp`, `contact_timestamp`
- `analysis_version`, `elbow_angle_at_contact`, `knee_bend_*`, `court_side`,
  `serve_number`, `serve_subtype`, `in_out`
- `toss_peak_height` (nullable, from ball detection; normalized by player height)
- `toss_peak_timestamp` (nullable, video time in seconds)
- `source_proposal_id` (FK -> `serve_window_proposals.id`, nullable, indexed)
