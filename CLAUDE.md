# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

This is a **serve-focused tennis coaching MVP** (hobby project) with a FastAPI backend and React frontend. The application helps users upload serve videos, tag serve attempts, and get a small set of coach-meaningful metrics with one actionable recommendation.

**Current Status**: Active development on `refactor/serve-mvp-backend` branch

**Vision Alignment**: Optimizing for a focused serve-analysis loop:
- **One shot type**: serve
- **One phase**: a single named phase (keep it consistent)
- **3–5 metrics**: simple + coach-meaningful
- **One recommendation**: one high-leverage improvement (not 10)

**Out of scope (for now)**: Ball detection/trajectory, multi-shot rally analysis, complex interaction effects, annotated video generation.

## Architecture

### High-Level Structure
- **Backend**: FastAPI application with SQLAlchemy ORM, SQLite (dev) / PostgreSQL (prod), MediaPipe pose estimation
- **Frontend**: React with TypeScript, using a simple state management approach
- **Computer Vision**: MediaPipe for pose estimation (YOLO/ball detection removed for MVP focus)
- **File Storage**: Local filesystem (dev) or Supabase Storage (prod)
- **Background Processing**: Redis Queue (RQ) for pose detection and serve analysis jobs

### Key Components

#### Backend (`backend/`)
- **API Layer**: REST endpoints in `app/api/routes/` with versioned `/v0/` prefix
- **Services**: Business logic in `app/services/` including pose detection, serve analysis, and storage
- **Models**: SQLAlchemy models in `app/models/` for Video, Player, PoseDetection, and ServeAttempt
- **Background Jobs**: RQ task functions in `app/services/rq_tasks.py` (pose detection, serve analysis)
- **Computer Vision**: `app/services/pose_detection/detection_service.py` uses MediaPipe for pose estimation

#### Frontend (`frontend/`)
- **Components**: React components in `src/components/` with co-located CSS files
- **Services**: API client in `src/services/api.ts` using axios
- **State Management**: Custom hooks in `src/hooks/` for analysis and task status management
- **Main Views**: Upload, Video List, and Analysis Dashboard

#### Data Flow (Serve Loop)
1. **Upload** serve drill video → FastAPI endpoint → Local/cloud file storage
2. **Tag serve attempts** → User marks time windows + contact timestamps → Stored in `serve_attempts` table
3. **Pose detection** → RQ background job → MediaPipe pose estimation → Stored in `pose_detections` table
4. **Serve analysis** → RQ background job → Calculates metrics (e.g., elbow angle at contact) → Updates `serve_attempts` table
5. **Display** → Frontend renders small set of metrics + one recommendation

## Common Commands

### Backend Development
```bash
cd backend

# Install dependencies
pip install -e .

# Run development server
python -m uvicorn app.main:app --reload --port 8000

# Code quality (always run before committing)
ruff check .
ruff format .
ruff check --fix .

# Testing
pytest                          # Run all tests
pytest -v                       # Verbose output
pytest tests/test_specific.py   # Run specific test file
pytest --cov=app               # Run with coverage
```

### Frontend Development
```bash
cd frontend

# Install dependencies
npm install

# Run development server
npm start

# Code quality
npm run lint
npm run lint:fix
npm run format
npm run format:check
npm run type-check

# Testing
npm test                    # Interactive test runner
npm run test:coverage       # Run with coverage
npm run test:ci            # CI mode (non-interactive)

# Build
npm run build
```

### Docker Development (Recommended)
```bash
# Start all services
docker compose up --build

# Run in background
docker compose up -d

# View logs
docker compose logs -f

# Stop services
docker compose down

# Run backend tests in container
docker compose exec backend pytest

# Run frontend tests in container
docker compose exec frontend npm test
```

### Database Operations
```bash
cd backend

# Database is auto-created on startup at data/database/tennis_coach.db
# Manual migration operations (if needed):
alembic upgrade head                    # Apply migrations
alembic revision --autogenerate -m "Description"  # Create migration
```

## Code Standards

### Python (Backend)
- **Code Style**: Use `ruff format .` and `ruff check .` before committing
- **Type Hints**: Required for all function parameters and return values
- **Error Handling**: Use centralized error handling utilities, never bare `except:`
- **Pydantic v2**: Use `model_validate()` and `from_attributes = True` (not deprecated v1 patterns)
- **Database**: Keep queries simple, use SQLAlchemy ORM patterns
- **Testing**: Follow AAA pattern (Arrange, Act, Assert), mock external dependencies

### TypeScript/React (Frontend)
- **Code Style**: Use `npm run lint` and `npm run format` before committing
- **Components**: Functional components with hooks, co-located CSS files
- **API Calls**: Use the centralized API service, handle loading and error states
- **Testing**: Test user interactions and component behavior, not implementation details

### API Design
- **REST Patterns**: Resource-based URLs (`/v0/videos/{id}`, `/v0/serve-attempts/{id}`)
- **Versioning**: Use `/v0/` prefix to indicate alpha status
- **Error Handling**: Consistent error response format with specific error codes
- **File Uploads**: Validate format and size limits on server side

## Key Files and Locations

### Backend Key Files
- `backend/app/main.py` - FastAPI application setup and middleware
- `backend/app/api/routes/analysis.py` - Analysis endpoints (pose detection via RQ)
- `backend/app/api/routes/serve_attempts.py` - Serve attempt CRUD endpoints
- `backend/app/api/routes/video.py` - Video management and serve analysis trigger
- `backend/app/services/rq_tasks.py` - RQ task functions (pose detection, serve analysis)
- `backend/app/services/serve_analysis_service.py` - Serve metrics calculation (elbow angle, etc.)
- `backend/app/services/pose_detection/detection_service.py` - MediaPipe pose estimation
- `backend/app/models/serve_attempt.py` - Serve attempt model with metrics fields
- `backend/app/models/pose_detection.py` - Pose detection results model

