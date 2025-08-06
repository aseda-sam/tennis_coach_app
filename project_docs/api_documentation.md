# API Documentation

## Overview

The Tennis Analysis API provides endpoints for video upload, processing, and analysis results retrieval. Built with FastAPI for optimal performance and automatic documentation generation.

## Base URL
```
http://localhost:8000
```

## Authentication
Currently, no authentication is required for MVP. Future versions will implement JWT-based authentication.

## Endpoints

### Video Management

#### POST /api/videos/upload
Upload a tennis video for analysis.

**Request:**
- Content-Type: `multipart/form-data`
- Body: Video file (MP4, MOV, AVI supported)

**Response:**
```json
{
  "video_id": "uuid-string",
  "filename": "tennis_rally.mp4",
  "status": "uploaded",
  "message": "Video uploaded successfully"
}
```

#### GET /api/videos
Retrieve list of uploaded videos.

**Response:**
```json
{
  "videos": [
    {
      "video_id": "uuid-string",
      "filename": "tennis_rally.mp4",
      "upload_date": "2024-01-15T10:30:00Z",
      "duration": 45.2,
      "status": "processed",
      "analysis_available": true
    }
  ]
}
```

#### GET /api/videos/{video_id}
Get detailed information about a specific video.

**Response:**
```json
{
  "video_id": "uuid-string",
  "filename": "tennis_rally.mp4",
  "upload_date": "2024-01-15T10:30:00Z",
  "duration": 45.2,
  "file_size": 15728640,
  "status": "processed",
  "processing_time": 12.5,
  "analysis_available": true
}
```

### Analysis Results

#### GET /api/analysis/{video_id}
Get analysis results for a specific video.

**Response:**
```json
{
  "video_id": "uuid-string",
  "analysis_summary": {
    "total_strokes": 12,
    "forehand_count": 8,
    "backhand_count": 4,
    "serve_count": 0,
    "average_rally_duration": 8.5,
    "court_coverage_percentage": 65.2
  },
  "ball_trajectory": [
    {
      "frame": 1,
      "timestamp": 0.0,
      "x": 150,
      "y": 200,
      "confidence": 0.95
    }
  ],
  "player_positions": [
    {
      "frame": 1,
      "timestamp": 0.0,
      "court_position": "baseline",
      "x": 300,
      "y": 400,
      "confidence": 0.88
    }
  ],
  "stroke_events": [
    {
      "frame": 15,
      "timestamp": 0.5,
      "stroke_type": "forehand",
      "confidence": 0.92,
      "position": {
        "x": 320,
        "y": 380
      }
    }
  ]
}
```

#### GET /api/analysis/{video_id}/metrics
Get detailed metrics for a video.

**Response:**
```json
{
  "video_id": "uuid-string",
  "performance_metrics": {
    "stroke_speed": {
      "average": 85.2,
      "max": 120.5,
      "min": 45.8
    },
    "court_positioning": {
      "baseline_time": 65.2,
      "service_line_time": 34.8,
      "net_time": 0.0
    },
    "ball_trajectory": {
      "average_speed": 45.8,
      "max_height": 2.5,
      "bounce_count": 8
    }
  },
  "heatmap_data": {
    "court_coverage": "base64-encoded-image",
    "stroke_positions": "base64-encoded-image"
  }
}
```

### Processing Status

#### GET /api/processing/status/{video_id}
Check processing status of a video.

**Response:**
```json
{
  "video_id": "uuid-string",
  "status": "processing",
  "progress": 75,
  "current_step": "stroke_analysis",
  "estimated_completion": "2024-01-15T10:35:00Z"
}
```

### Batch Operations

#### POST /api/analysis/batch
Process multiple videos in batch.

**Request:**
```json
{
  "video_ids": ["uuid-1", "uuid-2", "uuid-3"]
}
```

**Response:**
```json
{
  "batch_id": "batch-uuid",
  "total_videos": 3,
  "status": "queued",
  "estimated_completion": "2024-01-15T11:00:00Z"
}
```

## Error Responses

### Standard Error Format
```json
{
  "error": {
    "code": "VALIDATION_ERROR",
    "message": "Invalid video format. Supported formats: MP4, MOV, AVI",
    "details": {
      "field": "video_file",
      "value": "invalid_format"
    }
  }
}
```

### Common Error Codes
- `VALIDATION_ERROR`: Invalid input data
- `FILE_TOO_LARGE`: Video file exceeds size limit
- `UNSUPPORTED_FORMAT`: Video format not supported
- `PROCESSING_FAILED`: Analysis processing failed
- `VIDEO_NOT_FOUND`: Video ID not found
- `ANALYSIS_NOT_AVAILABLE`: Analysis not yet completed

## Rate Limiting
- Upload: 10 requests per minute
- Analysis: 5 requests per minute
- General: 100 requests per minute

## File Size Limits
- Maximum video size: 100MB
- Supported formats: MP4, MOV, AVI
- Maximum duration: 5 minutes (for MVP)

## WebSocket Endpoints

### /ws/processing/{video_id}
Real-time processing status updates.

**Message Format:**
```json
{
  "type": "status_update",
  "data": {
    "progress": 50,
    "current_step": "ball_tracking",
    "message": "Tracking ball trajectory..."
  }
}
```

## Development Notes

### Testing Endpoints
Use the automatic FastAPI documentation at `/docs` for interactive testing.

### Environment Variables
```bash
DATABASE_URL=sqlite:///./data/database/tennis_analysis.db
UPLOAD_DIR=./data/videos/raw
PROCESSED_DIR=./data/videos/processed
MAX_FILE_SIZE=104857600  # 100MB
```

### Response Headers
All responses include:
- `Content-Type: application/json`
- `X-Processing-Time: 0.123s`
- `X-Request-ID: uuid-string` 