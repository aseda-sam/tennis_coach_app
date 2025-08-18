# Tennis Coach App - Project Roadmap

> **Note**: This document serves as a development roadmap and project status tracker. For current setup instructions, see [backend/README.md](../backend/README.md) and [frontend/README.md](../frontend/README.md).

## Project Overview

A computer vision-based tennis analysis system that demonstrates data engineering and AI evaluation skills. The system processes tennis videos to extract meaningful insights about player performance, ball trajectory, and court positioning.

### Key Features (MVP) ✅ **COMPLETED**

- **Video Upload & Processing**: Upload tennis videos and extract basic metadata
- **Ball Tracking**: YOLO-based ball detection with trajectory analysis
- **Player Positioning**: MediaPipe pose estimation for court position analysis
- **Stroke Detection**: Basic forehand identification and analysis
- **Metrics Dashboard**: Visualization of key tennis performance metrics

### Tech Stack

- **Backend**: FastAPI (Python)
- **Frontend**: React (Simple, portfolio-focused)
- **Computer Vision**: YOLO + MediaPipe
- **Database**: SQLite (Development) → PostgreSQL/Supabase (Production)
- **Storage**: Local file system → Cloud Storage (S3/Cloudinary)

## Current Status

### ✅ Completed Features

- **Phase 1**: Basic Video Upload & File Management
- **Phase 2**: Database Integration
- **Phase 3**: Frontend Development
- **Phase 4**: Computer Vision Foundation (including MediaPipe)
- **Phase 5**: Analysis Pipeline
- **Phase 6**: Frontend Analysis Display
- **Phase 7**: React Analysis Components
- **Phase 8**: Video Playback & Codec Optimization
- **Phase 9**: Video Resolution Handling & Performance Optimization

### 🚀 Production Ready

- **CI/CD Pipeline**: GitHub Actions with automated testing and deployment
- **Backend Deployment**: Render with automatic GitHub integration
- **Frontend Deployment**: GitHub Pages with production builds
- **Docker Containerization**: GitHub Container Registry for backend images
- **Multi-environment Configuration**: Development vs production settings

## Implementation Phases

### Phase 1: Basic Video Upload & File Management ✅

- [x] Set up FastAPI project structure
- [x] Create video upload endpoint with validation
- [x] Add file storage system
- [x] Extract video metadata (duration, resolution, fps)
- [x] Create file management endpoints (list, delete, get details)
- [x] Integrate with SQLite database
- [x] Build React frontend with upload interface

### Phase 2: Computer Vision Foundation ✅

- [x] Add OpenCV for video frame extraction
- [x] Integrate YOLO for ball detection
- [x] Add MediaPipe for pose estimation
- [x] Extract tennis-relevant keypoints
- [x] Implement pose detection confidence thresholds
- [x] Create pose overlay visualization

### Phase 3: Analysis Pipeline ✅

- [x] Process video frames with CV models
- [x] Store analysis results in database
- [x] Calculate basic metrics (ball detections, pose detection rate)
- [x] Create annotated videos with pose and ball overlays
- [x] Implement comprehensive analysis pipeline
- [x] Add pose detection metrics to database schema

### Phase 4: Frontend Analysis Display ✅

- [x] Show analysis results in frontend
- [x] Create AnalysisResults component with collapsible sections
- [x] Build VideoPlayer component with controls and fullscreen
- [x] Implement AnalysisDashboard with video player and results
- [x] Add smart video selection (annotated vs original)
- [x] Create enhanced video list with analysis status

### Phase 5: Video Playback & Codec Optimization ✅

- [x] Fix annotated video playback issues
- [x] Implement fallback codec system for OpenCV
- [x] Add FFmpeg H.264 conversion for browser compatibility
- [x] Ensure cross-browser video compatibility
- [x] Add proper error handling and fallback mechanisms

### Phase 6: Production Deployment ✅

- [x] CI/CD pipeline with GitHub Actions
- [x] Render backend deployment with automatic GitHub integration
- [x] GitHub Pages frontend deployment with production builds
- [x] GitHub Container Registry for Docker image publishing
- [x] Multi-environment configuration (development vs production)
- [x] Docker multi-stage builds with development and production targets
- [x] Health checks and proper container lifecycle management

### Phase 7: Enhancement & Polish ✅

