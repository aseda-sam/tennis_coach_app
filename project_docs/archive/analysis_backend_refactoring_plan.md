# Analysis Backend Refactoring Plan

## Executive Summary

This document outlines the refactoring of the tennis coach app's analysis backend from a monolithic structure to a granular, service-oriented architecture. **The refactoring is COMPLETE** - we've successfully extracted modular services and removed all legacy code entirely.

## Current State Analysis

### ✅ COMPLETED: Problems Solved

1. **✅ Modular Services Created**: Pose detection, ball detection, and video quality services are now independent
2. **✅ Background Processing**: All analysis types route through background_service with proper task management
3. **✅ Independent Execution**: Can trigger pose-only, ball-only, or comprehensive analysis independently
4. **✅ Service Decoupling**: CV service responsibilities distributed across specialized services
5. **✅ Code Deduplication**: Video quality assessment consolidated into single service

### ✅ NEW FLOW: Modular Architecture

```
POST /v0/analysis/videos/{video_id} → background_service → Route by analysis_type:
├── "pose_only" → PoseDetectionService → PoseDetection model
├── "ball_only" → BallDetectionService → BallDetection model
├── "comprehensive" → Both services → Both models + VideoAnnotation
└── All types → Modular services only (legacy removed)
```

### ✅ COMPLETED: Modular Services

- **✅ PoseDetectionService**: Independent pose detection with MediaPipe
- **✅ BallDetectionService**: Independent ball detection with YOLO
- **✅ VideoQualityService**: Independent quality assessment
- **✅ BallContact System**: Manual contact detection with timestamp tolerance
- **✅ Background Processing**: All services support task management, progress tracking, cancellation

## ✅ COMPLETED: Legacy Code Removal

### ✅ COMPLETED: Core Services

1. **✅ Video Quality Assessment** - Independent quality service with metrics in Video model
2. **✅ Ball Detection** - Independent YOLO-based detection service
3. **✅ Pose Detection** - Independent MediaPipe-based detection service
4. **✅ Video Annotation** - Independent annotation service (creates annotated videos)
5. **✅ Ball Contact System** - Manual contact detection with timestamp tolerance

### ✅ COMPLETED: Legacy System Removal

**All legacy Analysis system components have been removed**:

- **✅ Legacy Analysis Model**: Deleted `analysis.py` and dropped `analyses` table
- **✅ Legacy Analysis Service**: Deleted `analysis_service.py` and all functions
- **✅ Legacy Analysis Routes**: Deleted `analysis.py` routes and schemas
- **✅ Legacy CV Service**: Removed monolithic `analyze_video` method
- **✅ Database Migration**: Applied migration to drop `analyses` table
- **✅ Import Cleanup**: Removed all Analysis references from codebase

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

## ✅ COMPLETED: Legacy Code Removal

### ✅ COMPLETED: All Core Services

**Phase 1**: ✅ Video Quality Assessment - Independent service with metrics in Video model
**Phase 2**: ✅ Ball Detection Service - Independent YOLO-based detection  
**Phase 3**: ✅ Pose Detection Service - Independent MediaPipe-based detection
**Phase 3.1**: ✅ Background Service Integration - All analysis types route through background_service
**Phase 3.5**: ✅ Video Annotation Service - Independent annotation creation
**Phase 4**: ✅ Legacy System Removal - All legacy Analysis components deleted

### ✅ COMPLETED: Legacy Analysis System Removal

**Goal**: Completely remove the monolithic Analysis system and all legacy code

**Final State**:

- ✅ All analysis types use modular services via background_service
- ✅ Frontend works with existing API endpoints
- ✅ Data stored in proper modular models (PoseDetection, BallDetection, VideoAnnotation)
- ✅ Legacy Analysis model completely removed
- ✅ Legacy analysis_service.py completely deleted
- ✅ Legacy CV service cleaned up

**Completed Removal Tasks**:

