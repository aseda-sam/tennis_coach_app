# Backend Architecture Improvements Plan

## Executive Summary

This document outlines critical and important improvements needed for the FastAPI backend architecture. While the recent refactoring successfully removed legacy code and created modular services, several architectural inconsistencies and data flow issues remain that need to be addressed for production readiness.

**Status**: 🔴 **CRITICAL ISSUES IDENTIFIED** - Immediate attention required

## 🚨 Critical Issues (Fix First)

### 1. Schema/Model Data Loss Issues

**Problem**: Several database model fields are not exposed through API schemas, causing data loss and inconsistent API responses.

**Impact**:

- Data stored in database but not accessible via API
- Inconsistent field availability between create/read operations
- Potential data corruption in client applications

**Affected Models**:

#### BallContact Model - Missing Schema Fields

```python
# Database model has these fields NOT in API schemas:
- ball_area: Column(Float, nullable=True)
- ball_size_factor: Column(Float, nullable=True)
- racket_data: Column(String, nullable=True)
- ball_bbox: Column(String, nullable=True)
- ball_racket_distance: Column(Float, nullable=True)
- player: Column(Integer, nullable=True)
- confidence: Column(Float, nullable=True)
- ball_position: Column(String, nullable=True)
- player_position: Column(String, nullable=True)
- description: Column(String, nullable=True)
```

**Required Actions**:

1. Update `BallContactInfo`, `BallContactCreate`, `BallContactUpdate` schemas
2. Add proper field validation and documentation
3. Ensure backward compatibility for existing API consumers

### 2. Background Task Response Schema Mismatches

**Problem**: Background task API responses don't match the declared response schemas, causing runtime errors and inconsistent API contracts.

**Impact**:

- API documentation doesn't match actual responses
- Frontend applications may break due to unexpected response structure
- Type safety violations

**Examples**:

```python
# ball_detection.py returns fields not in schema:
return BallDetectionResponse(
    ball_detection_id=None,  # Field doesn't exist in schema
    video_filename=video.filename,  # Field doesn't exist in schema
    task_id=task_id,  # Field doesn't exist in schema
    estimated_duration=180,  # Field doesn't exist in schema
)
```

**Required Actions**:

1. Create unified task response base schemas
2. Update all background task endpoints to use consistent response patterns
3. Add proper task tracking fields to all response schemas

### 3. Memory-Based Task Storage (Non-Persistent)

**Problem**: Background tasks use in-memory storage that doesn't persist across server restarts.

**Impact**:

- Task progress lost on server restart
- No task history or audit trail
- Cannot scale to multiple server instances
- No way to recover from server crashes

**Current Implementation**:

```python
# Global task storage - will not scale or persist
_active_tasks: Dict[int, Dict[str, Any]] = {}
```

**Recommended Solution**: **Redis Integration**

Since you plan to move to Redis for task storage, the current in-memory implementation is acceptable for now. Redis will provide:

- Task persistence across restarts
- Distributed task tracking
- Built-in expiration and cleanup
- Better performance than database storage

**Required Actions** (When implementing Redis):

1. Replace in-memory storage with Redis backend
2. Add Redis connection management and error handling
3. Implement task expiration and cleanup policies
4. Add Redis health checks and fallback mechanisms

**Note**: This is not a breaking issue for current functionality, so can be deferred until Redis implementation.

## ⚠️ Important Issues (Next Phase)

### 4. Inconsistent Service Architecture Patterns

**Problem**: Services use mixed architectural patterns - some are class-based, others are functional.

**Impact**:

- Inconsistent dependency injection
- Difficult to test and mock services
- Tight coupling between services
- No clear service lifecycle management

**Examples**:

```python
# video_service.py - Functional approach
def create_video_record(db: Session, ...)
def get_video_by_id(db: Session, ...)

# ball_detection/detection_service.py - Class-based approach
class BallDetectionService:
    def analyze_video_file(...)
    def save_detection_results(...)
```

**Required Actions**:

