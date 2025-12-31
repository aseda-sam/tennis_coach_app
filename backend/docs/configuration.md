# Configuration Guide

## Overview

The Tennis Coach App uses a centralized configuration system based on Pydantic Settings. Configuration values can be set via environment variables, `.env` files, or default values in the code.

## Configuration File

The main configuration is defined in `backend/app/core/config.py` using the `Settings` class.

## Environment Variables

### API Configuration

- `API_HOST` - API server host (default: "0.0.0.0")
- `API_PORT` - API server port (default: 8000)
- `DEBUG` - Enable debug mode (default: False). When True: enables auto-reload and DEBUG-level logging

### Database Configuration

- `DATABASE_URL` - SQLite database URL (default: "sqlite:///../data/database/tennis_coach.db")
- `SUPABASE_URL` - Supabase project URL (production)
- `SUPABASE_KEY` - Supabase API key (production)
- `SUPABASE_DB_URL` - Direct Supabase database connection URL (production)

### File Storage Configuration

- `STORAGE_TYPE` - Storage type: "local", "cloudinary", "s3" (default: "local")
- `UPLOAD_DIR` - Directory for uploaded videos (default: "../data/videos/raw")
- `PROCESSED_DIR` - Directory for processed videos (default: "../data/videos/processed")
- `MAX_FILE_SIZE` - Maximum file size in bytes (default: 104857600 = 100MB)
- `SUPPORTED_FORMATS` - List of supported video formats (default: [".mp4", ".mov", ".avi"])

### Computer Vision Configuration

- `ML_MODELS_DIR` - Directory containing ML models (default: "ml_models")
- `YOLO_DEFAULT_MODEL` - Default YOLO model to use (default: "nano")
- `CONFIDENCE_THRESHOLD` - General confidence threshold (default: 0.5)
- `BALL_CONFIDENCE_THRESHOLD` - Ball detection confidence threshold (default: 0.7)

### Pose Detection Configuration

- `POSE_DETECTION_CONFIDENCE` - Minimum detection confidence for pose estimation (default: 0.5)
- `POSE_TRACKING_CONFIDENCE` - Minimum tracking confidence for pose estimation (default: 0.5)
- `POSE_OVERALL_CONFIDENCE` - Overall confidence score for pose detection results (default: 0.8)

### Ball Contact Detection Configuration

- `BALL_CONTACT_TIMESTAMP_TOLERANCE` - Tolerance in seconds for duplicate contact detection (default: 0.1)

This setting controls how close two ball contacts can be in time before they're considered duplicates. Used when:

- Preventing duplicate manual contact markers
- Validating contact timestamps
- Checking for existing contacts at similar timestamps

**Usage Examples:**

- `0.1` - 100ms tolerance (default, suitable for most cases)
- `0.05` - 50ms tolerance (more strict, for high-precision analysis)
- `0.2` - 200ms tolerance (more lenient, for rough marking)

### Processing Configuration

- `MAX_VIDEO_DURATION` - Maximum video duration in seconds (default: 300 = 5 minutes)
- `FRAME_SKIP_RATIO` - Process every Nth frame (default: 1 = every frame)
- `MAX_VIDEO_RESOLUTION` - Maximum video resolution (default: (3840, 2160) = 4K)
- `MAX_FPS` - Maximum frame rate (default: 60)

### Docker-Specific Configuration

- `DOCKER_MAX_VIDEO_RESOLUTION` - Maximum resolution in Docker (default: (1920, 1080) = 1080p)
- `DOCKER_MAX_FPS` - Maximum frame rate in Docker (default: 60)
- `DOCKER_FRAME_SKIP_RATIO` - Frame skip ratio in Docker (default: 1)

### CORS Configuration

- `BACKEND_CORS_ORIGINS` - List of allowed CORS origins (default: ["http://localhost:3000", "http://127.0.0.1:3000"])

## Environment Detection

The application automatically detects the environment and applies appropriate limits:

### Local Environment

- Uses full resolution and frame rate limits
- Processes every frame by default
- Optimized for development and testing

### Docker Environment

- Uses reduced resolution and frame rate limits
- Optimized for containerized deployment
- Detected by presence of `/.dockerenv` file

### Production Environment

- Uses production database (Supabase)
- Applies strict processing limits
- Optimized for performance and cost

## Configuration Usage

### In Python Code

```python
from app.core.config import settings

# Access configuration values
tolerance = settings.BALL_CONTACT_TIMESTAMP_TOLERANCE
max_file_size = settings.MAX_FILE_SIZE
```

### Environment Variable Override

```bash
# Set tolerance to 200ms
export BALL_CONTACT_TIMESTAMP_TOLERANCE=0.2

# Set maximum file size to 50MB
export MAX_FILE_SIZE=52428800
```

### .env File

Create a `.env` file in the backend directory:

```env
BALL_CONTACT_TIMESTAMP_TOLERANCE=0.15
MAX_FILE_SIZE=52428800
PROFILE=production
```

## Configuration Validation

The configuration system automatically validates:

- Data types (float, int, string, etc.)
- Required vs optional fields
- Environment-specific constraints
- File path existence for directories

## Best Practices

1. **Use Environment Variables** for production configuration
2. **Document New Settings** in this file when adding them
3. **Provide Sensible Defaults** for all configuration values
4. **Validate Configuration** at startup
5. **Use Type Hints** for all configuration fields
6. **Group Related Settings** logically in the config file

## Migration Notes

When adding new configuration settings:

1. Add the setting to `Settings` class in `config.py`
2. Document it in this file
3. Update any relevant tests
4. Consider backward compatibility
5. Update deployment documentation if needed