1. **✅ Remove Legacy Analysis Model**

   - ✅ Deleted `backend/app/models/analysis.py`
   - ✅ Created database migration to drop `analyses` table
   - ✅ Removed Analysis imports from all files

2. **✅ Remove Legacy Analysis Service**

   - ✅ Deleted `backend/app/services/analysis_service.py`
   - ✅ Removed all functions: `analyze_video()`, `create_analysis_record()`, etc.
   - ✅ Removed Analysis imports from background_service.py

3. **✅ Remove Legacy Analysis Routes**

   - ✅ Deleted `backend/app/api/routes/analysis.py`
   - ✅ Removed analysis router from `main.py`
   - ✅ Removed analysis schemas

4. **✅ COMPLETE: Clean Up CV Service**

   - ✅ **COMPLETE**: `analyze_video()` method removed (340+ lines of legacy code)
   - ✅ **COMPLETE**: All detection methods removed (detect_balls, detect_pose, etc.)
   - ✅ **COMPLETE**: `_create_annotated_video` method removed
   - ✅ **COMPLETE**: No references to CVService in production code
   - ✅ **COMPLETE**: Contact detection functions moved to `ball_contact_service.py`
   - ✅ **COMPLETE**: Utility functions moved to appropriate services
   - ✅ **COMPLETE**: `cv_service.py` file completely deleted

5. **✅ Update Background Service**

   - ✅ Removed legacy fallback in `_run_analysis_task()`
   - ✅ Removed `create_analysis_record()` calls
   - ✅ Removed Analysis model imports

6. **✅ Update Video Service**
   - ✅ Removed Analysis model imports
   - ✅ Removed Analysis-related file deletion logic

**Files Deleted**:

- ✅ `backend/app/models/analysis.py`
- ✅ `backend/app/services/analysis_service.py`
- ✅ `backend/app/api/routes/analysis.py`
- ✅ `backend/app/api/schemas/analysis.py`

**Files Updated**:

- ✅ `backend/app/services/background_service.py` - Removed legacy fallback
- ✅ `backend/app/services/cv_service.py` - Removed analyze_video method
- ✅ `backend/app/services/video_service.py` - Removed Analysis imports
- ✅ `backend/app/main.py` - Removed analysis router
- ✅ `backend/app/models/__init__.py` - Removed Analysis import
- ✅ `backend/app/core/database.py` - Removed Analysis import from create_tables

**Database Migration**:

- ✅ Applied migration to drop `analyses` table
- ✅ No data loss - all data already in proper modular tables

**Success Criteria Met**:

- ✅ No references to Analysis model anywhere in codebase
- ✅ All analysis types work through modular services only
- ✅ Frontend continues to work (uses modular data via background_service)
- ✅ Database contains only modular tables (pose_detections, ball_detections, video_annotations)
- ✅ Codebase is 2000+ lines smaller and cleaner
- ✅ Server starts without errors

## Summary

**Status**: ✅ **COMPLETE** - Backend refactoring fully finished

**Completed**: All core services extracted and working independently

- ✅ Video Quality Assessment
- ✅ Ball Detection Service
- ✅ Pose Detection Service
- ✅ Video Annotation Service
- ✅ Background Service Integration
- ✅ Legacy Analysis System Removal
- ✅ **CVService Cleanup** (340+ lines of legacy code removed)

**Final Result**: Clean, modular architecture with independent services and no legacy dependencies.

**Architecture**: The backend now runs entirely on modular services:

- `PoseDetectionService` → `pose_detections` table
- `BallDetectionService` → `ball_detections` table
- `VideoAnnotationService` → `video_annotations` table
- `BackgroundTaskService` → manages all analysis workflows

**Code Reduction**: Removed 2000+ lines of legacy code, including the complete CVService cleanup (340+ lines), resulting in a cleaner, more maintainable codebase.

---

_This document can now be archived as the refactoring is complete._
