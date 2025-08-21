# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

This is a computer vision-based tennis coaching platform with a FastAPI backend and React frontend. The application processes tennis videos to detect ball positions and player poses, generating annotated videos and analysis reports.

**Current Status**: Active development on `feature/improved-contact-detection` branch

## Architecture

### High-Level Structure
- **Backend**: FastAPI application with SQLAlchemy ORM, SQLite database, and computer vision services
- **Frontend**: React with TypeScript, using a simple state management approach
- **Computer Vision**: YOLO for ball detection, MediaPipe for pose estimation
- **File Storage**: Local filesystem for video files and processed outputs
- **Background Processing**: Custom background service for video analysis tasks

### Key Components

#### Backend (`backend/`)
- **API Layer**: REST endpoints in `app/api/routes/` with versioned `/v0/` prefix
- **Services**: Business logic in `app/services/` including CV processing, analysis, and background tasks
- **Models**: SQLAlchemy models in `app/models/` for Video and Analysis entities
- **Background Service**: Custom task queue system for video processing in `app/services/background_service.py`
- **Computer Vision**: `app/services/cv_service.py` orchestrates YOLO ball detection and MediaPipe pose estimation

#### Frontend (`frontend/`)
- **Components**: React components in `src/components/` with co-located CSS files
- **Services**: API client in `src/services/api.ts` using axios
- **State Management**: Custom hooks in `src/hooks/` for analysis and task status management
- **Three Main Views**: Upload, Video List, and Analysis Dashboard

#### Data Flow
1. Video upload → FastAPI endpoint → Local file storage
2. Analysis request → Background service → CV pipeline (YOLO + MediaPipe)
3. Results stored in database → Annotated video generated
4. Frontend polls for status → Displays results and annotated video

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
- **REST Patterns**: Resource-based URLs (`/v0/videos/{id}`, `/v0/analysis/{id}`)
- **Versioning**: Use `/v0/` prefix to indicate alpha status
- **Error Handling**: Consistent error response format with specific error codes
- **File Uploads**: Validate format and size limits on server side

## Key Files and Locations

### Backend Key Files
- `backend/app/main.py` - FastAPI application setup and middleware
- `backend/app/api/routes/analysis.py:43` - Analysis endpoints with background processing
- `backend/app/services/background_service.py:1` - Task queue and background job management
- `backend/app/services/cv_service.py:1` - Computer vision pipeline orchestration
- `backend/app/services/analysis_service.py:22` - Analysis business logic and database operations
- `backend/app/models/analysis.py` - Analysis data model with ball contact detection fields

### Frontend Key Files
- `frontend/src/App.tsx:8` - Main application component with view routing
- `frontend/src/components/AnalysisDashboard.tsx` - Analysis results and video display
- `frontend/src/hooks/useAnalysisManager.ts` - Analysis state management
- `frontend/src/services/api.ts` - Centralized API client

### Configuration Files
- `backend/pyproject.toml` - Python project configuration with ruff settings
- `frontend/package.json` - Node.js dependencies and scripts
- `docker-compose.yml` - Docker development environment
- `backend/pytest.ini` - Test configuration with markers

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
- Working on `feature/improved-contact-detection`
- Recent changes include ball contact detection improvements and task logging
- Several debug/test files exist for contact detection development

## Computer Vision Pipeline

### Ball Detection (YOLO)
- Model: YOLOv8n (lightweight, fast detection)
- Input: Video frames
- Output: Bounding boxes with confidence scores
- Location: `backend/app/services/cv_service.py`

### Pose Estimation (MediaPipe)
- Model: MediaPipe Pose with 33 keypoints
- Tennis-specific: Focuses on 11 relevant keypoints for stroke analysis
- Output: Joint positions and pose landmarks
- Integration: Combined with ball detection for comprehensive analysis

### Background Processing
- Custom task queue system (not Celery)
- Handles long-running video analysis jobs
- Progress tracking and status updates
- Error handling and retry logic

## Deployment

### Docker Production
- Multi-stage builds for both frontend and backend
- Nginx for frontend serving
- Environment-specific configuration via Docker Compose
- Health checks and monitoring endpoints

### Local Development
- Requires Python 3.11+, Node.js 16+, FFmpeg
- SQLite database for simplicity
- Hot reload for both backend and frontend