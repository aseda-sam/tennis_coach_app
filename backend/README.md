# Tennis Coach App - Backend

FastAPI backend for a **serve-focused** tennis coaching MVP:

- Upload a serve video
- Tag `serve_windows`
- Run pose detection + serve metrics in background jobs
- Return a small set of coach-meaningful metrics + one recommendation

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

3. **Start PostgreSQL Database**:

   ```bash
   # Using Docker Compose (recommended)
   docker compose up -d postgres

   # Or use your own PostgreSQL instance
   # Make sure it's running and accessible
   ```

4. **Create Data Directories**:

   ```bash
   mkdir -p data/videos/raw data/videos/processed data/analysis_cache
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
# Database (PostgreSQL)
# Defaults to Docker PostgreSQL when PROFILE=local
# Override if using a different PostgreSQL instance
DATABASE_URL=postgresql://tennis:tennis_dev@localhost:5432/tennis_coach

# Supabase Storage (Production)
SUPABASE_URL=https://your-project.supabase.co
SUPABASE_SECRET_KEY=your-secret-key
SUPABASE_STORAGE_BUCKET=your-private-bucket-name
SUPABASE_DEMO_BUCKET=your-public-demo-bucket-name  # Optional: public bucket for demo videos

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
PROFILE=local  # 'local' for local development (disables auth), 'production' for production

# Redis Queue (for background tasks)
REDIS_URL=redis://localhost:6379/0

# Processing Configuration
MAX_WORKERS=4
BATCH_SIZE=10
CONFIDENCE_THRESHOLD=0.5
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
- Analysis requests

### Default Player Profile

Each user has a default player profile that is automatically created or retrieved:

- **GET `/v0/players/me`**: Fetch the current user's default player profile
- **PUT `/v0/players/me`**: Create or update the default player profile

When a user signs up, they provide their name, dominant hand, and backhand style. This creates their default player profile. The profile can be updated later using the `/me` endpoint.

**Note:** The default player is used for serve window tagging when no specific player is selected. Users can create additional players via `POST /v0/players/` if needed.

### Authorization

The application enforces user-based data isolation:

- Users can only access their own videos and players
- Video owners control access to their video data
- Admin users (configured via Supabase metadata) can access all data
- Player name conflicts are checked per-user (different users can have players with the same name)

For endpoint details, use the OpenAPI docs at `http://localhost:8000/docs`.

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

#### Running Migrations in Docker

When using Docker Compose for local development, run migrations inside the container:

```bash
# Check current migration status
docker exec tennis-coach-api alembic current

# Run all pending migrations
docker exec tennis-coach-api alembic upgrade head

# Run migrations one at a time
docker exec tennis-coach-api alembic upgrade +1

# View migration history
docker exec tennis-coach-api alembic history

# Downgrade to previous version
docker exec tennis-coach-api alembic downgrade -1
```

**Note**: The container name may vary. Check running containers with `docker ps` to find the correct name.

### Demo Videos

Demo videos are served from a public Supabase bucket (when configured) and are accessible to all authenticated users. Only one demo video can be active at a time.

**📖 For complete setup and management guide, see [`docs/demo-videos.md`](docs/demo-videos.md)**

#### Setting Up Demo Bucket

1. **Create a public bucket in Supabase**:
   - Go to Storage → Create bucket
   - Name it (e.g., `demo-videos`)
   - Set it to **public** (important: demo videos need public access)

2. **Configure environment variable**:

   ```bash
   SUPABASE_DEMO_BUCKET=demo-videos
   ```

3. **Upload demo videos**:
   - **Recommended**: Upload via app with "Upload as demo video" checkbox (see [guide](docs/demo-videos.md))
   - **Alternative**: Upload videos to the demo bucket with paths starting with `demo/` and create video records manually

#### Managing Active Demo

Use the admin script to rotate between demo videos:

```bash
# List all demo videos
python backend/scripts/set_active_demo.py --list

# Set a video as the active demo
python backend/scripts/set_active_demo.py --video-id <id>
```

The script will:

- Verify the video is eligible (marked as demo, file_path starts with `demo/`)
- Copy the video to demo bucket if it doesn't exist (from private bucket)
- Set the video as active (automatically unsetting any previous active demo)

**Note**: Only videos with `file_path` starting with `demo/` can be set as active demos. This ensures demo videos are stored in the public bucket.

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
│   │   └── video.py         # Video metadata
│   ├── services/            # Business logic
│   │   ├── pose_data_service.py   # Pose helpers for biomechanics
│   │   ├── video_service.py     # Video processing utilities
│   └── main.py              # FastAPI app
├── docs/                    # Detailed documentation
│   ├── README.md           # Docs index (keep it small)
│   ├── serve-mvp.md        # MVP scope + workflow
│   ├── config.md           # PROFILE-based config
│   ├── background-jobs.md  # RQ background jobs
│   ├── deploy-flyio.md     # (Optional) Fly.io deploy notes
│   └── demo-videos.md      # (Optional) demo video workflow
├── alembic/                 # Database migrations
├── tests/                   # Test files
├── pyproject.toml           # Project configuration
└── README.md               # This file
```

## Features (Serve MVP)

- **Serve-focused workflow**: tag serve windows, compute biomechanics on demand
- **Pose detection**: MediaPipe pose estimation (background job)
- **Biomechanics reports**: phases + metrics stored per serve window
- **User Authentication**: Supabase-backed auth (disabled in `PROFILE=local`)
- **User-based Data Isolation**: videos/players/serve windows are scoped per user
- **REST API**: FastAPI + OpenAPI (`/docs`)
- **Background jobs**: RQ + Redis
- **DB**: PostgreSQL (local Docker + production Supabase)
- **Code quality**: Ruff + tests

## Documentation

Start here: **[`docs/README.md`](docs/README.md)**.

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
# Reset database (PostgreSQL)
# Drop and recreate the database
docker compose exec postgres psql -U tennis -c "DROP DATABASE IF EXISTS tennis_coach;"
docker compose exec postgres psql -U tennis -c "CREATE DATABASE tennis_coach;"

# Run migrations
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

Key docs:

- **[Serve MVP](docs/serve-mvp.md)**
- **[Config](docs/config.md)**
- **[Background jobs](docs/background-jobs.md)**
- **[(Optional) Deploy](docs/deploy-flyio.md)**
- **[(Optional) Demo videos](docs/demo-videos.md)**

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
