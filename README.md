# Tennis Coach App

[![CI](https://github.com/aseda-sam/tennis_coach_app/actions/workflows/ci.yml/badge.svg?branch=main)](https://github.com/aseda-sam/tennis_coach_app/actions/workflows/ci.yml)
[![Deploy Frontend](https://github.com/aseda-sam/tennis_coach_app/actions/workflows/deploy-frontend.yml/badge.svg?branch=main)](https://github.com/aseda-sam/tennis_coach_app/actions/workflows/deploy-frontend.yml)
[![Publish Backend Docker Image](https://github.com/aseda-sam/tennis_coach_app/actions/workflows/docker-publish.yml/badge.svg?branch=main)](https://github.com/aseda-sam/tennis_coach_app/actions/workflows/docker-publish.yml)
[![Trivy Security Scan](https://github.com/aseda-sam/tennis_coach_app/actions/workflows/trivy.yml/badge.svg?branch=main)](https://github.com/aseda-sam/tennis_coach_app/actions/workflows/trivy.yml)
[![License: MIT](https://img.shields.io/badge/License-MIT-green.svg)](LICENSE)
[![Code Style: Ruff](https://img.shields.io/badge/code%20style-ruff-4B8BBE.svg)](https://github.com/astral-sh/ruff)
[![PRs Welcome](https://img.shields.io/badge/PRs-welcome-brightgreen.svg)](CONTRIBUTING.md)

A computer vision-based tennis coaching platform that analyzes your tennis videos to provide insights on ball tracking, pose estimation, and stroke analysis.

## 🎾 What It Does

- **Upload tennis videos** and get instant analysis
- **Ball detection** using YOLO computer vision
- **Pose estimation** with MediaPipe for stroke analysis
- **Manual ball contact marking** for precise timing analysis
- **Annotated video generation** with AI overlays
- **Real-time analysis dashboard** with progress tracking

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

### Option 2: Local Development

**Prerequisites:** Python 3.11+, Node.js 16+, FFmpeg

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
├── ml_models/        # YOLO models
└── project_docs/     # Project documentation
```

**Tech Stack:**

- **Backend**: FastAPI, SQLAlchemy, YOLO, MediaPipe
- **Frontend**: React, TypeScript, HTML5 Video
- **Database**: SQLite (dev) → PostgreSQL (prod)
- **Deployment**: Docker, GitHub Actions

## 📚 Documentation

### Development Guides

- **[Backend Setup](backend/README.md)** - Backend development and API
- **[Frontend Setup](frontend/README.md)** - Frontend development and components

### Detailed Documentation

- **[Backend API](backend/docs/api.md)** - Complete API reference
- **[Backend Database](backend/docs/database.md)** - Database schema and models
- **[Backend Configuration](backend/docs/configuration.md)** - Environment variables
- **[Backend Deployment](backend/docs/deployment.md)** - Production deployment
- **[Frontend Components](frontend/docs/components.md)** - Component documentation
- **[Frontend API Integration](frontend/docs/api-integration.md)** - API communication
- **[ML Models](ml_models/README.md)** - Machine learning models and usage

### Project Documentation

- **[Architecture](project_docs/backend_architecture_improvements.md)** - System architecture and improvements

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

**Built with ❤️ for tennis and software engineering**
