# Tennis Computer Vision Analysis System

## Project Overview

A computer vision-based tennis analysis system that demonstrates data engineering and AI evaluation skills. The system processes tennis videos to extract meaningful insights about player performance, ball trajectory, and court positioning.

### Key Features (MVP)
- **Video Upload & Processing**: Batch analysis of tennis video clips (30-60 seconds)
- **Ball Tracking**: YOLO-based ball detection with trajectory analysis
- **Player Positioning**: MediaPipe pose estimation for court position analysis
- **Stroke Detection**: Basic forehand identification and analysis
- **Metrics Dashboard**: Visualization of key tennis performance metrics
- **Historical Analysis**: Store and compare analysis results over time

### Tech Stack
- **Backend**: FastAPI (Python)
- **Frontend**: React (Simple, portfolio-focused)
- **Computer Vision**: YOLO + MediaPipe
- **Database**: SQLite (MVP) → PostgreSQL (later)
- **Storage**: Local file system → S3/MinIO (later)
- **Processing**: Batch processing with background tasks

## Project Architecture

### Data Pipeline Flow
```
Video Upload → Frame Extraction → CV Analysis → Metrics Calculation → Results Storage → Frontend Display
```

### Core Components
1. **Video Processing Engine**: Handles video upload, frame extraction, and analysis
2. **Computer Vision Pipeline**: YOLO for ball detection, MediaPipe for pose estimation
3. **Analysis Engine**: Calculates tennis-specific metrics and insights
4. **Data Storage**: SQLite for structured analysis results
5. **Web Interface**: Simple React frontend for upload and results display

## Database Schema

### Tables
- **videos**: Video metadata and processing status
- **analysis_results**: Main analysis data with JSON columns for flexibility
- **player_positions**: Time-series position data
- **stroke_events**: Stroke detection events with timestamps
- **metrics_summary**: Aggregated performance metrics

### Key Metrics Tracked
- Ball trajectory and speed
- Player court positioning (baseline vs service line)
- Stroke count and types
- Rally duration and patterns
- Court coverage heatmaps

## Implementation Plan

### Week 1: Foundation & Core Pipeline

#### Days 1-2: Project Setup & Basic Infrastructure
- [ ] Set up FastAPI project structure
- [ ] Create basic video upload endpoint
- [ ] Implement simple file storage system
- [ ] Set up SQLite database with schema
- [ ] Create basic React frontend for video upload

#### Days 3-4: Computer Vision Pipeline Foundation
- [ ] Integrate YOLO for ball detection
- [ ] Set up MediaPipe for pose estimation
- [ ] Create basic video processing pipeline
- [ ] Implement frame extraction and analysis

#### Days 5-7: Core Analysis Features
- [ ] Ball trajectory tracking and analysis
- [ ] Basic stroke detection (forehand focus)
- [ ] Court position analysis (baseline vs service line)
- [ ] Store analysis results in database

### Week 2: Enhancement & Polish

#### Days 8-10: Advanced Analysis & Metrics
- [ ] Implement stroke speed calculation
- [ ] Add rally duration analysis
- [ ] Create player positioning heatmaps
- [ ] Develop basic tennis metrics (stroke count, court coverage)

#### Days 11-12: Frontend & Visualization
- [ ] Create analysis results display
- [ ] Add simple charts/graphs for metrics
- [ ] Implement video playback with overlay
- [ ] Polish UI/UX for portfolio presentation

#### Days 13-14: Testing & Documentation
- [ ] End-to-end testing
- [ ] Create comprehensive README
- [ ] Prepare portfolio documentation
- [ ] Final polish and bug fixes

## Project Structure

```
tennis_coach_app_2/
├── backend/
│   ├── app/
│   │   ├── __init__.py
│   │   ├── main.py
│   │   ├── api/
│   │   │   ├── __init__.py
│   │   │   ├── routes/
│   │   │   │   ├── __init__.py
│   │   │   │   ├── video.py
│   │   │   │   └── analysis.py
│   │   │   └── models/
│   │   │       ├── __init__.py
│   │   │       └── database.py
│   │   ├── core/
│   │   │   ├── __init__.py
│   │   │   ├── config.py
│   │   │   └── database.py
│   │   ├── services/
│   │   │   ├── __init__.py
│   │   │   ├── video_processor.py
│   │   │   ├── cv_pipeline.py
│   │   │   └── analysis_engine.py
│   │   └── utils/
│   │       ├── __init__.py
│   │       └── helpers.py
│   ├── requirements.txt
│   └── alembic/
│       └── versions/
├── frontend/
│   ├── public/
│   ├── src/
│   │   ├── components/
│   │   ├── pages/
│   │   └── utils/
│   ├── package.json
│   └── README.md
├── data/
│   ├── videos/
│   │   ├── raw/
│   │   └── processed/
│   ├── database/
│   └── analysis_cache/
├── project_docs/
│   ├── README.md
│   ├── api_documentation.md
│   ├── database_schema.md
│   └── deployment_guide.md
├── tests/
│   ├── backend/
│   └── frontend/
├── docker-compose.yml
├── Dockerfile
└── README.md
```

## Success Metrics

### Technical Goals
- [ ] Process 30-60 second tennis videos successfully
- [ ] Detect and track tennis ball with 80%+ accuracy
- [ ] Identify player position on court correctly
- [ ] Detect forehand strokes with reasonable accuracy
- [ ] Generate meaningful tennis performance metrics

### Portfolio Goals
- [ ] Clean, well-documented codebase
- [ ] Demonstrates data engineering best practices
- [ ] Shows computer vision pipeline development
- [ ] Scalable architecture design
- [ ] Professional project presentation

## Future Enhancements

### Phase 2 Features
- Backhand and serve detection
- Real-time processing capabilities
- Advanced stroke analysis (spin, power)
- Player comparison features
- Cloud deployment with S3/PostgreSQL

### Phase 3 Features
- Real-time coaching feedback
- Multi-player analysis
- Tournament-level analytics
- Mobile app integration
- AI-powered stroke improvement suggestions

## Development Guidelines

### Code Standards
- Use type hints in Python
- Follow FastAPI best practices
- Implement proper error handling
- Write comprehensive tests
- Document all API endpoints

### Data Engineering Best Practices
- Implement proper data validation
- Use database migrations
- Handle large file uploads efficiently
- Implement background task processing
- Design scalable data models

### Computer Vision Pipeline
- Use pre-trained models for efficiency
- Implement proper frame processing
- Handle video format variations
- Optimize for processing speed
- Implement result caching

## Getting Started

### Prerequisites
- Python 3.8+
- Node.js 16+
- M1 MacBook Pro (GPU acceleration available)

### Quick Start
1. Clone the repository
2. Set up backend environment
3. Install frontend dependencies
4. Run database migrations
5. Start development servers

### Development Commands
```bash
# Backend
cd backend
pip install -r requirements.txt
uvicorn app.main:app --reload

# Frontend
cd frontend
npm install
npm start

# Database
alembic upgrade head
```

## Portfolio Presentation

### GitHub Repository
- Comprehensive README
- Clear project structure
- Well-documented code
- Demo videos/screenshots
- Technical blog post

### Resume/CV Highlights
- Computer vision pipeline development
- Data engineering with FastAPI
- Real-time video processing
- Machine learning integration
- Full-stack development

### YouTube Video Content
- Project overview and demo
- Technical implementation details
- Code walkthrough
- Lessons learned
- Future roadmap 