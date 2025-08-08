# Tennis Computer Vision Analysis System

A computer vision-based tennis analysis system that demonstrates data engineering and AI evaluation skills. Currently implements a robust backend for video upload and management, with a React frontend for user interaction.

## CI/CD Status

- [![CI](https://github.com/aseda-sam/tennis_coach_app/workflows/CI/badge.svg)](https://github.com/aseda-sam/tennis_coach_app/actions)
- [![Deploy Frontend](https://github.com/aseda-sam/tennis_coach_app/workflows/Deploy%20Frontend/badge.svg)](https://github.com/aseda-sam/tennis_coach_app/actions)
- [![Docker](https://github.com/aseda-sam/tennis_coach_app/workflows/Publish%20Backend%20Docker%20Image/badge.svg)](https://github.com/aseda-sam/tennis_coach_app/actions)

## 🎾 Current Features

- **Video Upload & Playback**: Upload tennis videos and watch them directly in the browser
- **Video Library Management**: Organize and manage your tennis video collection with easy browsing
- **Ball Detection Analysis**: Automatically detect and track tennis balls in your videos
- **Analysis Dashboard**: View detailed statistics about ball detection performance and video processing
- **Real-time Processing**: Get instant feedback on analysis progress and results
- **Cross-platform Access**: Use the web interface from any device with a modern browser
- **Secure File Handling**: Your videos are processed locally with no external data sharing

## 🚀 Quick Start

### Option 1: Docker Development (Recommended)

**Prerequisites**: Docker and Docker Compose

1. **Clone and Setup**
```bash
git clone <repository-url>
cd tennis_coach_app_2
```

2. **Start All Services**
```bash
docker-compose up --build
```

3. **Access the Application**
- **Frontend**: http://localhost:3000
- **Backend API**: http://localhost:8000
- **API Documentation**: http://localhost:8000/docs
- **Health Check**: http://localhost:8000/health

### Option 2: Local Development

**Prerequisites**: Python 3.8+, Node.js 16+

1. **Clone and Setup**
```bash
git clone <repository-url>
cd tennis_coach_app_2

# Create Python virtual environment
python3 -m venv venv
source venv/bin/activate
```

2. **Install Backend Dependencies**
```bash
pip install -e .
```

3. **Install Frontend Dependencies**
```bash
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

## 📁 Project Structure

```
tennis_coach_app_2/
├── backend/                 # FastAPI backend
│   ├── app/
│   │   ├── api/            # API routes and models
│   │   ├── core/           # Configuration and database
│   │   ├── services/       # Business logic
│   │   └── models/         # Database models
│   └── data/               # Local data storage
├── frontend/               # React frontend
│   ├── src/
│   │   ├── components/     # React components
│   │   ├── services/       # API service layer
│   │   └── types/          # TypeScript type definitions
│   └── public/             # Static assets
├── project_docs/           # Project documentation
├── pyproject.toml          # Python project configuration
└── README.md               # This file
```

## 🛠 Tech Stack

- **Backend**: FastAPI (Python)
- **Frontend**: React with TypeScript
- **Database**: SQLite with SQLAlchemy ORM
- **File Storage**: Local file system
- **Validation**: Pydantic models
- **Code Quality**: Ruff linting and formatting

## 📊 API Endpoints

### Video Management
- `GET /api/videos/` - List all uploaded videos
- `GET /api/videos/{filename}` - Get video details
- `POST /api/videos/upload` - Upload new video
- `DELETE /api/videos/{filename}` - Delete video

### Analysis
- `POST /api/analysis/{video_filename}` - Start analysis for a video
- `GET /api/analysis/{video_filename}` - Get analysis results
- `GET /api/analysis/` - List all analyses
- `DELETE /api/analysis/{video_filename}` - Delete analysis results

### Health & Status
- `GET /` - API information
- `GET /health` - Health check

### Documentation & Static Files
- `GET /docs` - Interactive API documentation (Swagger UI)
- `GET /redoc` - Alternative API documentation (ReDoc)
- `GET /processed/{filename}` - Access processed video files

## 🎯 Project Highlights

This project demonstrates:
- **FastAPI Development**: RESTful API with proper error handling
- **React Frontend**: Modern web interface with TypeScript
- **Database Design**: SQLAlchemy ORM with comprehensive schema
- **Computer Vision**: YOLO-based ball detection and analysis
- **File Management**: Secure file upload with validation
- **Code Quality**: Type hints, linting, and comprehensive testing
- **Documentation**: Professional project documentation and guides

## 📚 Documentation

- [Project Plan](project_docs/project_plan.md)
- [API Documentation](project_docs/api_documentation.md)
- [Database Schema](project_docs/database_schema.md)
- [Testing Guide](project_docs/testing_guide.md)
- [React Frontend Guide](project_docs/react_frontend_guide.md)
- [Deployment Guide](project_docs/deployment_guide.md)

## 🚀 Deployment

### Live Applications
- **Frontend**: [GitHub Pages](https://aseda-sam.github.io/tennis_coach_app/)
- **Backend API**: Available as Docker image at `ghcr.io/aseda-sam/tennis_coach_app/backend:latest`

### Container Deployment
```bash
# Pull and run the backend container
docker pull ghcr.io/aseda-sam/tennis_coach_app/backend:latest
docker run -p 8000:8000 ghcr.io/aseda-sam/tennis_coach_app/backend:latest
```

## 🔧 Development

### Docker Development (Recommended)

```bash
# Start all services
docker-compose up --build

# Start in background
docker-compose up -d

# View logs
docker-compose logs -f

# Stop services
docker-compose down

# Rebuild and restart
docker-compose up --build --force-recreate

# Run backend tests
docker-compose exec backend pytest

# Run frontend tests
docker-compose exec frontend npm test

# Access backend shell
docker-compose exec backend bash

# Access frontend shell
docker-compose exec frontend sh
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

# Run tests (when implemented)
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
# Located at: data/database/tennis_analysis.db
```

## 🤝 Contributing

1. Fork the repository from main
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Make your changes
4. Add tests if applicable
5. Submit a pull request

## 📄 License

MIT License

---

**Built with Aseda's ❤️ for tennis and software engineering** 