# Analysis Backend Refactoring Plan

## Executive Summary

This document outlines a comprehensive plan to refactor the tennis coach app's analysis backend from a monolithic structure to a granular, service-oriented architecture. The current system couples all analysis types into a single "analysis" concept, preventing independent execution of specific analysis types and requiring completion before video playback.

## Current State Analysis

### Problems Identified

1. **Monolithic Analysis Model**: All analysis types (ball detection, pose estimation, contact detection) are bundled into one `Analysis` table and service
2. **Frontend Coupling**: Videos cannot be played without completing "analysis"
3. **All-or-Nothing Processing**: Cannot trigger individual analysis types independently
4. **Service Coupling**: `cv_service.py` (1961 lines) handles multiple responsibilities
5. **Duplicate Code**: Video quality assessment exists in both `cv_service.py` and `quality_service.py`

### Current Flow

```
analyze_video() → cv_service.analyze_video() → Everything:
├── Frame extraction
├── Ball detection (YOLO)
├── Pose estimation (MediaPipe)
├── Ball contact detection (if both available)
├── Annotated video creation
└── Single monolithic Analysis record
```

### Manual Ball Contact System ✅

The recently implemented ball contact system demonstrates the correct pattern:

- Separate `BallContact` model and service
- Manual vs automated detection sources
- Timestamp tolerance for duplicates
- Independent CRUD APIs

## Vision: Granular Analysis Services

### Target Analysis Types

1. **Video Quality Assessment** - Assess video clarity, lighting, resolution
2. **Ball Detection** - Detect tennis balls using YOLO (not tracking trajectories)
3. **Pose Detection** - Extract player pose keypoints using MediaPipe (not analysis)
4. **Video Annotation** - Create annotated videos with detection overlays
5. **Racket Detection** - Detect and track rackets (future)
6. **Posture Analysis** - Analyze player posture at contact points (main goal)

### New Service Architecture

```
backend/app/services/
├── video_quality/
│   ├── __init__.py
│   ├── assessment_service.py
│   └── models.py
├── ball_detection/
│   ├── __init__.py
│   ├── detection_service.py
│   └── models.py
├── pose_detection/
│   ├── __init__.py
│   ├── detection_service.py
│   └── models.py
├── video_annotation/
│   ├── __init__.py
│   ├── annotation_service.py
│   └── models.py
├── posture_analysis/
│   ├── __init__.py
│   ├── analysis_service.py
│   └── models.py
└── video/
    ├── __init__.py
    ├── video_service.py (existing)
    ├── frame_extractor.py
    └── metadata.py
```

### New Database Models

Replace monolithic `Analysis` with specific models:

```python
# Quality metrics stay in existing Video model - no separate model needed

class BallDetection(Base):
    __tablename__ = "ball_detections"
    id, video_id, total_detections, detection_rate,
    detection_data, confidence_scores, model_used, etc.

class PoseDetection(Base):
    __tablename__ = "pose_detections"
    id, video_id, total_poses, pose_confidence,
    keypoint_data, detection_quality_metrics, etc.

class VideoAnnotation(Base):
    __tablename__ = "video_annotations"
    id, video_id, annotated_video_path, annotation_type,
    ball_detection_id, pose_detection_id, processing_time, etc.

class PostureAnalysis(Base):
    __tablename__ = "posture_analyses"
    id, video_id, ball_contact_id,  # Link to specific contact
    posture_score, joint_angles, balance_metrics,
    recommendations, etc.

# Keep existing
class BallContact(Base): # ✅ Already implemented
```

### New API Endpoints

Individual analysis triggers:

```
POST /v0/video-quality/assess/{video_id}
POST /v0/ball-detection/analyze/{video_id}
POST /v0/pose-detection/analyze/{video_id}
POST /v0/video-annotation/create/{video_id}  # Creates annotated video from existing detections
POST /v0/posture/analyze/{video_id}/{contact_id}

GET /v0/video-quality/{video_id}
GET /v0/ball-detection/{video_id}
GET /v0/pose-detection/{video_id}
GET /v0/video-annotation/{video_id}
GET /v0/posture/{video_id}
```

