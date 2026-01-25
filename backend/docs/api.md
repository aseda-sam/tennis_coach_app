# API Reference

> **Note**: For interactive API documentation, visit http://localhost:8000/docs when the backend server is running.

## Overview

The Tennis Coach API provides endpoints for video upload, processing, and analysis results retrieval. Built with FastAPI for optimal performance and automatic documentation generation.

**Current Version**: v0 (Alpha) - API is under active development and may have breaking changes.

## Base URL

```
http://localhost:8000
```

## API Versioning

The API uses versioned endpoints to ensure stability and backward compatibility:

- **Current**: `/v0/` - Alpha version (under development)
- **Future**: `/v1/` - Stable version (when ready for production)

All endpoints are prefixed with the version number (e.g., `/v0/videos/upload`).

## Interactive Documentation

- **Swagger UI**: http://localhost:8000/docs - Interactive API documentation with testing interface
- **ReDoc**: http://localhost:8000/redoc - Alternative documentation format
- **API Info**: http://localhost:8000/v0 - Version information and endpoint overview

## Quick Reference

### Health & Status

- `GET /health` - Health check endpoint
- `GET /` - API root information
- `GET /v0` - Version 0 API information

### Video Management

- `POST /v0/videos/upload` - Upload a tennis video for analysis
- `GET /v0/videos/` - List all uploaded videos
- `GET /v0/videos/demo` - Get the active demo video (requires authentication)
- `GET /v0/videos/{video_id}` - Get video details by ID
- `GET /v0/videos/{video_id}/stream` - Stream original video (uses public demo bucket URL for active demo videos)
- `GET /v0/videos/{video_id}/url` - Get signed URL for video access (returns public demo bucket URL for active demo videos)
- `GET /v0/videos/{video_id}/overlay-data` - Get pose overlay data for client-side rendering
- `GET /v0/videos/{video_id}/analysis-status` - Get analysis status for a video
- `DELETE /v0/videos/{video_id}` - Delete video and associated data

#### Demo Videos

Demo videos are served from a public Supabase bucket (when configured) and do not require signed URLs. Only one demo video can be active at a time, controlled by the `is_active_demo` flag. Active demo videos are accessible to all authenticated users and use public bucket URLs for efficient streaming.

### Analysis

- `POST /v0/analysis/videos/{video_id}` - Start analysis for a video
- `GET /v0/analysis/{analysis_id}` - Get analysis results by ID
- `GET /v0/analysis/` - List all analyses
- `GET /v0/analysis/status/{analysis_id}` - Get analysis processing status
- `DELETE /v0/analysis/{analysis_id}` - Delete analysis results

### Serve Attempts

- `POST /v0/serve-attempts/` - Create a new serve attempt
- `GET /v0/serve-attempts/me` - Get my serve attempts (with optional filters)
- `GET /v0/serve-attempts/{serve_attempt_id}` - Get a specific serve attempt by ID
- `PUT /v0/serve-attempts/{serve_attempt_id}` - Update a serve attempt
- `DELETE /v0/serve-attempts/{serve_attempt_id}` - Delete a serve attempt
- `POST /v0/videos/{video_id}/analyze-serves` - Batch analyze serve attempts for a video

## Authentication

The API uses **JWT-based authentication** (configurable provider). Rate limiting is applied to authentication endpoints to prevent brute force attacks:

- Production: 5 authentication attempts per minute per IP
- Other profiles: 10 authentication attempts per minute per IP
- Local development: No rate limiting

## Upload Limits

Video uploads are rate-limited per user:

- **Regular users**: Maximum 3 videos per day (production)
- **Admin users**: Unlimited uploads
- **Local development**: No limits
- Limits are enforced via database queries (counts uploads in last 24 hours)

## File Upload Limits

- **Maximum file size**: 100MB
- **Supported formats**: MP4, MOV, AVI, MKV, WMV
- **Processing time**: Varies based on video length and resolution

### Video Processing Limits (Environment-Specific)

#### Local Environment (M1 MacBook Pro)

- **Maximum resolution**: 4K (3840x2160)
- **Maximum frame rate**: 60fps
- **Maximum duration**: 5 minutes (300 seconds)
- **Frame skip ratio**: 1 (process all frames)

#### Docker Environment

- **Maximum resolution**: 1080p (1920x1080)
- **Maximum frame rate**: 60fps
- **Maximum duration**: 5 minutes (300 seconds)
- **Frame skip ratio**: 1 (process all frames)

#### Production Environment

- **Maximum resolution**: 1080p (1920x1080)
- **Maximum frame rate**: 30fps
- **Maximum duration**: 5 minutes (300 seconds)
- **Frame skip ratio**: 1 (process all frames)

> **Note**: These limits are automatically detected and applied based on the environment. Videos exceeding these limits will be rejected with appropriate error messages.

## CORS Configuration

The API is configured to allow requests from:

- http://localhost:3000
- http://127.0.0.1:3000

This enables the React frontend to communicate with the backend.

## Overlay Data Endpoints

### Get Overlay Data

**GET** `/v0/videos/{video_id}/overlay-data`

Retrieves pose detection data formatted for client-side overlay rendering. This endpoint formats existing pose detection data for frontend consumption - no new analysis is performed.

**Response:** `200 OK`