- [x] **Video Resolution Handling**: Add resolution and frame rate limits to prevent processing crashes ✅ **COMPLETED**
  - [x] **Quick Fix**: Add 1080p resolution validation to prevent 4K uploads
  - [x] **Video Downscaling**: Automatically downscale 4K videos to 1080p before processing
  - [x] **Dynamic Frame Skip**: Adjust frame skip ratio based on video resolution
  - [x] **Frame Rate Limits**: Add 30fps maximum to prevent high-fps processing issues
  - [x] **Environment Detection**: Dynamic configuration based on local/Docker/production
  - [x] **Performance Testing**: Comprehensive testing scripts for different environments
- [x] **Background Tasks Backend**: Non-blocking video analysis with progress tracking ✅ **COMPLETED**
  - [x] **FastAPI Background Tasks**: ThreadPoolExecutor for concurrent processing
  - [x] **Progress Tracking**: Real-time status updates and progress monitoring
  - [x] **Task Management**: Start, cancel, and monitor background tasks
  - [x] **Thread Safety**: Proper synchronization and race condition prevention
  - [x] **Error Handling**: Robust error handling and status reporting
  - [x] **API Endpoints**: Complete REST API for task management
- [x] **Frontend Background Task Integration**: Real-time UI updates and progress tracking ✅ **COMPLETED**
  - [x] **Task Status Polling**: Real-time progress monitoring in UI
  - [x] **Progress Indicators**: Visual feedback for ongoing analyses
  - [x] **Cancel Functionality**: Cancel ongoing analysis with proper cleanup
  - [x] **Error Recovery**: Graceful error handling and retry mechanisms
- [x] **Granular Progress Tracking**: Stage-specific feedback and detailed progress ✅ **COMPLETED**
  - [x] **Backend Stage Configuration**: Analysis stage definitions and progress ranges
  - [x] **Enhanced Task Status Schema**: Stage information and detailed progress
  - [x] **CV Service Progress Callbacks**: Stage-specific progress tracking
  - [x] **Frontend Stage Icons**: Custom SVG icons for each analysis stage
  - [x] **Enhanced Progress Components**: Stage-specific progress indicators
  - [x] **Stage Information Display**: Current stage, sub-progress, and time estimates

### Phase 8: Production Infrastructure Migration ✅ **COMPLETED**

- [x] **Supabase Database Migration**: Replace SQLite with PostgreSQL for production ✅ **COMPLETED**
  - [x] **Environment-based Configuration**: Support both SQLite (dev) and Supabase (prod)
  - [x] **Database Connection Setup**: Direct PostgreSQL connection to Supabase
  - [x] **Migration Strategy**: Fresh migration approach for clean schema
  - [x] **Environment Variables**: Production vs development database URLs
  - [x] **Testing**: Verify database connectivity and migration success
  - [x] **Local Development Setup**: Environment variable management for local Supabase testing
  - [x] **Security Considerations**: RLS warnings addressed (optional for single-user app)
- [ ] **Cloud Storage Integration**: Replace local file storage with cloud solution (Future)
  - [ ] **Storage Provider Selection**: S3 vs Cloudinary vs Backblaze B2 evaluation
  - [ ] **Environment-based Storage**: Local storage (dev) vs cloud storage (prod)
  - [ ] **File Upload/Download**: Cloud storage integration for video files
  - [ ] **Storage Configuration**: Environment variables for cloud credentials
  - [ ] **Fallback Strategy**: Local storage fallback for development
- [ ] **Multi-environment Setup**: Complete development vs production configuration (Future)
  - [ ] **Environment Detection**: Automatic environment detection and configuration
  - [ ] **Configuration Management**: Centralized settings for all environments
  - [ ] **Deployment Updates**: Update deployment scripts for new infrastructure
  - [ ] **Testing Strategy**: Comprehensive testing across environments

### Phase 9: Ball Detection Improvements & Contact Posture Analysis 🚧 **IN PROGRESS**

#### Phase 9A: Ball Detection Foundation Improvements (Current Priority)

**Goal**: Improve ball detection reliability and accuracy as foundation for contact posture analysis.

- [x] **Step 1: Fix Configuration Usage** (Low-hanging fruit) ✅ **COMPLETED**

  - [x] Use `BALL_CONFIDENCE_THRESHOLD` from config instead of hard-coded 0.5
  - [x] Implement proper `FRAME_SKIP_RATIO` usage in frame extraction
  - [x] Disable frame skipping by default (set ratio to 1) for smoother video playback
  - [x] Test with existing videos to verify improvements
  - [x] **User Testing**: Verify ball detection quality improvement

- [ ] **Step 2: Adaptive Confidence Thresholds** (Medium complexity)

  - [ ] Implement video quality assessment (blur, lighting, resolution)
  - [ ] Adjust confidence thresholds based on video quality
  - [ ] Add quality metrics to analysis results
  - [ ] **User Testing**: Test with poor vs good quality videos

