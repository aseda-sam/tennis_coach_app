# Tennis Coach App - Backend

FastAPI backend for the tennis analysis system with computer vision capabilities for ball detection and pose estimation.

## Features

- **Video Upload & Management**: Secure file upload with validation
- **Computer Vision Analysis**: YOLO ball detection + MediaPipe pose estimation
- **Annotated Video Creation**: Generate videos with detection overlays
- **RESTful API**: FastAPI with automatic OpenAPI documentation
- **Database Integration**: SQLite with SQLAlchemy ORM
- **Code Quality**: Ruff linting and formatting

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
- **Health Check**: http://localhost:8000/api/videos/

## Environment Configuration

### Required Environment Variables

Create a `.env` file in the `backend/` directory:

```bash
# Database
DATABASE_URL=sqlite:///./data/database/tennis_analysis.db

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

```bash
# Processing Configuration
MAX_WORKERS=4
BATCH_SIZE=10
CONFIDENCE_THRESHOLD=0.5

# Security (for production)
SECRET_KEY=your-secret-key-here
```

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
```

### Testing

```bash
# Run all tests
pytest

# Run with coverage
pytest --cov=app --cov-report=html

# Run specific test files
pytest tests/test_video_api.py

# Run specific test functions
pytest tests/test_video_api.py::test_upload_video_success
```

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

### Video Management
- `POST /api/videos/upload` - Upload video file
- `GET /api/videos/` - List all videos
- `GET /api/videos/{filename}` - Get video details
- `GET /api/videos/{filename}/stream` - Stream original video
- `GET /api/videos/{filename}/annotated` - Stream annotated video
- `DELETE /api/videos/{filename}` - Delete video

### Analysis
- `POST /api/analysis/{video_filename}` - Start analysis
- `GET /api/analysis/{video_filename}` - Get analysis results
- `GET /api/analysis/` - List all analyses
- `DELETE /api/analysis/{video_filename}` - Delete analysis

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
rm data/database/tennis_analysis.db
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
  -e DATABASE_URL=sqlite:///./data/database/tennis_analysis.db \
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

## Contributing

1. Follow the code quality standards (Ruff formatting and linting)
2. Add type hints to all functions
3. Write tests for new features
4. Update documentation for API changes
5. Use conventional commit messages

## License

MIT License
