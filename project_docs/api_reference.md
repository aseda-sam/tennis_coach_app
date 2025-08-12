# API Reference

> **Note**: For complete, interactive API documentation, visit the Swagger UI at http://localhost:8000/docs when the backend server is running.

## Overview

The Tennis Coach API provides endpoints for video upload, processing, and analysis results retrieval. Built with FastAPI for optimal performance and automatic documentation generation.

## Base URL
```
http://localhost:8000
```

## Interactive Documentation

- **Swagger UI**: http://localhost:8000/docs - Interactive API documentation with testing interface
- **ReDoc**: http://localhost:8000/redoc - Alternative documentation format

## Quick Reference

### Video Management
- `POST /api/videos/upload` - Upload a tennis video for analysis
- `GET /api/videos/` - List all uploaded videos
- `GET /api/videos/{filename}` - Get video details
- `GET /api/videos/{filename}/stream` - Stream original video for playback
- `GET /api/videos/{filename}/annotated` - Stream annotated video with overlays
- `DELETE /api/videos/{filename}` - Delete video and associated data

### Analysis
- `POST /api/analysis/{video_filename}` - Start analysis for a video
- `GET /api/analysis/{video_filename}` - Get analysis results
- `GET /api/analysis/` - List all analyses
- `DELETE /api/analysis/{video_filename}` - Delete analysis results

### Health & Status
- `GET /` - API information
- `GET /api/videos/` - Health check (lists videos)

## Authentication

Currently, no authentication is required for MVP. Future versions will implement JWT-based authentication.

## File Upload Limits

- **Maximum file size**: 100MB
- **Supported formats**: MP4, MOV, AVI
- **Processing time**: Varies based on video length and resolution

## CORS Configuration

The API is configured to allow requests from:
- http://localhost:3000
- http://127.0.0.1:3000

This enables the React frontend to communicate with the backend.

## Error Responses

Common HTTP status codes:
- `200` - Success
- `400` - Bad Request (invalid file format, size too large)
- `404` - Not Found (video or analysis not found)
- `500` - Internal Server Error (processing failure)

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
curl -X POST "http://localhost:8000/api/videos/upload" \
  -H "accept: application/json" \
  -H "Content-Type: multipart/form-data" \
  -F "file=@tennis_video.mp4"
```

#### List Videos
```bash
curl -X GET "http://localhost:8000/api/videos/" \
  -H "accept: application/json"
```

#### Start Analysis
```bash
curl -X POST "http://localhost:8000/api/analysis/tennis_video.mp4" \
  -H "accept: application/json"
```

## Production Deployment

For production deployment information, see the [Deployment Guide](deployment_guide.md).

## Support

- **API Issues**: Check the Swagger UI for detailed error responses
- **Development**: See [backend README](../backend/README.md) for setup and troubleshooting
- **Deployment**: See [deployment guide](deployment_guide.md) for production setup