1. Standardize all services to class-based architecture
2. Implement proper dependency injection container
3. Create service interfaces for better testability
4. Add service lifecycle management

### 5. Mixed Sync/Async Patterns

**Problem**: API routes inconsistently use async/sync patterns without clear rationale.

**Impact**:

- Performance inconsistencies
- Confusing for developers
- Potential blocking operations in async routes
- Inconsistent error handling patterns

**Examples**:

```python
# Mixed patterns in routes:
@router.post("/upload", response_model=VideoUploadResponse)
async def upload_video(...)  # Async route

@router.post("/", response_model=BallContactInfo)
def create_ball_contact_endpoint(...)  # Sync route
```

**Required Actions**:

1. Standardize all routes to async patterns
2. Ensure all service calls are properly awaited
3. Add async database operations where beneficial
4. Document async/sync usage guidelines

### 6. Database Transaction Boundary Issues

**Problem**: Multi-step operations span multiple service calls without proper transaction management.

**Impact**:

- Data inconsistency if operations fail partway through
- No rollback capability for failed operations
- Potential orphaned data in database

**Example**:

```python
# In background_service._run_comprehensive_analysis():
ball_detection = ball_service.save_detection_results(...)  # Separate transaction
pose_detection = pose_service.save_detection_results(...)  # Separate transaction
# No rollback if second operation fails
```

**Required Actions**:

1. Implement transaction decorators for multi-step operations
2. Add proper rollback mechanisms
3. Create transaction boundary documentation
4. Add transaction testing scenarios

### 7. Service Discovery and Dependency Management

**Problem**: Services directly instantiate other services instead of using dependency injection.

**Impact**:

- Tight coupling between services
- Difficult to test individual services
- No service lifecycle control
- Hard to implement service mocking

**Example**:

```python
# In background_service.py:
ball_service = BallDetectionService()  # Direct instantiation
pose_service = PoseDetectionService()  # No DI
```

**Required Actions**:

1. Implement dependency injection container
2. Create service interfaces and abstractions
3. Add service registration and discovery
4. Implement proper service lifecycle management

## Implementation Plan

### Phase 1: Critical Fixes (Immediate - 1-2 weeks)

1. **Fix Schema/Model Consistency**

   - Update all API schemas to include missing database fields
   - Add proper field validation and documentation
   - Test backward compatibility

2. **Fix Background Task Response Schemas**

   - Create unified task response base schemas
   - Update all background task endpoints
   - Ensure API documentation accuracy

3. **Redis Task Storage** (When ready to implement)

   - Replace in-memory storage with Redis backend
   - Add Redis connection management
   - Implement task expiration and cleanup

### Phase 2: Architecture Improvements (2-4 weeks)

1. **Standardize Service Architecture**

   - Convert functional services to class-based
   - Implement dependency injection container
   - Add service interfaces

2. **Implement Transaction Management**

   - Add transaction decorators
   - Create rollback mechanisms
   - Add transaction testing

3. **Standardize Async Patterns**
   - Convert all routes to async
   - Add proper async database operations
   - Update error handling patterns

## Success Criteria

### Critical Issues Resolution:

- ✅ All database fields accessible via API schemas
- ✅ API responses match declared schemas
- ✅ No data loss in multi-step operations
- ✅ Redis-based task storage implemented (when ready)

### Architecture Improvements:

- ✅ Consistent service architecture patterns
- ✅ Proper dependency injection throughout
- ✅ Standardized async/sync usage
- ✅ Comprehensive transaction management

## Risk Assessment

**High Risk**: Schema/Model inconsistencies could cause data loss in production
**Medium Risk**: Background task storage issues could cause user experience problems
**Low Risk**: Architecture inconsistencies affect maintainability but not functionality

## Dependencies

- Database migration capabilities for task storage
- Service container implementation
- Transaction management framework
- Async/await standardization across codebase

---

**Note**: This document focuses only on critical and important issues. Nice-to-have improvements and positive aspects of the current architecture are not included as requested.
