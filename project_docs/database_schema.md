# Database Schema Documentation

## Overview

The tennis analysis system uses SQLite for the MVP with a well-structured schema designed for flexibility and performance. The schema supports storing video metadata, analysis results, and time-series data efficiently.

## Database Location
```
./data/database/tennis_analysis.db
```

## Schema Design

### 1. Videos Table
Stores video metadata and processing information.

```sql
CREATE TABLE videos (
    id TEXT PRIMARY KEY,  -- UUID string
    filename TEXT NOT NULL,
    original_filename TEXT NOT NULL,
    file_path TEXT NOT NULL,
    file_size INTEGER NOT NULL,  -- bytes
    duration REAL,  -- seconds
    format TEXT,
    resolution_width INTEGER,
    resolution_height INTEGER,
    fps REAL,
    upload_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    status TEXT DEFAULT 'uploaded',  -- uploaded, processing, completed, failed
    processing_start_time TIMESTAMP,
    processing_end_time TIMESTAMP,
    processing_duration REAL,  -- seconds
    error_message TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

**Indexes:**
```sql
CREATE INDEX idx_videos_status ON videos(status);
CREATE INDEX idx_videos_upload_date ON videos(upload_date);
```

### 2. Analysis Results Table
Stores main analysis data with JSON flexibility.

```sql
CREATE TABLE analysis_results (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    video_id TEXT NOT NULL,
    analysis_type TEXT NOT NULL,  -- ball_tracking, pose_estimation, stroke_detection
    frame_number INTEGER,
    timestamp REAL,  -- seconds from video start
    data JSON NOT NULL,  -- Flexible JSON storage
    confidence REAL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (video_id) REFERENCES videos(id) ON DELETE CASCADE
);
```

**Indexes:**
```sql
CREATE INDEX idx_analysis_video_id ON analysis_results(video_id);
CREATE INDEX idx_analysis_type ON analysis_results(analysis_type);
CREATE INDEX idx_analysis_timestamp ON analysis_results(timestamp);
```

### 3. Player Positions Table
Time-series data for player court positioning.

```sql
CREATE TABLE player_positions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    video_id TEXT NOT NULL,
    frame_number INTEGER NOT NULL,
    timestamp REAL NOT NULL,
    x_coordinate REAL,
    y_coordinate REAL,
    court_position TEXT,  -- baseline, service_line, net, etc.
    confidence REAL,
    pose_landmarks JSON,  -- MediaPipe pose data
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (video_id) REFERENCES videos(id) ON DELETE CASCADE
);
```

**Indexes:**
```sql
CREATE INDEX idx_positions_video_id ON player_positions(video_id);
CREATE INDEX idx_positions_timestamp ON player_positions(timestamp);
CREATE INDEX idx_positions_court_position ON player_positions(court_position);
```

### 4. Stroke Events Table
Stores detected stroke events with metadata.

```sql
CREATE TABLE stroke_events (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    video_id TEXT NOT NULL,
    frame_number INTEGER NOT NULL,
    timestamp REAL NOT NULL,
    stroke_type TEXT NOT NULL,  -- forehand, backhand, serve, volley
    confidence REAL,
    x_coordinate REAL,
    y_coordinate REAL,
    stroke_speed REAL,  -- estimated speed
    ball_position JSON,  -- ball location during stroke
    player_position JSON,  -- player position during stroke
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (video_id) REFERENCES videos(id) ON DELETE CASCADE
);
```

**Indexes:**
```sql
CREATE INDEX idx_strokes_video_id ON stroke_events(video_id);
CREATE INDEX idx_strokes_type ON stroke_events(stroke_type);
CREATE INDEX idx_strokes_timestamp ON stroke_events(timestamp);
```

### 5. Ball Trajectory Table
Tracks ball movement throughout the video.

```sql
CREATE TABLE ball_trajectory (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    video_id TEXT NOT NULL,
    frame_number INTEGER NOT NULL,
    timestamp REAL NOT NULL,
    x_coordinate REAL,
    y_coordinate REAL,
    z_coordinate REAL,  -- depth estimation
    velocity_x REAL,
    velocity_y REAL,
    velocity_z REAL,
    confidence REAL,
    detected BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (video_id) REFERENCES videos(id) ON DELETE CASCADE
);
```

**Indexes:**
```sql
CREATE INDEX idx_ball_video_id ON ball_trajectory(video_id);
CREATE INDEX idx_ball_timestamp ON ball_trajectory(timestamp);
CREATE INDEX idx_ball_detected ON ball_trajectory(detected);
```

### 6. Metrics Summary Table
Aggregated performance metrics per video.

```sql
CREATE TABLE metrics_summary (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    video_id TEXT UNIQUE NOT NULL,
    total_strokes INTEGER DEFAULT 0,
    forehand_count INTEGER DEFAULT 0,
    backhand_count INTEGER DEFAULT 0,
    serve_count INTEGER DEFAULT 0,
    volley_count INTEGER DEFAULT 0,
    average_rally_duration REAL,
    total_rally_count INTEGER DEFAULT 0,
    court_coverage_percentage REAL,
    baseline_time_percentage REAL,
    service_line_time_percentage REAL,
    net_time_percentage REAL,
    average_stroke_speed REAL,
    max_stroke_speed REAL,
    ball_bounce_count INTEGER DEFAULT 0,
    average_ball_speed REAL,
    max_ball_height REAL,
    processing_accuracy REAL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (video_id) REFERENCES videos(id) ON DELETE CASCADE
);
```

**Indexes:**
```sql
CREATE INDEX idx_metrics_video_id ON metrics_summary(video_id);
```

### 7. Processing Jobs Table
Tracks background processing tasks.

```sql
CREATE TABLE processing_jobs (
    id TEXT PRIMARY KEY,  -- UUID string
    video_id TEXT NOT NULL,
    job_type TEXT NOT NULL,  -- video_analysis, batch_processing
    status TEXT DEFAULT 'queued',  -- queued, running, completed, failed
    progress INTEGER DEFAULT 0,  -- 0-100
    current_step TEXT,
    error_message TEXT,
    started_at TIMESTAMP,
    completed_at TIMESTAMP,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (video_id) REFERENCES videos(id) ON DELETE CASCADE
);
```

**Indexes:**
```sql
CREATE INDEX idx_jobs_video_id ON processing_jobs(video_id);
CREATE INDEX idx_jobs_status ON processing_jobs(status);
```

## JSON Data Examples

### Analysis Results JSON Structure
```json
{
  "ball_detection": {
    "bbox": [x1, y1, x2, y2],
    "confidence": 0.95,
    "track_id": 1
  },
  "pose_estimation": {
    "landmarks": [...],
    "keypoints": {...},
    "confidence": 0.88
  },
  "stroke_detection": {
    "stroke_type": "forehand",
    "confidence": 0.92,
    "motion_data": {...}
  }
}
```

### Player Position JSON Structure
```json
{
  "pose_landmarks": [
    {"x": 0.5, "y": 0.3, "z": 0.1, "visibility": 0.9},
    ...
  ],
  "keypoints": {
    "nose": {"x": 0.5, "y": 0.3},
    "left_shoulder": {"x": 0.4, "y": 0.35},
    ...
  },
  "court_position": "baseline",
  "confidence": 0.88
}
```

## Database Operations

### Common Queries

#### Get Video Analysis Summary
```sql
SELECT 
    v.filename,
    v.duration,
    ms.total_strokes,
    ms.forehand_count,
    ms.backhand_count,
    ms.average_rally_duration,
    ms.court_coverage_percentage
