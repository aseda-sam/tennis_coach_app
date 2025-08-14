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

## Indexes

### Videos Table
- `ix_videos_id` - Primary key index
- `ix_videos_filename` - Unique filename index

### Analyses Table
- `ix_analyses_id` - Primary key index
- `ix_analyses_video_id` - Foreign key index
- `ix_analyses_video_filename` - Filename lookup index

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
