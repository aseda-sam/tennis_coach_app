# Database Schema Documentation

## Overview

The Tennis Coach App uses SQLite as its database with SQLAlchemy ORM for data modeling. The database stores video metadata, pose analysis results, player information, and serve attempt data.

**Source of Truth:** All table definitions are in `app/models/` - this documentation provides a high-level overview.

## Database Location

- **Development**: `data/database/tennis_coach.db`
- **Production**: Configured via `DATABASE_URL` environment variable

## Current Schema (6 Tables)

The database consists of 6 main tables that support serve-focused tennis video analysis and player management.

## Database Relationships Overview

**Core Entity:** Videos (central hub for all analysis data)

**Analysis Tables:** Pose Detections, Video Annotations (one per video)
**Association Table:** VideoPlayer (many-to-many between Videos and Players)  
**Event Table:** Serve Attempts (many per video, linked to players)

### Relationship Summary

- **Videos** → **Pose Detections** (1:1) - One analysis per video
- **Videos** → **Video Annotations** (1:many) - Multiple annotation styles
- **Videos** → **Serve Attempts** (1:many) - Multiple serve attempts per video
- **Videos** ↔ **Players** (many:many via VideoPlayer) - Multiple players per video
- **Players** → **Serve Attempts** (1:many) - Player's serve attempts across videos

## Table Overview

### 1. Videos Table

**Model:** `app.models.video.Video`

Stores metadata for uploaded tennis videos including file information, processing status, and session metadata.

**Key Fields:**

- `id` - Unique video identifier (Primary Key)
- `filename` - Original uploaded filename (Unique)
- `file_path` - Storage location on filesystem
- `file_size` - File size in bytes
- `duration` - Video length in seconds
- `fps` - Frames per second
- `width` / `height` - Video dimensions in pixels
- `status` - Processing status (uploaded, processing, completed, failed)
- `user_id` - UUID of the user who owns this video (required)
- `is_demo` - Boolean flag indicating if this is a demo video (readable by all authenticated users)
- `is_active_demo` - Boolean flag indicating if this is the currently active demo video (only one should be active at a time)
- `original_user_id` - Original user_id before promotion to demo (for restore purposes)
- `session_type` - Type of session ('serve_drill', 'match', 'practice', 'other')
- `camera_angle` - Camera angle ('behind', 'profile', 'diagonal', 'unknown')
- `recorded_at` - When video was recorded (for trends)

### 2. Players Table

**Model:** `app.models.player.Player`

Stores player information and attributes for tracking individual players across multiple videos.

**Key Fields:**

- `id` - Unique player identifier (Primary Key)
- `name` - Player name
- `dominant_hand` - Hand typically used for hitting ('left' or 'right')
- `backhand_style` - Backhand technique ('one_handed' or 'two_handed')
- `notes` - Additional player information
- `user_id` - UUID of the user who owns this player (required)

### 3. VideoPlayer Junction Table

**Model:** `app.models.video_player.VideoPlayer`

Associates players with specific videos (many-to-many relationship). Prevents duplicate associations.

**Key Fields:**

- `id` - Unique association identifier (Primary Key)
- `video_id` - Reference to videos table (Foreign Key)
- `player_id` - Reference to players table (Foreign Key)
- `pose_detection_id` - Optional reference to pose detection data
- **Unique Constraint**: Prevents duplicate video-player associations

### 4. Serve Attempts Table

**Model:** `app.models.serve_attempt.ServeAttempt`

Stores manually-tagged serve attempts with timing and calculated metrics.

**Key Fields:**

- `id` - Unique serve attempt identifier (Primary Key)
- `video_id` - Reference to videos table (Foreign Key)
- `user_id` - UUID of the user who owns this serve attempt (required)
- `player_id` - Reference to players table (Foreign Key, required)
- `start_timestamp` - When serve attempt starts (seconds)
- `end_timestamp` - When serve attempt ends (seconds)
- `contact_timestamp` - Optional timestamp when ball contact occurred
- `elbow_angle_at_contact` - Calculated elbow angle at contact point (degrees)
- `court_side` - Court side ('deuce', 'ad')
- `serve_number` - Serve number (1, 2)
- `serve_subtype` - Serve type ('flat', 'slice', 'kick')
- `in_out` - Outcome ('in', 'out_long', 'out_wide', 'net', 'unknown')
- `created_at` - When serve attempt was created

### 5. Pose Detections Table

