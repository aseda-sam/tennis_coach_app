# API Documentation

## Overview

The Tennis Analysis API provides endpoints for video upload, processing, and analysis results retrieval. Built with FastAPI for optimal performance and automatic documentation generation.

## Base URL
```
http://localhost:8000
```

## Authentication
Currently, no authentication is required for MVP. Future versions will implement JWT-based authentication.

## Interactive Documentation
- **Swagger UI**: http://localhost:8000/docs
- **ReDoc**: http://localhost:8000/redoc

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
  "filename": "tennis_rally.mp4",
  "file_size": 15728640,
  "content_type": "video/mp4",
  "duration": 45.2,
  "fps": 30.0,
  "width": 1920,
  "height": 1080,
  "frame_count": 1356,
  "message": "Video uploaded successfully"
}
```

#### GET /api/videos
Retrieve list of uploaded videos.

**Response:**
```json
[
  {
    "filename": "tennis_rally.mp4",
    "file_size": 15728640,
    "duration": 45.2,
    "width": 1920,
    "height": 1080
  }
]
```

#### GET /api/videos/{filename}
Get detailed information about a specific video.

**Response:**
```json
{
  "filename": "tennis_rally.mp4",
  "file_size": 15728640,
  "content_type": "video/mp4",
  "duration": 45.2,
  "fps": 30.0,
  "width": 1920,
  "height": 1080,
  "frame_count": 1356,
  "message": "Video details retrieved successfully"
}
```

#### GET /api/videos/{filename}/stream ✅ **NEW**
Stream a video file for playback.

**Response:**
- Video file content (binary stream)
- Content-Type: video/mp4 (or appropriate video type)
- 404 Not Found if video doesn't exist

#### DELETE /api/videos/{filename}
Delete a video and its associated data.

**Response:**
```json
{
  "message": "Video deleted successfully"
}
```

### Analysis

#### POST /api/analysis/{video_filename}
Start analysis for a specific video.

**Response:**
```json
{
  "message": "Analysis started successfully",
  "analysis_id": 1,
  "processing_time": 12.5,
  "analysis_summary": {
    "total_frames": 1356,
    "frames_with_balls": 1200,
    "total_ball_detections": 2400,
    "average_detections_per_frame": 2.0,
    "detection_rate": 0.88
  },
  "frames_processed": 1356,
  "error": null
}
```

#### GET /api/analysis/{video_filename}
Get analysis results for a specific video.

**Response:**
```json
{
  "id": 1,
  "video_filename": "tennis_rally.mp4",
  "analysis_type": "ball_detection",
  "total_frames": 1356,
  "frames_with_balls": 1200,
  "total_ball_detections": 2400,
  "average_detections_per_frame": 2.0,
  "detection_rate": 0.88,
  "processing_time": 12.5,
  "model_used": "yolov8n.pt",
  "confidence_threshold": 0.5
}
```

#### GET /api/analysis
List all analyses.

**Response:**
```json
[
  {
    "id": 1,
    "video_filename": "tennis_rally.mp4",
    "analysis_type": "ball_detection",
    "total_frames": 1356,
    "frames_with_balls": 1200,
    "total_ball_detections": 2400,
    "average_detections_per_frame": 2.0,
    "detection_rate": 0.88,
    "processing_time": 12.5,
    "model_used": "yolov8n.pt",
    "confidence_threshold": 0.5
  }
]
```

#### DELETE /api/analysis/{video_filename}
Delete analysis results for a specific video.

**Response:**
```json
{
  "message": "Analysis deleted successfully"
}
```

### Health & Status

#### GET /
Get API information.

**Response:**
```json
{
  "message": "Tennis Analysis API",
  "version": "1.0.0",
  "docs": "/docs",
  "status": "running"
}
```

#### GET /health ⚠️ **DEPRECATED**
Health check endpoint (not implemented in current version).

**Alternative**: Use `GET /api/videos/` for health checks.

**Response:**
```json
{
  "status": "healthy"
}
```

### Static Files

#### GET /processed/{filename}
Access processed video files.

**Response:**
- Video file content (if file exists)
- 404 Not Found (if file doesn't exist)

## Error Responses

### 400 Bad Request
```json
{
  "detail": "Invalid file format. Only MP4, MOV, AVI files are supported."
}
```

### 404 Not Found
```json
{
  "detail": "Video not found"
}
```

### 500 Internal Server Error
```json
{
  "detail": "Analysis failed: Model loading error"
}
```

## File Upload Limits

- **Maximum file size**: 100MB
- **Supported formats**: MP4, MOV, AVI
- **Processing time**: Varies based on video length and resolution

## CORS Configuration

The API is configured to allow requests from:
- http://localhost:3000
- http://127.0.0.1:3000

This enables the React frontend to communicate with the backend. 