FROM videos v
LEFT JOIN metrics_summary ms ON v.id = ms.video_id
WHERE v.status = 'completed'
ORDER BY v.upload_date DESC;
```

#### Get Stroke Events for Video
```sql
SELECT 
    timestamp,
    stroke_type,
    confidence,
    x_coordinate,
    y_coordinate
FROM stroke_events
WHERE video_id = ?
ORDER BY timestamp;
```

#### Get Ball Trajectory
```sql
SELECT 
    timestamp,
    x_coordinate,
    y_coordinate,
    confidence
FROM ball_trajectory
WHERE video_id = ? AND detected = TRUE
ORDER BY timestamp;
```

#### Get Player Position Timeline
```sql
SELECT 
    timestamp,
    court_position,
    x_coordinate,
    y_coordinate,
    confidence
FROM player_positions
WHERE video_id = ?
ORDER BY timestamp;
```

## Migration Strategy

### Version 1.0 (MVP)
- SQLite with all tables above
- Basic indexing for performance
- JSON flexibility for analysis data

### Future Migrations
- PostgreSQL for production
- Partitioning for large datasets
- Advanced indexing strategies
- Data archival policies

## Performance Considerations

### Indexing Strategy
- Primary keys on all tables
- Composite indexes for common queries
- JSON indexes for flexible data

### Query Optimization
- Use prepared statements
- Limit result sets
- Implement pagination
- Cache frequently accessed data

### Storage Optimization
- Compress JSON data if needed
- Archive old analysis results
- Implement data retention policies
- Regular VACUUM operations

## Backup and Recovery

### Backup Strategy
```bash
# Daily backup
sqlite3 tennis_analysis.db ".backup backup_$(date +%Y%m%d).db"

# Weekly full backup
cp tennis_analysis.db weekly_backup_$(date +%Y%m%d).db
```

### Recovery Procedures
1. Stop application
2. Restore from backup
3. Verify data integrity
4. Restart application

## Monitoring and Maintenance

### Database Health Checks
- Monitor table sizes
- Check index usage
- Analyze query performance
- Monitor disk space

### Maintenance Tasks
- Weekly VACUUM
- Monthly ANALYZE
- Quarterly index rebuild
- Annual data archival 