**Model:** `app.models.pose_detection.PoseDetection`

Stores pose detection analysis results and keypoint data.

**Key Fields:**

- `id` - Unique pose detection identifier (Primary Key)
- `video_id` - Reference to videos table (Foreign Key)
- `total_frames` - Total frames processed
- `frames_with_poses` - Frames containing pose detections
- `detection_rate` - Percentage of frames with pose data
- `pose_data` - JSON string of pose keypoint data
- `pose_stability_score` - Overall pose detection stability
- `annotated_video_path` - Path to annotated video file
- `status` - Processing status (processing, completed, failed)

### 6. Video Annotations Table

**Model:** `app.models.video_annotation.VideoAnnotation`

Stores video annotation processing results and metadata.

**Key Fields:**

- `id` - Unique annotation identifier (Primary Key)
- `video_id` - Reference to videos table (Foreign Key)
- `annotation_type` - Type of annotation applied
- `annotated_video_path` - Path to annotated video file
- `file_size_bytes` - Size of annotated video file
- `frames_annotated` - Number of frames processed
- `annotation_style` - Style of annotation applied

## Relationships

### One-to-Many Relationships

**Videos → Serve Attempts**

- One video can have multiple serve attempts
- Cascade delete: When video is deleted, all serve attempts are deleted

**Videos → Pose Detections**

- One video can have one pose detection analysis
- Cascade delete: When video is deleted, pose detection is deleted

**Videos → Video Annotations**

- One video can have multiple annotations
- Cascade delete: When video is deleted, annotations are deleted

**Players → Serve Attempts**

- One player can have multiple serve attempts across videos
- Set null on delete: When player is deleted, serve attempts remain but player_id is set to null

### Many-to-Many Relationships

**Videos ↔ Players (via VideoPlayer)**

- Many videos can have many players
- Many players can appear in many videos
- Junction table: `video_players`
- Unique constraint prevents duplicate associations

## Data Types and Enums

### Video Status Values

- `uploaded` - File uploaded successfully
- `processing` - Currently being processed
- `completed` - Processing finished successfully
- `failed` - Processing encountered an error

### Analysis Status Values

- `processing` - Analysis is currently running
- `completed` - Analysis finished successfully
- `failed` - Analysis encountered an error

### Player Hand Values

- `left` - Left-handed player
- `right` - Right-handed player

### Backhand Style Values

- `one_handed` - One-handed backhand
- `two_handed` - Two-handed backhand

### Session Type Values

- `serve_drill` - Serve practice session
- `match` - Match play
- `practice` - General practice
- `other` - Other session type

### Camera Angle Values

- `behind` - Camera behind player
- `profile` - Camera to the side
- `diagonal` - Camera at diagonal angle
- `unknown` - Unknown camera angle

### Serve Subtype Values

- `flat` - Flat serve
- `slice` - Slice serve
- `kick` - Kick/topspin serve

### Serve Outcome Values

- `in` - Serve landed in
- `out_long` - Serve went long
- `out_wide` - Serve went wide
- `net` - Serve hit the net
- `unknown` - Unknown outcome

## Migration Management

The database uses Alembic for schema migrations:

```bash
# Apply all pending migrations
alembic upgrade head

# Create new migration
alembic revision --autogenerate -m "Description"

# View migration history
alembic history

# Downgrade to previous version
alembic downgrade -1
```

## Backup and Recovery

### Backup

```bash
# Create backup
cp data/database/tennis_coach.db data/database/tennis_coach_backup.db

# With timestamp
cp data/database/tennis_coach.db "data/database/tennis_coach_$(date +%Y%m%d_%H%M%S).db"
```

### Recovery

```bash
# Restore from backup
cp data/database/tennis_coach_backup.db data/database/tennis_coach.db
```

## Performance Considerations

- **File Storage**: Videos are stored on filesystem, not in database
- **JSON Fields**: Large detection data stored as JSON strings
- **Indexes**: Foreign keys and frequently queried fields are indexed
- **SQLite**: Suitable for development and small to medium deployments
- **Unique Constraints**: Prevent duplicate data and ensure data integrity

## Future Considerations

- **PostgreSQL Migration**: For production deployments with multiple users
- **Data Archiving**: Strategy for old analysis data
- **Compression**: JSON field compression for large datasets
- **Partitioning**: Time-based partitioning for large datasets
- **Player Analytics**: Enhanced player-specific performance tracking
