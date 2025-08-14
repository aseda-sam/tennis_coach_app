# Tennis Coach App

[![CI](https://github.com/aseda-sam/tennis_coach_app/actions/workflows/ci.yml/badge.svg?branch=main)](https://github.com/aseda-sam/tennis_coach_app/actions/workflows/ci.yml)
[![Deploy Frontend](https://github.com/aseda-sam/tennis_coach_app/actions/workflows/deploy-frontend.yml/badge.svg?branch=main)](https://github.com/aseda-sam/tennis_coach_app/actions/workflows/deploy-frontend.yml)
[![Publish Backend Docker Image](https://github.com/aseda-sam/tennis_coach_app/actions/workflows/docker-publish.yml/badge.svg?branch=main)](https://github.com/aseda-sam/tennis_coach_app/actions/workflows/docker-publish.yml)
[![Trivy Security Scan](https://github.com/aseda-sam/tennis_coach_app/actions/workflows/trivy.yml/badge.svg?branch=main)](https://github.com/aseda-sam/tennis_coach_app/actions/workflows/trivy.yml)
[![License: MIT](https://img.shields.io/badge/License-MIT-green.svg)](LICENSE)
[![Code Style: Ruff](https://img.shields.io/badge/code%20style-ruff-4B8BBE.svg)](https://github.com/astral-sh/ruff)
[![PRs Welcome](https://img.shields.io/badge/PRs-welcome-brightgreen.svg)](CONTRIBUTING.md)

A computer vision-based tennis coaching platform. Currently implements a backend for video upload, analysis and management, with a React frontend for user interaction.

## Features

- **Video Upload & Playback**: Upload tennis videos and watch them directly in the browser
- **Video Library Management**: Organize and manage your tennis video collection with easy browsing
- **Ball Detection Analysis**: Automatically detect and track tennis balls in your videos using YOLO
- **Pose Estimation**: Advanced player pose detection using MediaPipe for stroke analysis
- **Annotated Video Creation**: Generate videos with pose and ball detection overlays
- **Smart Video Player**: Automatically displays annotated videos when analysis is available
- **Analysis Dashboard**: View detailed statistics about ball and pose detection performance
- **Progress Tracking**: Monitor analysis progress and completion status in real-time

## Quick Start

### Option 1: Docker Development (Recommended)

**Prerequisites**: Docker and Docker Compose

1. **Clone and Setup**
```bash
git clone https://github.com/aseda-sam/tennis_coach_app.git
cd tennis_coach_app
```

2. **Start All Services**
```bash
docker compose up --build
```

3. **Access the Application**
- **Frontend**: http://localhost:3000
- **Backend API**: http://localhost:8000
- **API Documentation**: http://localhost:8000/docs
- **Health Check**: http://localhost:8000/health

### Option 2: Local Development

**Prerequisites**: Python 3.11+, Node.js 16+, FFmpeg

1. **Install FFmpeg** (required for video processing):
```bash
# macOS
brew install ffmpeg

# Ubuntu/Debian
sudo apt install ffmpeg

# Windows (using chocolatey)
choco install ffmpeg
```

2. **Setup Backend**
```bash
# Create Python virtual environment
python3 -m venv venv
source venv/bin/activate

# Install backend dependencies
cd backend
pip install -e .
cd ..
```

3. **Setup Frontend**
```bash
# Install frontend dependencies
cd frontend
npm install
cd ..
```

4. **Run Backend Server**
```bash
cd backend
python -m uvicorn app.main:app --reload --port 8000
```

5. **Run Frontend Development Server** (in a new terminal)
```bash
cd frontend
npm start
```

6. **Access the Application**
- **Frontend**: http://localhost:3000
- **Backend API**: http://localhost:8000
- **API Documentation**: http://localhost:8000/docs
- **Health Check**: http://localhost:8000/health

## Project Structure

```
tennis_coach_app/
├── backend/                 # FastAPI backend
│   ├── app/
│   │   ├── api/            # API routes and schemas
│   │   ├── core/           # Configuration and database
│   │   ├── services/       # Business logic
│   │   └── models/         # Database models
│   ├── pyproject.toml      # Python project configuration
│   ├── tests/              # Backend tests
│   └── README.md           # Backend documentation
├── frontend/               # React frontend
│   ├── src/
│   │   ├── components/     # React components
│   │   ├── services/       # API service layer
│   │   └── types/          # TypeScript type definitions
│   ├── public/             # Static assets
│   └── README.md           # Frontend documentation
├── project_docs/           # Project documentation
├── docker-compose.yml      # Docker development setup
├── Dockerfile              # Backend container
└── README.md               # This file
```

## Tech Stack

- **Backend**: FastAPI (Python)
- **Frontend**: React with TypeScript
- **Database**: SQLite with SQLAlchemy ORM
- **Computer Vision**: YOLO (ball detection) + MediaPipe (pose estimation)
- **File Storage**: Local file system
- **Validation**: Pydantic models
- **Code Quality**: Ruff linting and formatting
- **Video Processing**: OpenCV with H.264 codec

## Analysis Capabilities

### Ball Detection
- **YOLO Integration**: Uses YOLOv8n for efficient ball detection
- **Real-time Processing**: Processes video frames for ball tracking
- **Detection Metrics**: Tracks total detections, frames with balls, detection rate
- **Visual Overlays**: Red bounding boxes around detected balls

### Pose Estimation
- **MediaPipe Integration**: Advanced pose detection with 33 keypoints
- **Tennis-Focused**: Extracts 11 relevant keypoints (shoulders, elbows, wrists, hips, knees, ankles)
- **Stroke Analysis**: Tracks upper body mechanics and lower body positioning
- **Visual Overlays**: Green skeleton lines and blue joint markers

### Progress Tracking
- **Status Monitoring**: Track analysis progress (processing/completed/failed)
- **Progress Percentage**: Real-time completion percentage (0-100)
- **Timing Information**: Creation and completion timestamps
- **API Endpoint**: `GET /v0/analysis/status/{analysis_id}` for status updates

### Annotated Videos
- **Combined Overlays**: Pose and ball detection on same video
- **H.264 Codec**: Browser-compatible video format
- **Smart Playback**: Automatically shows annotated version when available
- **No Audio**: Silent videos optimized for analysis

## Documentation

### Development Guides
- **[Backend Guide](backend/README.md)** - Setup, API, testing, deployment
- **[Frontend Guide](frontend/README.md)** - Components, testing, build process

### Project Documentation
- **[API Reference](project_docs/api_reference.md)** - API endpoints and usage guide
- **[Database Schema](project_docs/database_schema.md)** - Database models and relationships
- **[Deployment Guide](project_docs/deployment_guide.md)** - Production deployment instructions
- **[Project Roadmap](project_docs/project_plan.md)** - Development phases and future plans
- **[Pose Estimation Comparison](project_docs/pose_estimation_comparison.md)** - Technology decision record

## Development

### Docker Development (Recommended)

```bash
# Start all services
docker compose up --build

# Start in background
docker compose up -d

# View logs
docker compose logs -f

# Stop services
docker compose down

# Rebuild and restart
docker compose up --build --force-recreate

# Run backend tests
docker compose exec backend pytest

# Run frontend tests
docker compose exec frontend npm test

# Access backend shell
docker compose exec backend bash

# Access frontend shell
docker compose exec frontend sh
```

### Local Development

#### Backend Development
```bash
cd backend

# Run development server
python -m uvicorn app.main:app --reload

# Run code formatting
ruff format .

# Run linting
ruff check .

# Run tests
pytest
```

#### Frontend Development
```bash
cd frontend

# Run development server
npm start

# Build for production
npm run build

# Run tests
npm test
```

### Database Operations
```bash
# Database is automatically created on startup
# Located at: data/database/tennis_coach.db

# Manual database operations (if needed)
cd backend
alembic upgrade head  # Apply migrations
alembic revision --autogenerate -m "Description"  # Create new migration
```

## Contributing

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Make your changes
4. Add tests if applicable
5. Run code quality checks:
   - Backend: `ruff check . && ruff format .`
   - Frontend: `npm run lint && npm test`
6. Submit a pull request

## License

MIT License

---

**Built with Aseda's ❤️ for tennis and software engineering**
