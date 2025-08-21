# Tennis Coach App - Backend

FastAPI backend for the tennis analysis system with computer vision capabilities for ball detection and pose estimation.

## Features

- **Video Upload & Management**: Secure file upload with validation and metadata extraction
- **Computer Vision Analysis**: YOLO ball detection + MediaPipe pose estimation + Ball-racket contact detection
- **Annotated Video Creation**: Generate videos with detection overlays
- **Smart Contact Detection**: Accurate ball-racket contact timing with false positive filtering
- **RESTful API**: FastAPI with automatic OpenAPI documentation and versioning
- **Database Integration**: SQLite with SQLAlchemy ORM
- **Code Quality**: Ruff linting and formatting
- **Comprehensive Testing**: Unit and integration tests with schema validation
- **Standardized Error Handling**: Consistent error responses across all endpoints
- **API Versioning**: Versioned endpoints for future compatibility
- **Request Monitoring**: Processing time and request ID tracking

## Quick Start

### Prerequisites

- Python 3.11+
- FFmpeg (required for video processing)
- Virtual environment (recommended)

### Installation

1. **Install FFmpeg**:

   ```bash
   # macOS
   brew install ffmpeg

   # Ubuntu/Debian
   sudo apt install ffmpeg

   # Windows (using chocolatey)
   choco install ffmpeg
   ```

2. **Setup Python Environment**:

   ```bash
   # Create virtual environment
   python3 -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate

   # Install dependencies
   cd backend
   pip install -e .
   ```

3. **Create Data Directories**:

   ```bash
   mkdir -p data/videos/raw data/videos/processed data/analysis_cache data/database
   ```

4. **Download YOLO Models (Optional)**:
   ```bash
   # Models will be downloaded automatically when needed, but you can pre-download them:
   cd backend
   python scripts/download_models.py
   ```

### Running the Server

#### Development Mode

```bash
cd backend
python -m uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

#### Production Mode

```bash
cd backend
python -m uvicorn app.main:app --host 0.0.0.0 --port 8000
```

#### Docker (Alternative)

```bash
# Build and run with Docker Compose
docker compose up backend

# Or build standalone
docker build -t tennis-backend .
docker run -p 8000:8000 tennis-backend
```

### Access Points

- **API**: http://localhost:8000
- **Interactive Docs**: http://localhost:8000/docs
- **Alternative Docs**: http://localhost:8000/redoc
- **Health Check**: http://localhost:8000/health
- **API Info**: http://localhost:8000/v0

## Environment Configuration

### Required Environment Variables

Create a `.env` file in the `backend/` directory:

```bash
# Database
DATABASE_URL=sqlite:///./data/database/tennis_coach.db

# File Storage
UPLOAD_DIR=./data/videos/raw
PROCESSED_DIR=./data/videos/processed
MAX_FILE_SIZE=104857600  # 100MB

# API Configuration
API_HOST=0.0.0.0
API_PORT=8000
DEBUG=True

# CORS (for frontend integration)
CORS_ORIGINS=http://localhost:3000,http://127.0.0.1:3000
```

### Optional Environment Variables

````bash
# Processing Configuration
MAX_WORKERS=4
BATCH_SIZE=10
CONFIDENCE_THRESHOLD=0.5

# Security (for production)
SECRET_KEY=your-secret-key-here

## Model Files

The application uses YOLO models for ball detection. These are automatically downloaded when needed:

- **yolov8n.pt** (~6.5MB): Nano model - faster processing, good for real-time
- **yolov8s.pt** (~22.6MB): Small model - better accuracy, slower processing

### Model Management

- Models are downloaded automatically on first use
- Models are cached locally in the working directory
- Model files are ignored by Git (see `.gitignore`)
- You can pre-download models using: `python scripts/download_models.py`

## Development

### Code Quality

The project uses Ruff for linting and formatting:

```bash
# Check code quality
ruff check .

# Fix auto-fixable issues
ruff check --fix .

# Format code
ruff format .

# Check specific files
ruff check app/api/routes/
ruff format app/services/
````

### Testing

