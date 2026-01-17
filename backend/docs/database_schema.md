# Database Schema Documentation

## Overview

The Tennis Coach App uses SQLite as its database with SQLAlchemy ORM for data modeling. The database stores video metadata, analysis results, player information, and processing status information.

**Source of Truth:** All table definitions are in `app/models/` - this documentation provides a high-level overview.

## Database Location

- **Development**: `data/database/tennis_coach.db`
- **Production**: Configured via `DATABASE_URL` environment variable

## Current Schema (7 Tables)

The database consists of 7 main tables that support comprehensive tennis video analysis and player management.

## Database Relationships Overview

**Core Entity:** Videos (central hub for all analysis data)

**Analysis Tables:** Ball Detections, Pose Detections, Video Annotations (one per video)
**Association Table:** VideoPlayer (many-to-many between Videos and Players)  
**Event Table:** Ball Contacts (many per video, optionally linked to players)

### Relationship Summary

- **Videos** → **Ball Detections** (1:1) - One analysis per video
- **Videos** → **Pose Detections** (1:1) - One analysis per video
- **Videos** → **Video Annotations** (1:many) - Multiple annotation styles
- **Videos** → **Ball Contacts** (1:many) - Multiple contact events
- **Videos** ↔ **Players** (many:many via VideoPlayer) - Multiple players per video
- **Players** → **Ball Contacts** (1:many) - Player's contact events across videos

## Table Overview

### 1. Videos Table

**Model:** `app.models.video.Video`

Stores metadata for uploaded tennis videos including file information, processing status, and quality assessments.

**Key Fields:**

- `id` - Unique video identifier (Primary Key)
- `filename` - Original uploaded filename (Unique)
- `file_path` - Storage location on filesystem
- `file_size` - File size in bytes
- `duration` - Video length in seconds
- `fps` - Frames per second
- `width` / `height` - Video dimensions in pixels
- `status` - Processing status (uploaded, processing, completed, failed)
- `quality_score` - Overall video quality assessment
- `quality_level` - Quality rating (excellent, good, fair, poor)
- `user_id` - UUID of the user who owns this video (required)
- `is_demo` - Boolean flag indicating if this is a demo video (readable by all authenticated users)
- `is_active_demo` - Boolean flag indicating if this is the currently active demo video (only one should be active at a time)
- `original_user_id` - Original user_id before promotion to demo (for restore purposes)

### 2. Players Table

**Model:** `app.models.player.Player`

Stores player information and attributes for tracking individual players across multiple videos.

**Key Fields:**

- `id` - Unique player identifier (Primary Key)
- `name` - Player name
- `dominant_hand` - Hand typically used for hitting ('left' or 'right')
- `backhand_style` - Backhand technique ('one_handed' or 'two_handed')
- `height` - Player height in centimeters
- `notes` - Additional player information

### 3. VideoPlayer Junction Table

**Model:** `app.models.video_player.VideoPlayer`

Associates players with specific videos (many-to-many relationship). Prevents duplicate associations.

**Key Fields:**

- `id` - Unique association identifier (Primary Key)
- `video_id` - Reference to videos table (Foreign Key)
- `player_id` - Reference to players table (Foreign Key)
- `pose_detection_id` - Optional reference to pose detection data
- **Unique Constraint**: Prevents duplicate video-player associations

### 4. Ball Contacts Table

**Model:** `app.models.ball_contact.BallContact`

Stores ball contact detection data for tennis videos, including both automated and manual detections.

**Key Fields:**

- `id` - Unique ball contact identifier (Primary Key)
- `frame_number` - Frame index in the video
- `video_timestamp` - Timestamp in seconds when contact occurred
- `contact_hand` - Hand used for contact ('left' or 'right')
- `stroke_type` - Type of stroke (ground_stroke, serve, return, volley, overhead)
- `stroke_subtype` - Subtype of stroke (must be valid for the selected stroke_type)
- `detection_source` - Source of detection ('automated' or 'manual')
- `elbow_angle` - Elbow angle measurement for posture analysis
- `video_id` - Reference to videos table (Foreign Key)
- `player_id` - Reference to players table (Foreign Key, nullable)

### 5. Ball Detections Table

**Model:** `app.models.ball_detection.BallDetection`

Stores ball detection analysis results and processing metadata.

**Key Fields:**

- `id` - Unique detection identifier (Primary Key)
- `video_id` - Reference to videos table (Foreign Key)
- `total_frames` - Total frames processed
- `frames_with_balls` - Frames containing ball detections
- `detection_rate` - Percentage of frames with detections
- `model_used` - YOLO model version used
- `confidence_threshold` - Detection confidence threshold
- `detection_data` - JSON string of ball detection coordinates
- `processing_time_seconds` - Analysis duration

### 6. Pose Detections Table

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

### 7. Video Annotations Table

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

**Videos → Ball Contacts**

- One video can have multiple ball contacts
- Cascade delete: When video is deleted, all ball contacts are deleted

**Videos → Ball Detections**

- One video can have one ball detection analysis
- Cascade delete: When video is deleted, ball detection is deleted

**Videos → Pose Detections**

- One video can have one pose detection analysis
- Cascade delete: When video is deleted, pose detection is deleted

**Videos → Video Annotations**

- One video can have multiple annotations
- Cascade delete: When video is deleted, annotations are deleted

**Players → Ball Contacts**

- One player can have multiple ball contacts
- Set null on delete: When player is deleted, ball contacts remain but player_id is set to null

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

### Contact Hand Values

- `left` - Left hand contact
- `right` - Right hand contact

### Stroke Type Values

- `ground_stroke` - Ground stroke (forehand/backhand)
- `serve` - Serve
- `return` - Return of serve
- `volley` - Volley
- `overhead` - Overhead/smash

### Stroke Subtype Values

Subtypes are validated against their stroke type. Valid combinations include:

**Ground Strokes:**
- `forehand_flat`, `forehand_topspin`, `forehand_slice`
- `backhand_flat`, `backhand_topspin`, `backhand_slice`
- `drop_shot`, `lob`

**Serves:**
- `flat`, `topspin_kick`, `slice`, `underarm`

**Returns:**
- `forehand`, `backhand`

**Volleys:**
- `forehand`, `backhand`, `drop`, `half`

**Overhead:**
- `smash`

### Detection Source Values

- `automated` - Automatically detected by AI
- `manual` - Manually added by user

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

### Clean Migration Process (for future use)

When you need to create a fresh migration:

```bash
# 1. Backup current database
cp data/database/tennis_coach.db data/database/tennis_coach_backup_$(date +%Y%m%d_%H%M%S).db

# 2. Remove all existing migrations
rm -rf backend/alembic/versions/*.py

# 3. Remove current database
rm -f data/database/tennis_coach.db

# 4. Ensure all models are imported in alembic/env.py

# 5. Generate fresh migration
cd backend && alembic revision --autogenerate -m "initial_schema_with_all_tables"

# 6. Apply migration
alembic upgrade head

# 7. Test app startup
python -c "from app.main import app; print('Success!')"
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