```json
{
  "video_id": 1,
  "fps": 30.0,
  "total_frames": 900,
  "width": 1920,
  "height": 1080,
  "frames": [
    {
      "frame_index": 0,
      "timestamp": 0.0,
      "keypoints": {
        "left_shoulder": [320.5, 240.2],
        "right_shoulder": [450.3, 235.8],
        "left_elbow": [280.1, 320.5],
        "right_elbow": [490.2, 315.3],
        "left_wrist": [250.0, 400.0],
        "right_wrist": [520.0, 395.0],
        "left_hip": [350.0, 500.0],
        "right_hip": [420.0, 495.0],
        "left_knee": [340.0, 650.0],
        "right_knee": [430.0, 645.0],
        "left_ankle": [330.0, 800.0],
        "right_ankle": [440.0, 795.0]
      },
      "confidence": 0.85
    }
  ]
}
```

**Keypoints Format:**

- Each keypoint is a dictionary entry with the keypoint name as the key
- Values are arrays `[x, y]` representing coordinates in original video dimensions
- Coordinates are scaled client-side to match displayed video dimensions

**Use Case:**
This endpoint is used by the frontend to render pose skeleton overlays on videos. The overlay is rendered client-side using HTML5 Canvas, eliminating the need for server-side video encoding.

## Error Responses

The API uses standardized error responses with the following structure:

```json
{
  "error": {
    "code": "ERROR_CODE",
    "message": "Human-readable error message",
    "details": {
      "field": "additional_error_info"
    }
  }
}
```

### Common HTTP Status Codes

- `200` - Success
- `400` - Bad Request (validation errors, processing failures)
- `404` - Not Found (video or analysis not found)
- `422` - Validation Error (invalid request format)
- `500` - Internal Server Error (unexpected server errors)

### Error Codes

- `VALIDATION_ERROR` - Input validation failed
- `FILE_TOO_LARGE` - File exceeds size limit
- `UNSUPPORTED_FORMAT` - File format not supported
- `RESOLUTION_TOO_HIGH` - Video resolution exceeds environment limits
- `FPS_TOO_HIGH` - Video frame rate exceeds environment limits
- `DURATION_TOO_LONG` - Video duration exceeds maximum allowed
- `VIDEO_NOT_FOUND` - Video ID not found
- `ANALYSIS_NOT_FOUND` - Analysis ID not found
- `PROCESSING_FAILED` - Video processing failed
- `UPLOAD_FAILED` - File upload failed

## Request/Response Models

### Video Upload Response

```json
{
  "video_id": 1,
  "filename": "tennis_video.mp4",
  "file_size": 1048576,
  "status": "uploaded",
  "message": "Video uploaded successfully",
  "metadata": {
    "duration": 30.5,
    "fps": 30.0,
    "width": 1920,
    "height": 1080,
    "frame_count": 915
  }
}
```

### Video Information Response

```json
{
  "id": 1,
  "filename": "tennis_video.mp4",
  "file_path": "/path/to/video.mp4",
  "file_size": 1048576,
  "content_type": "video/mp4",
  "duration": 30.5,
  "fps": 30.0,
  "width": 1920,
  "height": 1080,
  "frame_count": 915,
  "created_at": "2024-01-15T10:30:00",
  "updated_at": "2024-01-15T10:30:00",
  "status": "uploaded",
  "error_message": null
}
```

### Analysis Start Response

```json
{
  "analysis_id": 1,
  "video_filename": "tennis_video.mp4",
  "status": "processing",
  "message": "Analysis started successfully",
  "estimated_duration": 60.0
}
```

### Analysis Status Response

```json
{
  "analysis_id": 1,
  "status": "completed",
  "progress": 100,
  "created_at": "2024-01-15T10:30:00",
  "completed_at": "2024-01-15T10:35:00"
}
```

**Status Values:**

- `processing` - Analysis is currently running
- `completed` - Analysis finished successfully
- `failed` - Analysis encountered an error

**Progress:** Integer (0-100) indicating completion percentage

## Development

### Testing the API

1. **Start the backend server**:

   ```bash
   cd backend
   python -m uvicorn app.main:app --reload --port 8000
   ```

2. **Visit Swagger UI**: http://localhost:8000/docs

3. **Test endpoints directly** in the browser interface

### Example Requests

#### Upload Video

```bash
curl -X POST "http://localhost:8000/v0/videos/upload" \
  -H "accept: application/json" \
  -H "Content-Type: multipart/form-data" \
  -F "file=@tennis_video.mp4"
```

#### List Videos

```bash
curl -X GET "http://localhost:8000/v0/videos/" \
  -H "accept: application/json"
```

#### Get Video Details

```bash
curl -X GET "http://localhost:8000/v0/videos/1" \
  -H "accept: application/json"
```

#### Start Analysis

```bash
curl -X POST "http://localhost:8000/v0/analysis/videos/1" \
  -H "accept: application/json" \
  -H "Content-Type: application/json" \
  -d '{
    "analysis_type": "pose_only",
    "confidence_threshold": 0.7
  }'
```

#### Get Analysis Results

```bash
curl -X GET "http://localhost:8000/v0/analysis/1" \
  -H "accept: application/json"
```

#### Get Analysis Status

```bash
curl -X GET "http://localhost:8000/v0/analysis/status/1" \
  -H "accept: application/json"
```

## Response Headers

The API includes custom headers for monitoring and debugging:

- `X-Processing-Time` - Request processing time in seconds
- `X-Request-ID` - Unique request identifier for tracing

## Production Deployment

For production deployment information, see the [Deployment Guide](deployment.md).

## Support

- **API Issues**: Check the Swagger UI for detailed error responses
- **Development**: See [backend README](../README.md) for setup and troubleshooting
- **Deployment**: See [deployment guide](deployment.md) for production setup
- **Testing**: Comprehensive integration tests available in `backend/tests/test_integration.py`