```bash
# Run all tests
pytest

# Run with coverage
pytest --cov=app --cov-report=html

# Run specific test files
pytest tests/test_video_api.py
pytest tests/test_integration.py

# Run specific test functions
pytest tests/test_video_api.py::test_upload_video_success
pytest tests/test_integration.py::TestVideoIntegration::test_schema_validation
```

#### Test Types

- **Basic API Tests** (`test_api_basic.py`): Endpoint availability and error handling
- **Integration Tests** (`test_integration.py`): Complete workflows, schema validation, and CRUD operations
- **Video Processing Tests** (`test_video_processing.py`): Real video file processing
- **Video API Tests** (`test_video_api.py`): API versioning and endpoint validation
- **Schema Validation**: Ensures database models match Pydantic schemas
- **Error Handling**: Tests standardized error responses and edge cases

#### Test Markers

- `@pytest.mark.slow` - Long-running tests (real video processing)
- `@pytest.mark.integration` - Integration tests (complete workflows)
- `@pytest.mark.unit` - Unit tests (isolated functionality)

### Database Operations

```bash
# Initialize database (first time)
alembic upgrade head

# Create new migration
alembic revision --autogenerate -m "Description of changes"

# Apply migrations
alembic upgrade head

# Downgrade to previous version
alembic downgrade -1

# View migration history
alembic history
```

### Database Schema

#### Analysis Table

- `id` (Integer, Primary Key) - Unique analysis identifier
- `video_id` (Integer, Foreign Key) - Reference to videos table
- `video_filename` (String) - Original video filename
- `analysis_type` (String) - Type of analysis performed
- `status` (String) - Processing status (processing/completed/failed)
- `progress` (Integer) - Analysis completion percentage (0-100)
- `total_frames` (Integer) - Total frames in video
- `frames_with_balls` (Integer) - Frames containing ball detections
- `total_ball_detections` (Integer) - Total ball detections found
- `detection_rate` (Float) - Percentage of frames with detections
- `processing_time` (Float) - Analysis duration in seconds
- `model_used` (String) - YOLO model version used
- `confidence_threshold` (Float) - Detection confidence threshold
- `created_at` (DateTime) - Analysis creation timestamp
- `updated_at` (DateTime) - Last update timestamp
- `completed_at` (DateTime) - Analysis completion timestamp (nullable)

#### Video Table

- `id` (Integer, Primary Key) - Unique video identifier
- `filename` (String) - Original filename
- `file_path` (String) - Storage path
- `file_size` (Integer) - File size in bytes
- `content_type` (String) - MIME type
- `duration` (Float) - Video duration in seconds
- `fps` (Float) - Frames per second
- `width` (Integer) - Video width in pixels
- `height` (Integer) - Video height in pixels
- `frame_count` (Integer) - Total number of frames
- `status` (String) - Processing status
- `error_message` (Text) - Error details if processing failed
- `created_at` (DateTime) - Upload timestamp
- `updated_at` (DateTime) - Last update timestamp

### Project Structure

```
backend/
├── app/
│   ├── api/
│   │   ├── routes/          # API endpoints
│   │   │   ├── analysis.py  # Analysis endpoints
│   │   │   └── video.py     # Video management
│   │   └── schemas/         # Pydantic models
│   ├── core/
│   │   ├── config.py        # Configuration
│   │   └── database.py      # Database setup
│   ├── models/              # SQLAlchemy models
│   │   ├── analysis.py      # Analysis results
│   │   └── video.py         # Video metadata
│   ├── services/            # Business logic
│   │   ├── analysis_service.py  # Analysis pipeline
│   │   ├── cv_service.py        # Computer vision
│   │   └── video_service.py     # Video processing
│   └── main.py              # FastAPI app
├── alembic/                 # Database migrations
├── tests/                   # Test files
├── pyproject.toml           # Project configuration
└── README.md               # This file
```

## API Overview

### API Versioning

The API uses versioned endpoints for stability and backward compatibility:

- **Current**: `/v0/` - Alpha version (under development)
- **Future**: `/v1/` - Stable version (when ready for production)

### Health & Status

- `GET /health` - Health check endpoint
- `GET /` - API root information
- `GET /v0` - Version 0 API information

