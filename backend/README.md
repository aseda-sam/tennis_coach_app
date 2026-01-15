# Tennis Coach App - Backend

FastAPI backend for the tennis analysis system with computer vision capabilities for ball detection and pose estimation.

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

**Note:** Most API endpoints require authentication. See the [Authentication](#authentication) section below for configuration details.

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

# Authentication (Supabase)
# Required for production, optional for local development
SUPABASE_URL=https://your-project.supabase.co/
SUPABASE_SECRET_KEY=your-secret-key
```

### Optional Environment Variables

```bash
# Service Configuration
SERVICE_TYPE=api  # 'api' for API service, 'worker' for Background Worker service (default: 'api')
ENVIRONMENT=development  # 'development' or 'production'

# Redis Queue (for background tasks)
REDIS_URL=redis://localhost:6379/0

# Processing Configuration
MAX_WORKERS=4
BATCH_SIZE=10
CONFIDENCE_THRESHOLD=0.5

# Ball Contact Configuration
BALL_CONTACT_TIMESTAMP_TOLERANCE=0.1  # Tolerance in seconds for duplicate detection

# Profile configuration (for local development)
PROFILE=local  # Disables auth automatically
```

## Authentication

The application uses **JWT-based authentication** (configurable provider). Most API endpoints require authentication to ensure users can only access their own data.

### Architecture

- **Frontend**: Handles user login/registration via Supabase client
- **Backend**: Verifies JWT tokens on protected endpoints
- **User Isolation**: All videos and players are scoped to individual users
- **Local Development**: Authentication can be disabled using `PROFILE=local`

### Production Setup

For production, configure Supabase authentication:

```bash
SUPABASE_URL=https://your-project.supabase.co/
SUPABASE_SECRET_KEY=your-secret-key
REQUIRE_AUTH=true
PROFILE=production
```

### Local Development

For local development, set the profile to `local`:

```bash
PROFILE=local
```

When `PROFILE=local`, the API automatically uses a mock user and doesn't require authentication tokens. This is useful for local testing but should never be used in production.

### Protected Endpoints

The following endpoints require authentication:
- Video upload and management
- Player creation and management
- Ball contact creation and management
- Analysis requests

### Authorization

The application enforces user-based data isolation:
- Users can only access their own videos and players
- Video owners control access to their video data
- Admin users (configured via Supabase metadata) can access all data

See the [API documentation](docs/api.md) for details on authentication requirements for each endpoint.

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

## Project Structure

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
│   │   ├── video_service.py     # Video processing utilities
│   └── main.py              # FastAPI app
├── docs/                    # Detailed documentation
│   ├── api.md              # API reference
│   ├── database_schema.md  # Database schema
│   ├── profile-configuration.md  # Profile-based configuration
│   ├── cloud-database-setup.md   # PostgreSQL setup guide
│   ├── cloud-storage-setup.md    # Cloud storage setup
│   ├── background-tasks.md       # Background task system overview
│   └── background-tasks-rq.md    # Background tasks with Redis Queue (RQ)
├── alembic/                 # Database migrations
├── tests/                   # Test files
├── pyproject.toml           # Project configuration
└── README.md               # This file
```

## Features

- **User Authentication**: Secure authentication with Supabase Auth
- **User-based Data Isolation**: Videos and players are scoped to individual users
- **Player Management**: Create and manage players with hand preference and backhand style
- **Video Upload & Management**: Secure file upload with validation and metadata extraction
- **Computer Vision Analysis**: YOLO ball detection + MediaPipe pose estimation
- **Client-Side Overlays**: Real-time pose skeleton overlays rendered in the browser
- **Ball Contact System**: Manual and automated ball contact detection with configurable tolerance
- **Contact Management**: Create, edit, and delete ball contact markers with stroke classification
- **RESTful API**: FastAPI with automatic OpenAPI documentation and versioning
- **Database Integration**: SQLite with SQLAlchemy ORM
- **Code Quality**: Ruff linting and formatting
- **Comprehensive Testing**: Unit and integration tests with schema validation
- **Standardized Error Handling**: Consistent error responses across all endpoints
- **API Versioning**: Versioned endpoints for future compatibility
- **Request Monitoring**: Processing time and request ID tracking

## Computer Vision Features

### Ball Detection

- **Model**: YOLOv8n (nano)
- **Features**: Real-time ball tracking, trajectory analysis
- **Output**: Bounding boxes, confidence scores, detection metrics

### Pose Estimation

- **Model**: MediaPipe Pose
- **Features**: 11 tennis-relevant keypoints (shoulders, elbows, wrists, hips, knees, ankles)
- **Output**: Skeleton overlays, pose detection metrics

### Client-Side Overlays

- **Rendering**: Canvas-based overlay rendering in the browser
- **Data Source**: Overlay data API endpoint (`GET /v0/videos/{id}/overlay-data`)
- **Features**: Real-time pose skeleton overlays synchronized with video playback
- **Styling**: Neon green skeleton with black outline
- **Performance**: Efficient client-side rendering without server-side video encoding

### Ball Contact System

- **Manual Marking**: Users can add ball contact markers directly on video timeline
- **Automated Detection**: AI-powered contact detection with configurable tolerance
- **Stroke Classification**: Support for ground_stroke, serve, volley, overhead
- **Hand Detection**: Track left/right hand usage
- **Source Attribution**: Distinguish between automated and manual detections
- **Duplicate Prevention**: Configurable timestamp tolerance (default: 0.1 seconds)
- **Database Storage**: Dedicated ball_contacts table with proper relationships

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
# Enable debug mode (auto-reload + DEBUG logging)
export DEBUG=True

# Start with debug
uvicorn app.main:app --reload --log-level debug
```

## Documentation

- **[API Reference](docs/api.md)** - Complete API documentation
- **[Database Schema](docs/database_schema.md)** - Database models and relationships
- **[Profile Configuration](docs/profile-configuration.md)** - Profile-based configuration system
- **[Cloud Database Setup](docs/cloud-database-setup.md)** - PostgreSQL/Supabase database setup
- **[Cloud Storage Setup](docs/cloud-storage-setup.md)** - Supabase storage configuration
- **[Background Tasks](docs/background-tasks.md)** - Background task system overview
- **[Background Tasks with RQ](docs/background-tasks-rq.md)** - Background task system using Redis Queue (RQ)

## Contributing

1. Follow the code quality standards (Ruff formatting and linting)
2. Add type hints to all functions
3. Write tests for new features
4. Update documentation for API changes
5. Use conventional commit messages

## License

MIT License

## Code Quality

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