- [ ] **Step 3: YOLO Model Optimization** (Medium complexity)

  - [ ] Test `yolov8s.pt` (small) vs `yolov8n.pt` (nano) for accuracy/speed trade-off
  - [ ] Implement model selection based on video quality
  - [ ] Add model performance metrics to analysis
  - [ ] **User Testing**: Compare detection accuracy between models

- [ ] **Step 4: Temporal Smoothing** (Advanced)
  - [ ] Implement ball trajectory prediction between frames
  - [ ] Filter false positives using motion patterns
  - [ ] Add trajectory confidence scoring
  - [ ] **User Testing**: Verify smoother ball tracking

#### Phase 9B: Contact Posture Analysis MVP

**Goal**: Implement minimal viable contact posture analysis using improved ball detection.

- [ ] **Step 1: Contact Frame Detection** (Foundation)

  - [ ] Implement ball deceleration detection algorithm
  - [ ] Add wrist proximity filtering for contact candidates
  - [ ] Create contact event detection service
  - [ ] **User Testing**: Verify contact frame detection accuracy

- [ ] **Step 2: Basic Posture Metrics** (Core functionality)

  - [ ] Calculate contact height (normalized to player torso)
  - [ ] Calculate lateral offset (ball position relative to body midline)
  - [ ] Calculate elbow angle at contact
  - [ ] **User Testing**: Verify metric calculations are reasonable

- [ ] **Step 3: Contact Analysis API** (Backend integration)

  - [ ] Create `ContactPostureAnalysis` Pydantic schemas
  - [ ] Implement compute-on-read endpoint (`GET /v0/analysis/{id}/contact`)
  - [ ] Add JSON caching with invalidation (algo_version + inputs_hash)
  - [ ] **User Testing**: Test API endpoint with existing analyses

- [ ] **Step 4: Frontend Contact Display** (UI integration)
  - [ ] Add contact events list to `AnalysisResults` component
  - [ ] Implement timeline markers on video player
  - [ ] Display contact metrics with tooltips
  - [ ] **User Testing**: Verify UI displays contact data correctly

#### Phase 9C: Enhanced Contact Analysis

**Goal**: Expand contact posture analysis with more sophisticated metrics.

- [ ] **Step 1: Advanced Posture Metrics**

  - [ ] Shoulder line angle and rotation
  - [ ] Hip-shoulder separation (stance width)
  - [ ] Weight distribution indicators
  - [ ] **User Testing**: Verify advanced metrics provide useful insights

- [ ] **Step 2: Contact Classification**

  - [ ] Classify contact types (forehand, backhand, serve)
  - [ ] Add stroke-specific posture analysis
  - [ ] Implement contact confidence scoring
  - [ ] **User Testing**: Verify stroke classification accuracy

- [ ] **Step 3: Database Integration**
  - [ ] Create `ContactPostureAnalysis` database model
  - [ ] Migrate from JSON cache to persistent storage
  - [ ] Add contact analysis to background task pipeline
  - [ ] **User Testing**: Verify database storage and retrieval

#### Phase 9D: Coaching Insights

**Goal**: Transform contact posture data into actionable coaching feedback.

- [ ] **Step 1: Posture Assessment**

  - [ ] Define "good" vs "needs improvement" thresholds for each metric
  - [ ] Implement posture scoring system
  - [ ] Add posture improvement suggestions
  - [ ] **User Testing**: Verify assessment provides useful feedback

- [ ] **Step 2: Trend Analysis**
  - [ ] Compare contact posture across multiple videos
  - [ ] Track improvement over time
  - [ ] Generate progress reports
  - [ ] **User Testing**: Verify trend analysis works across sessions

### Phase 10: Advanced Features (Future)

- [ ] **Redis Queue Migration**: Upgrade to RQ for production-grade task management
- [ ] **Advanced Stroke Detection**: Forehand/backhand classification
- [ ] **Rally Analysis**: Duration and pattern recognition
- [ ] **Court Coverage Heatmaps**: Player movement visualization
- [ ] **Performance Metrics**: Advanced tennis-specific analytics
- [ ] **User Experience Improvements**: Better loading states, error handling

### Phase 10: Performance & Testing Tools ✅ **COMPLETED**

- [x] **Performance Testing Scripts**: Comprehensive testing for different environments
  - [x] `performance_test.py` - Local environment testing with full video processing
  - [x] `docker_performance_test.py` - Docker-optimized testing with memory limits
  - [x] `run_performance_test.py` - Simple runner script for easy execution
