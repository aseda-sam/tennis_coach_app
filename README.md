# Tennis Computer Vision Analysis System

A computer vision-based tennis analysis system that demonstrates data engineering and AI evaluation skills. Currently implements a robust backend for video upload and management, with a React frontend for user interaction.

## 🎾 Current Features

- **Video Upload & Management**: Secure file upload with validation and metadata extraction
- **Database Integration**: SQLite database with comprehensive video metadata storage
- **RESTful API**: FastAPI backend with full CRUD operations
- **React Frontend**: Modern web interface for video management and analysis
- **Computer Vision Analysis**: Ball detection and analysis using YOLO models
- **File Management**: List, view details, and delete uploaded videos
- **Error Handling**: Comprehensive validation and error responses
- **Documentation**: Complete API documentation and testing guides

## 🚀 Quick Start

### Prerequisites
- Python 3.8+
- Node.js 16+ (for frontend)

### Local Development

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

## 🔧 Development

### Backend Development
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

### Frontend Development
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

**Built with ❤️ for tennis and data engineering** 