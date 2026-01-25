# Tennis Coach App

[![CI](https://github.com/aseda-sam/tennis_coach_app/actions/workflows/ci.yml/badge.svg?branch=main)](https://github.com/aseda-sam/tennis_coach_app/actions/workflows/ci.yml)
[![Deploy Frontend](https://github.com/aseda-sam/tennis_coach_app/actions/workflows/deploy-frontend.yml/badge.svg?branch=main)](https://github.com/aseda-sam/tennis_coach_app/actions/workflows/deploy-frontend.yml)
[![Publish Backend Docker Image](https://github.com/aseda-sam/tennis_coach_app/actions/workflows/docker-publish.yml/badge.svg?branch=main)](https://github.com/aseda-sam/tennis_coach_app/actions/workflows/docker-publish.yml)
[![Trivy Security Scan](https://github.com/aseda-sam/tennis_coach_app/actions/workflows/trivy.yml/badge.svg?branch=main)](https://github.com/aseda-sam/tennis_coach_app/actions/workflows/trivy.yml)
[![License: MIT](https://img.shields.io/badge/License-MIT-green.svg)](LICENSE)
[![Code Style: Ruff](https://img.shields.io/badge/code%20style-ruff-4B8BBE.svg)](https://github.com/astral-sh/ruff)
[![PRs Welcome](https://img.shields.io/badge/PRs-welcome-brightgreen.svg)](CONTRIBUTING.md)

A tennis coaching app (hobby project) focused on a **serve-analysis MVP**: upload a serve video, tag serve attempts, compute a small set of coach-meaningful metrics, and return one recommendation.

## 🎾 What It Does

- **User accounts** with secure authentication
- **Upload videos** and tag **serve attempts**
- **Pose estimation** (MediaPipe) for biomechanics signals
- **Serve metrics** computed from pose at key timestamps
- **Background job processing** (Redis Queue / RQ)
- **Real-time dashboard** with progress tracking

## 🚀 Quick Start

### Option 1: Docker (Recommended)

```bash
git clone https://github.com/aseda-sam/tennis_coach_app.git
cd tennis_coach_app
docker compose up --build
```

**Access the app:**

- Frontend: http://localhost:3000
- Backend API: http://localhost:8000
- API Docs: http://localhost:8000/docs
- RQ Dashboard (Background Jobs): http://localhost:9181

### Option 2: Local Development

**Prerequisites:** Python 3.11+, Node.js 16+, FFmpeg

**Note:** For local development, authentication can be disabled. See the [Backend README](backend/README.md) and [Frontend README](frontend/README.md) for environment variable configuration.

```bash
# Backend
cd backend
python -m venv venv
source venv/bin/activate
pip install -e .
python -m uvicorn app.main:app --reload

# Frontend (new terminal)
cd frontend
npm install
npm start
```

## 🏗️ Architecture

```
tennis_coach_app/
├── backend/          # FastAPI + Computer Vision
├── frontend/         # React + TypeScript
├── backend/ml_models/  # MediaPipe pose model (auto-downloaded)
└── project_docs/     # Local implementation notes (not in git)
```

**Tech Stack:**

- **Backend**: FastAPI, SQLAlchemy, MediaPipe, RQ
- **Frontend**: React, TypeScript, HTML5 Video
- **Database**: SQLite (dev) → PostgreSQL (prod)
- **Authentication**: JWT-based (configurable provider)
- **Deployment**: Docker, GitHub Actions

## 📚 Documentation

### Development Guides

- **[Backend Setup](backend/README.md)** - Backend development and API
- **[Frontend Setup](frontend/README.md)** - Frontend development and components

### Detailed Documentation

- **[Backend docs index](backend/docs/README.md)** - Serve MVP, config, background jobs, deploy notes
- **[Frontend Components](frontend/docs/components.md)** - Component documentation
- **[Frontend API Integration](frontend/docs/api-integration.md)** - API communication

### Project Documentation

> **Note:** Implementation plans and working documents are stored locally in `project_docs/` (not tracked in git). For operational documentation, see `backend/docs/`.

### Interactive API Documentation

- **Swagger UI**: http://localhost:8000/docs
- **ReDoc**: http://localhost:8000/redoc

## 🧪 Development

```bash
# Run tests
cd backend && pytest
cd frontend && npm test

# Code quality
cd backend && ruff check . && ruff format .
cd frontend && npm run lint

# Docker development
docker compose up --build
docker compose exec backend pytest
docker compose exec frontend npm test
```

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Make your changes
4. Add tests if applicable
5. Run code quality checks
6. Submit a pull request

## 📄 License

MIT License

---
