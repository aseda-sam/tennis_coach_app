# Database Schema Documentation

## Overview

The Tennis Coach App uses SQLite as its database with SQLAlchemy ORM for data modeling. The database stores video metadata, analysis results, and processing status information.

## Database Location

- **Development**: `data/database/tennis_coach.db`
- **Production**: Configured via `DATABASE_URL` environment variable

## Tables

### Videos Table

Stores metadata for uploaded tennis videos.

```sql
CREATE TABLE videos (
    id INTEGER PRIMARY KEY,
    filename VARCHAR(255) NOT NULL,
    file_path VARCHAR(500) NOT NULL,
    file_size INTEGER NOT NULL,
    content_type VARCHAR(100),
    duration FLOAT,
    fps FLOAT,
    width INTEGER,
    height INTEGER,
    frame_count INTEGER,
    status VARCHAR(50),
    error_message TEXT,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME
);
```

**Key Fields:**

- `id` - Unique video identifier (Primary Key)
- `filename` - Original uploaded filename
- `file_path` - Storage location on filesystem
- `file_size` - File size in bytes
- `content_type` - MIME type (e.g., "video/mp4")
- `duration` - Video length in seconds
- `fps` - Frames per second
- `width` / `height` - Video dimensions in pixels
- `frame_count` - Total number of frames
- `status` - Processing status (uploaded, processing, completed, failed)
- `error_message` - Error details if processing failed
- `created_at` - Upload timestamp
- `updated_at` - Last modification timestamp

### Ball Contacts Table

Stores ball contact detection data for tennis videos. This table tracks when the ball makes contact with the player's racket or hand, including both automated and manual detections.

```sql
CREATE TABLE ball_contacts (
    id INTEGER PRIMARY KEY,
    frame_number INTEGER,
    video_timestamp FLOAT NOT NULL,
    player INTEGER,
    contact_hand VARCHAR(10),  -- 'left' or 'right'
    stroke_type VARCHAR,       -- 'ground_stroke', 'serve', 'volley', 'overhead'
    stroke_subtype VARCHAR,    -- 'topspin', 'backspin', 'forehand', 'backhand', 'flat', 'slice', 'lob', 'drop'
    confidence FLOAT,
    ball_position VARCHAR,     -- JSON: {"x": 0.5, "y": 0.3}
    player_position VARCHAR,   -- JSON: {"x": 0.5, "y": 0.3}
    description VARCHAR,
    detection_source VARCHAR(20) NOT NULL DEFAULT 'automated',  -- 'automated' or 'manual'
    ball_area FLOAT,
    ball_size_factor FLOAT,
    racket_data VARCHAR,
    ball_bbox VARCHAR,
    ball_racket_distance FLOAT,
    video_id INTEGER NOT NULL,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME,
    FOREIGN KEY(video_id) REFERENCES videos (id) ON DELETE CASCADE
);
```

**Key Fields:**

- `id` - Unique ball contact identifier (Primary Key)
- `frame_number` - Frame index in the video (nullable)
- `video_timestamp` - Timestamp in seconds when contact occurred (NOT NULL)
- `player` - Player identifier (nullable)
- `contact_hand` - Hand used for contact ('left' or 'right')
- `stroke_type` - Type of stroke (ground_stroke, serve, volley, overhead)
- `stroke_subtype` - Subtype of stroke (topspin, backspin, forehand, backhand, flat, slice, lob, drop)
- `confidence` - Detection confidence score (0.0 to 1.0)
- `ball_position` - JSON string of ball coordinates
- `player_position` - JSON string of player position data
- `description` - Additional description or notes
- `detection_source` - Source of detection ('automated' or 'manual')
- `ball_area` - Area of detected ball in pixels
- `ball_size_factor` - Size factor of the ball
- `racket_data` - JSON string of racket detection data
- `ball_bbox` - JSON string of ball bounding box coordinates
- `ball_racket_distance` - Distance between ball and racket in pixels
- `video_id` - Reference to videos table (Foreign Key, NOT NULL)
- `created_at` - Contact detection timestamp
- `updated_at` - Last modification timestamp

### Analyses Table

Stores analysis results and processing metadata.