### Frontend Key Files
- `frontend/src/App.tsx` - Main application component with view routing
- `frontend/src/components/AnalysisDashboard.tsx` - Analysis results and video display
- `frontend/src/hooks/useAnalysisManager.ts` - Analysis state management
- `frontend/src/services/api.ts` - Centralized API client

### Configuration Files
- `backend/app/core/config.py` - Application configuration (PROFILE-based)
- `backend/pyproject.toml` - Python project configuration with ruff settings
- `frontend/package.json` - Node.js dependencies and scripts
- `docker-compose.yml` - Docker development environment
- `backend/pytest.ini` - Test configuration with markers

### Documentation
- `backend/docs/README.md` - Docs index (keep it small)
- `backend/docs/serve-mvp.md` - MVP scope + workflow
- `backend/docs/config.md` - PROFILE-based configuration
- `backend/docs/background-jobs.md` - RQ background jobs
- **API Reference**: Use FastAPI OpenAPI at `http://localhost:8000/docs` (don't duplicate in docs)

## Testing Strategy

### Backend Testing
- **Unit Tests**: Mock database sessions and external dependencies
- **Integration Tests**: Use test database with FastAPI TestClient
- **Markers**: Use `@pytest.mark.unit`, `@pytest.mark.integration`, `@pytest.mark.slow`
- **Fixtures**: Shared test setup in `backend/tests/conftest.py`

### Frontend Testing
- **Component Tests**: Test user interactions using React Testing Library
- **Coverage**: Minimum thresholds configured in package.json
- **API Mocking**: Mock API calls in component tests

## Development Workflow

### Before Starting Work
1. Check current branch status: `git status`
2. Pull latest changes: `git pull origin main`
3. Start development environment: `docker compose up -d`

### During Development
1. Run code quality checks frequently: `ruff check . && ruff format .` (backend), `npm run lint` (frontend)
2. Run relevant tests: `pytest` (backend), `npm test` (frontend)
3. Test integration using the full Docker stack

### Before Committing
1. **Backend**: Run `ruff check . && ruff format . && pytest`
2. **Frontend**: Run `npm run lint && npm run type-check && npm test`
3. Ensure Docker build succeeds: `docker compose build`

### Current Branch Context
- Working on `refactor/serve-mvp-backend`
- Recent changes: Removed YOLO/ball detection, simplified docs, focused on serve MVP
- Background jobs use RQ (Redis Queue) instead of custom task system

## Computer Vision Pipeline

### Pose Estimation (MediaPipe)
- **Model**: MediaPipe Pose Landmarker Heavy (33 keypoints)
- **Tennis-specific**: Focuses on 11 relevant keypoints for serve analysis (shoulders, elbows, wrists, hips, knees, ankles)
- **Output**: Joint positions and pose landmarks stored as JSON in `pose_detections` table
- **Location**: `backend/app/services/pose_detection/detection_service.py`
- **Background Job**: `app/services/rq_tasks.py::analyze_pose_detection_rq`

### Serve Analysis
- **Input**: Pose detection data + serve attempt timestamps
- **Metrics**: Calculated values (e.g., elbow angle at contact) written to `serve_attempts` table
- **Location**: `backend/app/services/serve_analysis_service.py`
- **Background Job**: `app/services/rq_tasks.py::analyze_serve_attempts_rq`

### Background Processing (RQ)
- **System**: Redis Queue (RQ) for background job processing
- **Queues**: `analysis` queue for pose detection and serve analysis
- **Workers**: Separate RQ worker processes (can run locally or on Fly.io)
- **Configuration**: `backend/app/core/redis_config.py`
- **Monitoring**: RQ dashboard at `http://localhost:9181` (local dev)

## Configuration

### Profile-Based System
The app uses a **profile-based** config model (see `backend/docs/config.md`):

- **`PROFILE=local`**: Auth disabled, SQLite DB, local storage
- **`PROFILE=production`**: Auth required, PostgreSQL (Supabase), cloud storage

Set one `PROFILE` variable and the app selects which services/vars matter.

## Deployment

### Docker Production
- Multi-stage builds for both frontend and backend
- Nginx for frontend serving
- Environment-specific configuration via Docker Compose
- Health checks and monitoring endpoints

### Fly.io Deployment (Optional)
- Separate apps for API and Worker services
- See `backend/docs/deploy-flyio.md` for minimal deploy notes

### Local Development
- Requires Python 3.11+, Node.js 16+, FFmpeg
- SQLite database for simplicity
- Hot reload for both backend and frontend
- Redis for RQ (via Docker Compose)

## Design Principles (Aligned to Vision)

- **Keep it simple**: Fewer moving parts, fewer features, fewer docs
- **Fast iteration**: Optimize for learning, not perfection
- **Layman terms**: Prefer "outstretched arm" over raw angles in UI
- **Legible metrics**: Explain why metrics matter, not just what they are
- **One recommendation**: Focus on high-leverage improvements, not 10 suggestions

## Notes for AI Assistants

- **Prefer code over docs**: When in doubt, read the code (`app/models/`, `app/api/routes/`)
- **Use OpenAPI docs**: Don't duplicate API details; point to `http://localhost:8000/docs`
- **Keep docs minimal**: Only document what's hard to infer from code
- **Serve MVP focus**: Don't add ball detection, rally analysis, or other out-of-scope features
- **Profile system**: Understand `PROFILE` determines which env vars are used/required