- [x] **Environment Detection**: Automatic detection of local/Docker/production
- [x] **Dynamic Configuration**: Environment-specific processing limits
- [x] **Validation Framework**: Comprehensive video metadata validation

### Phase 11: Scale & Performance (Future)

- [ ] **Microservices Architecture**: Separate video processing service
- [ ] **Load Balancing**: Multiple application instances
- [ ] **CDN Integration**: Global video delivery optimization
- [ ] **Caching Strategy**: Redis for frequently accessed data
- [ ] **Performance Monitoring**: Real-time system metrics

## Success Metrics

### Technical Goals ✅ **ACHIEVED**

- [x] Process tennis videos successfully
- [x] Detect and track tennis ball with reasonable accuracy
- [x] Identify player position on court correctly
- [x] Generate meaningful tennis performance metrics

### Development Goals ✅ **ACHIEVED**

- [x] Clean, well-documented codebase
- [x] Demonstrates data engineering best practices
- [x] Shows computer vision pipeline development
- [x] Scalable architecture design

### Future Goals

- [ ] **User Adoption**: Active users and engagement metrics
- [ ] **Performance**: Sub-second video processing times
- [ ] **Accuracy**: 95%+ detection accuracy for key metrics
- [ ] **Scalability**: Support for 1000+ concurrent users

## Technology Decisions

### Current Stack

- **FastAPI**: Chosen for performance, automatic docs, and Python ecosystem
- **React + TypeScript**: Modern frontend with type safety
- **SQLite**: Simple, reliable for development; Supabase PostgreSQL planned for production
- **YOLO + MediaPipe**: Best balance of accuracy and performance
- **Docker**: Consistent deployment across environments

### Future Considerations

- **Supabase PostgreSQL**: For production database needs
- **Cloud Storage**: S3/Cloudinary for scalable video storage
- **Redis**: For caching and background task queues
- **Kubernetes**: For container orchestration at scale

## Getting Started

### For New Developers

1. Read the [backend README](../backend/README.md) for setup instructions
2. Read the [frontend README](../frontend/README.md) for component development
3. Check the [deployment guide](deployment_guide.md) for production setup
4. Review the [pose estimation comparison](pose_estimation_comparison.md) for CV decisions

### Development Commands

```bash
# Backend development
cd backend
python -m uvicorn app.main:app --reload --port 8000

# Frontend development
cd frontend
npm start

# Run tests
cd backend && pytest
cd frontend && npm test

# Code quality
cd backend && ruff check . && ruff format .
cd frontend && npm run lint

# Performance testing
cd backend && python scripts/run_performance_test.py
cd backend && python scripts/docker_performance_test.py
```

## Local Development with Supabase

### Running Backend with Supabase Locally

To use Supabase instead of SQLite for local development:

```bash
# Option 1: Use .env.production (Recommended)
cd backend
set -a && source .env.production && set +a
python -m uvicorn app.main:app --reload

# Option 2: Set environment variables directly
cd backend
ENVIRONMENT=production SUPABASE_DB_URL='your_connection_string' python -m uvicorn app.main:app --reload

# Option 3: Create startup script
# Create backend/start-supabase.sh:
#!/bin/bash
set -a
source .env.production
set +a
python -m uvicorn app.main:app --reload
```

### Environment Variable Management

- **Session-specific**: Environment variables set with `set -a` only persist for current terminal session
- **Restart required**: Need to re-run environment setup for each new terminal session
- **Security**: `.env.production` contains database credentials and is gitignored

### Supabase Security Warnings (RLS)

When using Supabase, you may see Row Level Security (RLS) warnings:

```
Table 'public.videos' is public, but RLS has not been enabled.
Table 'public.analyses' is public, but RLS has not been enabled.
```

**For single-user applications:**

- These warnings can be safely ignored
- RLS is not critical until you implement user authentication
- Your app will function normally without RLS enabled

**To enable RLS (optional):**

```sql
-- Enable RLS on tables
ALTER TABLE videos ENABLE ROW LEVEL SECURITY;
ALTER TABLE analyses ENABLE ROW LEVEL SECURITY;

-- Create permissive policies (for single-user app)
CREATE POLICY "Allow all operations on videos" ON videos FOR ALL USING (true);
CREATE POLICY "Allow all operations on analyses" ON analyses FOR ALL USING (true);
```

## Contributing

1. **Pick a Phase**: Choose from the roadmap based on priority
2. **Follow Standards**: Use established patterns and code quality tools
3. **Test Thoroughly**: Write tests for new features
4. **Document Changes**: Update relevant documentation
5. **Submit PR**: Follow conventional commit messages

## License

MIT License
