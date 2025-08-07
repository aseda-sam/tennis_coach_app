# Tennis Computer Vision Analysis System

## Project Overview

A computer vision-based tennis analysis system that demonstrates data engineering and AI evaluation skills. The system processes tennis videos to extract meaningful insights about player performance, ball trajectory, and court positioning.

### Key Features (MVP)
- **Video Upload & Processing**: Upload tennis videos and extract basic metadata
- **Ball Tracking**: YOLO-based ball detection with trajectory analysis
- **Player Positioning**: MediaPipe pose estimation for court position analysis
- **Stroke Detection**: Basic forehand identification and analysis
- **Metrics Dashboard**: Visualization of key tennis performance metrics

### Tech Stack
- **Backend**: FastAPI (Python)
- **Frontend**: React (Simple, portfolio-focused)
- **Computer Vision**: YOLO + MediaPipe
- **Database**: SQLite (MVP) → PostgreSQL (later)
- **Storage**: Local file system → S3/MinIO (later)

## Implementation Steps

### Phase 1: Basic Video Upload & File Management

#### Step 1: Basic FastAPI Setup ✅
- [x] Set up FastAPI project structure
- [x] Create basic configuration
- [x] Test server startup and health checks

#### Step 2: Simple Video Upload ✅
- [x] Create video upload endpoint
- [x] Add file validation (size, format)
- [x] Test upload functionality
- [x] Verify file storage

#### Step 3: Video File Information ✅
- [x] Extract video metadata (duration, resolution, fps)
- [x] Display video information after upload
- [x] Test with different video formats

#### Step 4: File Management ✅
- [x] List uploaded videos endpoint
- [x] Delete video endpoint
- [x] Get video details endpoint

### Phase 2: Database Integration

#### Step 5: Database Setup ✅
- [x] Set up SQLite database
- [x] Create video metadata table
- [x] Store video information in database

#### Step 6: Video Management with Database ✅
- [x] Update upload to save to database
- [x] List videos from database
- [x] Delete videos from database and file system

### Phase 3: Frontend Development

#### Step 7: Basic React Setup
- [ ] Set up React frontend
- [ ] Create video upload component
- [ ] Display uploaded videos list

#### Step 8: Analysis Display
- [ ] Show analysis results
- [ ] Basic charts for metrics
- [ ] Video playback with overlay

### Phase 4: Computer Vision Foundation

#### Step 9: Basic Video Processing
- [ ] Add OpenCV for video frame extraction
- [ ] Extract frames from uploaded videos
- [ ] Test frame processing performance

#### Step 10: YOLO Integration
- [ ] Add YOLO model for object detection
- [ ] Test ball detection on sample frames
- [ ] Optimize detection performance

#### Step 11: MediaPipe Integration
- [ ] Add MediaPipe for pose estimation
- [ ] Test player detection on sample frames
- [ ] Extract basic pose data

### Phase 5: Analysis Pipeline

#### Step 12: Basic Analysis Engine
- [ ] Process video frames with CV models
- [ ] Store analysis results in database
- [ ] Calculate basic metrics (stroke count, court position)

#### Step 13: Analysis Results
- [ ] Create analysis results endpoint
- [ ] Display basic tennis metrics
- [ ] Test end-to-end analysis pipeline

### Phase 6: Enhancement & Polish

#### Step 14: Advanced Features
- [ ] Stroke type detection (forehand/backhand)
- [ ] Rally duration analysis
- [ ] Court coverage heatmaps

#### Step 15: Testing & Documentation
- [ ] End-to-end testing
- [ ] API documentation
- [ ] README updates

## Current Status

**Completed:**
- ✅ Basic FastAPI server setup
- ✅ Video upload endpoint with validation
- ✅ File storage system
- ✅ Error handling for file size and format
- ✅ Video metadata extraction (duration, resolution, fps)
- ✅ File management endpoints (list, delete, get details)

**Next Step:**
- Phase 3: Frontend Development (React app for video upload and management)

## Success Metrics

### Technical Goals
- Process tennis videos successfully
- Detect and track tennis ball with reasonable accuracy
- Identify player position on court correctly
- Generate meaningful tennis performance metrics

### Development Goals
- Clean, well-documented codebase
- Demonstrates data engineering best practices
- Shows computer vision pipeline development
- Scalable architecture design

## Getting Started

### Prerequisites
- Python 3.13+
- Virtual environment activated
- Git repository initialized

### Development Commands
```bash
# Activate virtual environment
source venv/bin/activate

# Install dependencies
pip install -e .

# Run development server
cd backend
python -m uvicorn app.main:app --reload --port 8000

# Test API
curl http://localhost:8000/
curl http://localhost:8000/docs
``` 