### Video Management

- `POST /v0/videos/upload` - Upload video file
- `GET /v0/videos/` - List all videos
- `GET /v0/videos/{video_id}` - Get video details by ID
- `GET /v0/videos/{video_id}/stream` - Stream original video
- `GET /v0/videos/{video_id}/annotated/stream` - Stream annotated video
- `DELETE /v0/videos/{video_id}` - Delete video

### Analysis

- `POST /v0/analysis/videos/{video_id}` - Start analysis
- `GET /v0/analysis/{analysis_id}` - Get analysis results by ID
- `GET /v0/analysis/` - List all analyses
- `GET /v0/analysis/status/{analysis_id}` - Get analysis processing status
- `DELETE /v0/analysis/{analysis_id}` - Delete analysis

### Interactive Documentation

- Visit http://localhost:8000/docs for Swagger UI
- Visit http://localhost:8000/redoc for ReDoc

## Computer Vision Features

### Ball Detection

- **Model**: YOLOv8n (nano)
- **Features**: Real-time ball tracking, trajectory analysis
- **Output**: Bounding boxes, confidence scores, detection metrics

### Pose Estimation

- **Model**: MediaPipe Pose
- **Features**: 11 tennis-relevant keypoints (shoulders, elbows, wrists, hips, knees, ankles)
- **Output**: Skeleton overlays, pose detection metrics

### Annotated Videos

- **Format**: H.264 MP4 (browser-compatible)
- **Overlays**: Ball detection (red boxes) + pose estimation (green skeleton)
- **Processing**: Automatic codec fallback for compatibility

## Troubleshooting

### Common Issues

#### Port Already in Use

```bash
# Check what's using port 8000
lsof -i :8000

# Kill process if needed
kill -9 <PID>
```

#### Database Issues

```bash
# Reset database
rm data/database/tennis_coach.db
alembic upgrade head
```

#### Video Processing Errors

```bash
# Check FFmpeg installation
ffmpeg -version

# Verify video file format
ffmpeg -i video.mp4 -f null -
```

#### Memory Issues

```bash
# Monitor memory usage
htop

# Increase swap if needed
sudo sysctl vm.swappiness=10
```

### Debug Mode

```bash
# Enable debug logging
export DEBUG=True
export LOG_LEVEL=DEBUG

# Start with debug
uvicorn app.main:app --reload --log-level debug
```

## Production Deployment

### Docker Deployment

```bash
# Build production image
docker build -t tennis-backend:latest .

# Run with environment variables
docker run -p 8000:8000 \
  -e DATABASE_URL=sqlite:///./data/database/tennis_coach.db \
  -e MAX_FILE_SIZE=104857600 \
  tennis-backend:latest
```

### Environment Variables for Production

```bash
# Database (consider PostgreSQL for production)
DATABASE_URL=postgresql://user:password@host:5432/tennis_analysis

# Security
DEBUG=False
SECRET_KEY=your-production-secret-key

# CORS
CORS_ORIGINS=https://yourdomain.com

# Storage (consider S3 for production)
STORAGE_TYPE=s3
AWS_ACCESS_KEY_ID=your-access-key
AWS_SECRET_ACCESS_KEY=your-secret-key
AWS_S3_BUCKET=tennis-analysis-videos
```

## Documentation

- **[API Reference](../project_docs/api_reference.md)** - Complete API documentation
- **[Database Schema](../project_docs/database_schema.md)** - Database models and relationships
- **[Deployment Guide](../project_docs/deployment_guide.md)** - Production deployment
- **[Project Roadmap](../project_docs/project_plan.md)** - Development phases

## Contributing

1. Follow the code quality standards (Ruff formatting and linting)
2. Add type hints to all functions
3. Write tests for new features
4. Update documentation for API changes
5. Use conventional commit messages

## License

MIT License

## Code quality

Run ruff locally before committing:

```bash
# From backend/
ruff format .
ruff check .
```

Set up pre-commit hooks to enforce ruff automatically on commit:

```bash
pip install pre-commit
pre-commit install
```

This will run ruff (lint + format) on staged files during `git commit`.