## Key Architecture Decisions

### Why Separate Video Annotation?

Currently, annotated video creation is bundled with detection in `cv_service.py`. This creates several issues:

1. **Tight Coupling**: Can't create annotations without re-running detection
2. **Inefficiency**: Must reprocess video to create different annotation styles
3. **Inflexibility**: Can't combine detections from different analysis runs

**New Approach**: Annotation as a separate service that consumes detection results:

```
Detection Services → Store Results → Annotation Service → Annotated Video
     ↓                    ↓              ↓
Ball Detection       BallDetection    Read detection data
Pose Detection   →   PoseDetection  → Combine as needed  → Create video
                     VideoAnnotation   Different styles
```

**Benefits**:

- Create multiple annotation styles from same detection data
- Annotate videos with subset of available detections
- Re-annotate without re-detecting
- Support for different overlay styles (debug, presentation, analysis)

### Service Naming Rationale

- **Assessment vs Analysis**: `VideoQualityAssessment` (technical measurement) vs `PostureAnalysis` (higher-level interpretation)
- **Detection vs Tracking**: `BallDetection` (finding balls in frames) vs tracking (following ball movement over time)
- **Detection vs Estimation**: `PoseDetection` (finding keypoints) vs `PoseEstimation` (biomechanical analysis)

## Implementation Phases

### Phase 1: Extract Video Quality Assessment (Quick Win)

**Goal**: Create standalone video quality service and remove coupling

**Tasks**:

1. Create `backend/app/services/video_quality/`
2. Move quality logic from `cv_service.py` and `quality_service.py`
3. Update upload endpoint to use new quality service
4. Create `/v0/video-quality/assess/{video_id}` endpoint (for independent assessment)
5. Remove `quality_service.py`
6. No new model needed - quality metrics stay in existing `Video` model

**Files Created**:

- `backend/app/services/video_quality/__init__.py`
- `backend/app/services/video_quality/assessment_service.py`
- `backend/app/api/routes/video_quality.py` (for independent assessment)
- `backend/app/api/schemas/video_quality.py` (for response schemas only)

**Files Updated**:

- `backend/app/api/routes/video.py` (import new quality service)
- `backend/app/services/video_service.py` (import new quality service if needed)

**Success Criteria**:

- ✅ Upload still performs quality assessment automatically
- ✅ Quality assessment can also be run independently
- ✅ No duplicate quality assessment code
- ✅ Quality metrics remain in existing `Video` model
- ✅ Existing upload functionality preserved

### Phase 2: Extract Ball Detection Service

**Goal**: Independent ball detection (not trajectory tracking)

**Tasks**:

1. Create `backend/app/services/ball_detection/`
2. Create `BallDetection` model
3. Move ball detection from `cv_service.py`
4. Create `/v0/ball-detection/analyze/{video_id}` endpoint
5. Database migration

**Files Created**:

- `backend/app/services/ball_detection/__init__.py`
- `backend/app/services/ball_detection/detection_service.py`
- `backend/app/models/ball_detection.py`
- `backend/app/api/routes/ball_detection.py`
- `backend/app/api/schemas/ball_detection.py`

**Success Criteria**:

- Ball detection can run independently
- Ball detection data stored separately
- YOLO model management preserved

### Phase 3: Extract Pose Detection Service

**Goal**: Independent pose detection (not pose analysis)

**Tasks**:

1. Create `backend/app/services/pose_detection/`
2. Create `PoseDetection` model
3. Move pose detection from `cv_service.py`
4. Create `/v0/pose-detection/analyze/{video_id}` endpoint
5. Database migration

**Files Created**:

- `backend/app/services/pose_detection/__init__.py`
- `backend/app/services/pose_detection/detection_service.py`
- `backend/app/models/pose_detection.py`
- `backend/app/api/routes/pose_detection.py`
- `backend/app/api/schemas/pose_detection.py`

**Success Criteria**:

- Pose detection runs independently
- MediaPipe integration preserved
- Pose data stored separately

### Phase 3.5: Extract Video Annotation Service

**Goal**: Separate video annotation from detection services

**Tasks**:

1. Create `backend/app/services/video_annotation/`
2. Create `VideoAnnotation` model
3. Move `_create_annotated_video()` from `cv_service.py`
4. Create `/v0/video-annotation/create/{video_id}` endpoint
5. Link annotations to detection records
6. Database migration

**Files Created**:

- `backend/app/services/video_annotation/__init__.py`
- `backend/app/services/video_annotation/annotation_service.py`
- `backend/app/models/video_annotation.py`
- `backend/app/api/routes/video_annotation.py`
- `backend/app/api/schemas/video_annotation.py`

**Success Criteria**:

- Video annotation can run independently
- Annotations linked to specific detection records
- Multiple annotation types supported (ball-only, pose-only, combined)

### Phase 4: Build Posture Analysis Service (Main Goal)

**Goal**: Analyze player posture at ball contact points

**Tasks**:

1. Create `backend/app/services/posture_analysis/`
2. Create `PostureAnalysis` model linked to `BallContact`
3. Build posture analysis algorithms
4. Create `/v0/posture/analyze/{video_id}/{contact_id}` endpoint
5. Database migration

**Key Features**:

- Analyze pose data at specific contact timestamps
- Calculate joint angles and body positioning
- Generate posture scores and recommendations
- Support analysis of frames around contact (±0.5 seconds)

**Files Created**:

- `backend/app/services/posture_analysis/__init__.py`
- `backend/app/services/posture_analysis/posture_service.py`
- `backend/app/models/posture_analysis.py`
- `backend/app/api/routes/posture_analysis.py`
- `backend/app/api/schemas/posture_analysis.py`

**Success Criteria**:

- Posture analysis at specific contact points
- Integration with existing `BallContact` system
- Actionable posture feedback

### Phase 5: Decouple Frontend Video Playback

**Goal**: Allow video playback without analysis requirement

**Tasks**:

1. Update `VideoPlayer` component to always allow original video playback
2. Create separate analysis overlay components
3. Remove analysis dependency from video streaming
4. Update video list to show analysis status separately

**Frontend Changes**:

```typescript
// Current (bad): Requires analysis for playback
const getVideoUrl = () => {
  return analysis?.pose_detections ? annotatedVideoUrl : originalVideoUrl;
};

// New (good): Always allow original playback
const getVideoUrl = () => {
  return originalVideoUrl;
};

// Separate analysis overlays
{
  hasAnalysis && <AnalysisOverlay analysisData={analysis} />;
}
```

**Success Criteria**:

- Videos play immediately after upload
- Analysis results shown as overlays when available
- No blocking analysis requirements

### Phase 6: Legacy Analysis System Migration

**Goal**: Remove monolithic analysis system

**Tasks**:

1. Data migration from `Analysis` to specific analysis tables
2. Update existing API endpoints to use new services
3. Remove `analysis_service.py` monolithic functions
4. Remove `Analysis` model
5. Update frontend to use new granular APIs

**Migration Strategy**:

- Keep legacy endpoints during transition
- Gradual migration of frontend components
- Deprecation warnings for old endpoints

## Technical Specifications

### Service Patterns

Each analysis service follows this pattern:

```python
# Service structure
class VideoQualityService:
    def __init__(self):
        # Initialize models/dependencies

    def analyze_video(self, video_id: int) -> VideoQualityAnalysis:
        # Perform analysis
        # Store results
        # Return analysis record

    def get_analysis(self, video_id: int) -> Optional[VideoQualityAnalysis]:
        # Retrieve existing analysis
```

