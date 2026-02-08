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

## players

Stores player profiles (one default per user, with optional additional players).

- `id` (PK)
- `user_id` (owner)
- `name` (required)
- `dominant_hand` (required)
- `backhand_style`, `height_cm`, `age_group`, `gender`, `notes`

## serve_attempts

Stores serve attempts and metrics derived from video analysis.

- `id` (PK)
- `video_id` (FK -> `videos.id`)
- `user_id` (owner)
- `player_id` (FK -> `players.id`, required)
- `start_timestamp`, `end_timestamp`, `contact_timestamp`
- `analysis_version`, `elbow_angle_at_contact`, `knee_bend_*`, `court_side`,
  `serve_number`, `serve_subtype`, `in_out`