```sql
CREATE TABLE analyses (
    id INTEGER PRIMARY KEY,
    video_id INTEGER,
    video_filename VARCHAR NOT NULL,
    analysis_type VARCHAR NOT NULL,
    total_frames INTEGER,
    frames_with_balls INTEGER,
    total_ball_detections INTEGER,
    average_detections_per_frame FLOAT,
    detection_rate FLOAT,
    frames_with_pose INTEGER,
    pose_detection_rate FLOAT,
    ball_detections TEXT,
    pose_detections TEXT,
    annotated_video_path VARCHAR,
    processing_time FLOAT,
    model_used VARCHAR,
    confidence_threshold FLOAT,
    status VARCHAR(50),
    progress INTEGER,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME,
    completed_at DATETIME,
    FOREIGN KEY(video_id) REFERENCES videos (id)
);
```

**Key Fields:**

- `id` - Unique analysis identifier (Primary Key)
- `video_id` - Reference to videos table (Foreign Key)
- `video_filename` - Original video filename
- `analysis_type` - Type of analysis (ball_tracking, pose_estimation, comprehensive)
- `status` - Processing status (processing, completed, failed)
- `progress` - Completion percentage (0-100)
- `total_frames` - Total frames in video
- `frames_with_balls` - Frames containing ball detections
- `total_ball_detections` - Total ball detections found
- `detection_rate` - Percentage of frames with detections
- `frames_with_pose` - Frames with pose detections
- `pose_detection_rate` - Percentage of frames with pose data
- `ball_detections` - JSON string of ball detection coordinates
- `pose_detections` - JSON string of pose keypoint data
- `annotated_video_path` - Path to annotated video file
- `processing_time` - Analysis duration in seconds
- `model_used` - YOLO model version (e.g., "yolov8n")
- `confidence_threshold` - Detection confidence threshold
- `created_at` - Analysis creation timestamp
- `updated_at` - Last modification timestamp
- `completed_at` - Analysis completion timestamp (nullable)

## Relationships

### One-to-Many: Videos to Analyses

- One video can have multiple analyses
- Each analysis belongs to one video
- Foreign key: `analyses.video_id` → `videos.id`

### One-to-Many: Videos to Ball Contacts

- One video can have multiple ball contacts
- Each ball contact belongs to one video
- Foreign key: `ball_contacts.video_id` → `videos.id`
- Cascade delete: When a video is deleted, all associated ball contacts are also deleted

## Indexes

### Videos Table

- `ix_videos_id` - Primary key index
- `ix_videos_filename` - Unique filename index

### Analyses Table

- `ix_analyses_id` - Primary key index
- `ix_analyses_video_id` - Foreign key index
- `ix_analyses_video_filename` - Filename lookup index

### Ball Contacts Table

- `ix_ball_contacts_id` - Primary key index
- `ix_ball_contacts_video_id` - Foreign key index
- `ix_ball_contacts_frame_number` - Frame number lookup index

## Data Types

### Status Values

**Video Status:**

- `uploaded` - File uploaded successfully
- `processing` - Currently being processed
- `completed` - Processing finished successfully
- `failed` - Processing encountered an error

**Analysis Status:**

- `processing` - Analysis is currently running
- `completed` - Analysis finished successfully
- `failed` - Analysis encountered an error

### Analysis Types

- `ball_tracking` - Ball detection only
- `pose_estimation` - Pose detection only
- `comprehensive` - Both ball and pose detection

### Ball Contact Data Types

**Contact Hand Values:**

- `left` - Left hand contact
- `right` - Right hand contact

**Stroke Type Values:**

- `ground_stroke` - Ground stroke (forehand/backhand)
- `serve` - Serve
- `volley` - Volley
- `overhead` - Overhead/smash

**Stroke Subtype Values:**

- `topspin` - Topspin shot
- `backspin` - Backspin/slice
- `forehand` - Forehand stroke
- `backhand` - Backhand stroke
- `flat` - Flat shot
- `slice` - Slice shot
- `lob` - Lob shot
- `drop` - Drop shot

**Detection Source Values:**

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

## Future Considerations

- **PostgreSQL Migration**: For production deployments with multiple users
- **Data Archiving**: Strategy for old analysis data
- **Compression**: JSON field compression for large datasets
- **Partitioning**: Time-based partitioning for large datasets
