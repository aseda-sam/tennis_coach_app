# API Reference

> **Note**: For complete, interactive API documentation, visit the Swagger UI at http://localhost:8000/docs when the backend server is running.

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
- `GET /v0/videos/{video_id}` - Get video details by ID
- `GET /v0/videos/{video_id}/stream` - Stream original video
- `GET /v0/videos/{video_id}/annotated/stream` - Stream annotated video with overlays
- `DELETE /v0/videos/{video_id}` - Delete video and associated data

### Analysis
- `POST /v0/analysis/videos/{video_id}` - Start analysis for a video
- `GET /v0/analysis/{analysis_id}` - Get analysis results by ID
- `GET /v0/analysis/` - List all analyses
- `GET /v0/analysis/status/{analysis_id}` - Get analysis processing status
- `DELETE /v0/analysis/{analysis_id}` - Delete analysis results

### Ball Contacts
- `POST /v0/ball-contacts/` - Create a new ball contact marker
- `GET /v0/ball-contacts/video/{video_id}` - Get all ball contacts for a video
- `GET /v0/ball-contacts/video/{video_id}/timestamps` - Get ball contact timestamps for a video
- `GET /v0/ball-contacts/{ball_contact_id}` - Get a specific ball contact by ID
- `PUT /v0/ball-contacts/{ball_contact_id}` - Update a ball contact
- `DELETE /v0/ball-contacts/{ball_contact_id}` - Delete a ball contact

## Authentication

Currently, no authentication is required for MVP. Future versions will implement JWT-based authentication.

## File Upload Limits

- **Maximum file size**: 100MB
- **Supported formats**: MP4, MOV, AVI, MKV, WMV
- **Processing time**: Varies based on video length and resolution

### Video Processing Limits (Environment-Specific)

#### Local Environment (M1 MacBook Pro)
- **Maximum resolution**: 4K (3840x2160)
- **Maximum frame rate**: 60fps
- **Maximum duration**: 5 minutes (300 seconds)
- **Frame skip ratio**: 2 (process every 2nd frame)

#### Docker Environment
- **Maximum resolution**: 1080p (1920x1080)
- **Maximum frame rate**: 60fps
- **Maximum duration**: 5 minutes (300 seconds)
- **Frame skip ratio**: 3 (process every 3rd frame)

#### Production Environment (Render)
- **Maximum resolution**: 1080p (1920x1080)
- **Maximum frame rate**: 30fps
- **Maximum duration**: 5 minutes (300 seconds)
- **Frame skip ratio**: 4 (process every 4th frame)

> **Note**: These limits are automatically detected and applied based on the environment. Videos exceeding these limits will be rejected with appropriate error messages.

## CORS Configuration

The API is configured to allow requests from:
- http://localhost:3000
- http://127.0.0.1:3000

This enables the React frontend to communicate with the backend.

## Ball Contact Endpoints

### Create Ball Contact
**POST** `/v0/ball-contacts/`

Creates a new ball contact marker for a video.

**Request Body:**
```json
{
  "video_id": 1,
  "video_timestamp": 5.23,
  "contact_hand": "right",
  "stroke_type": "ground_stroke",
  "stroke_subtype": "forehand",
  "detection_source": "manual"
}
```

**Response:** `201 Created`
```json
{
  "id": 1,
  "video_id": 1,
  "video_timestamp": 5.23,
  "contact_hand": "right",
  "stroke_type": "ground_stroke",
  "stroke_subtype": "forehand",
  "detection_source": "manual",
  "created_at": "2025-01-01T12:00:00Z"
}
```

### Get Ball Contacts for Video
**GET** `/v0/ball-contacts/video/{video_id}`

Retrieves all ball contacts for a specific video.

**Response:** `200 OK`
```json
[
  {
    "id": 1,
    "video_timestamp": 5.23,
    "contact_hand": "right",
    "stroke_type": "ground_stroke",
    "detection_source": "manual"
  }
]
```

### Get Ball Contact Timestamps
**GET** `/v0/ball-contacts/video/{video_id}/timestamps`

Retrieves only the timestamps of ball contacts for a video.

**Response:** `200 OK`
```json
[5.23, 8.45, 12.67]
```

### Update Ball Contact
**PUT** `/v0/ball-contacts/{ball_contact_id}`

Updates an existing ball contact.

**Request Body:**
```json
{
  "stroke_type": "serve",
  "stroke_subtype": "flat"
}
```

### Delete Ball Contact
**DELETE** `/v0/ball-contacts/{ball_contact_id}`

Deletes a ball contact marker.

**Response:** `200 OK`
```json
{
  "message": "Ball contact deleted successfully"
}
```

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
    "analysis_type": "ball_tracking",
    "confidence_threshold": 0.5,
    "include_pose_detection": true
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

For production deployment information, see the [Deployment Guide](deployment_guide.md).

## Support

- **API Issues**: Check the Swagger UI for detailed error responses
- **Development**: See [backend README](../backend/README.md) for setup and troubleshooting
- **Deployment**: See [deployment guide](deployment_guide.md) for production setup
- **Testing**: Comprehensive integration tests available in `backend/tests/test_integration.py`