### API Patterns

Following REST and FastAPI best practices:

```python
@router.post("/analyze/{video_id}", response_model=AnalysisStartResponse)
async def start_analysis(video_id: int, db: Session = Depends(get_db)):
    # Validate video exists
    # Check for existing analysis
    # Start background analysis
    # Return task tracking info

@router.get("/{video_id}", response_model=AnalysisInfo)
async def get_analysis(video_id: int, db: Session = Depends(get_db)):
    # Retrieve analysis results
    # Return structured data
```

### Database Migration Strategy

1. **Additive Migrations**: Create new tables alongside existing `Analysis`
2. **Data Migration**: Copy relevant data from `Analysis` to new tables
3. **Gradual Cutover**: Update services to use new tables
4. **Cleanup**: Remove `Analysis` table once migration complete

### Error Handling

Consistent error responses across all services:

```python
class AnalysisError(HTTPException):
    def __init__(self, detail: str, analysis_type: str):
        super().__init__(
            status_code=500,
            detail=f"{analysis_type} analysis failed: {detail}"
        )
```

### Background Processing

Each service supports background processing:

```python
# Background task for each analysis type
@background_service.task
def analyze_video_quality_task(video_id: int):
    service = VideoQualityService()
    return service.analyze_video(video_id)
```

## Success Metrics

### Technical Metrics

- [ ] Reduction in service file sizes (target: <500 lines each)
- [ ] Independent analysis execution
- [ ] Eliminated code duplication
- [ ] Improved test coverage (target: >80% per service)

### User Experience Metrics

- [ ] Video playback works immediately after upload
- [ ] Analysis can be triggered selectively
- [ ] Contact point analysis works with manual contacts
- [ ] Analysis results load faster (granular data)

### Maintenance Metrics

- [ ] Easier to add new analysis types
- [ ] Clearer service boundaries
- [ ] Reduced coupling between components
- [ ] Better error isolation

## Risk Mitigation

### 1. Incremental Implementation

- Implement one phase at a time
- Keep existing system running during transition
- Comprehensive testing after each phase

### 2. Backward Compatibility

- Maintain existing API contracts during migration
- Use feature flags for gradual rollout
- Provide migration period for frontend updates

### 3. Data Integrity

- Thorough data migration testing
- Backup existing analysis data
- Rollback procedures for each phase

### 4. Performance Monitoring

- Monitor analysis performance during transition
- Compare processing times before/after
- Optimize bottlenecks identified during migration

## Timeline

- **Phase 1** (Video Quality Assessment): 3-4 days
- **Phase 2** (Ball Detection): 4-5 days
- **Phase 3** (Pose Detection): 4-5 days
- **Phase 3.5** (Video Annotation): 3-4 days
- **Phase 4** (Posture Analysis): 6-7 days
- **Phase 5** (Frontend Decoupling): 3-4 days
- **Phase 6** (Legacy Migration): 4-5 days

**Total Estimated Time**: 27-34 days

## Dependencies

### Internal Dependencies

- Existing `BallContact` system (✅ complete)
- Database migration capabilities
- Background processing system
- Frontend component architecture

### External Dependencies

- OpenCV for video processing
- YOLO models for detection
- MediaPipe for pose estimation
- SQLAlchemy for ORM

## Related Issues

- **GitHub Issue #73**: CV Service refactoring (provides additional technical context)
- **Ball Contact Migration**: Completed system demonstrating correct pattern
- **Frontend Analysis Coupling**: Current blocking behavior for video playback

## Future Enhancements

After core refactoring:

1. **Racket Tracking Service**: Dedicated racket detection
2. **Advanced Posture Analysis**: Multi-frame analysis around contacts
3. **Performance Optimization**: Parallel analysis processing
4. **Real-time Analysis**: WebSocket-based progress updates
5. **Analysis Workflows**: Predefined analysis sequences

---

_This document will be updated as implementation progresses and requirements evolve._
