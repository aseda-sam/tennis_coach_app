# Background Tasks System

This document provides a comprehensive guide to the background task system in the Tennis Coach App, explaining why we need it, what's implemented, and how it works.

## Table of Contents

- [Why Background Tasks?](#why-background-tasks)
- [What's Implemented](#whats-implemented)
- [How It Works](#how-it-works)
- [Task Lifecycle](#task-lifecycle)
- [Progress Tracking](#progress-tracking)
- [Current Limitations](#current-limitations)
- [Redis Migration Plan](#redis-migration-plan)
- [API Integration](#api-integration)
- [Troubleshooting](#troubleshooting)

## Why Background Tasks?

### The Problem

Tennis video analysis is **computationally expensive** and can take several minutes to complete:

- **Ball Detection**: YOLO processes every frame (30fps video = 1800 frames for 1 minute)
- **Pose Estimation**: MediaPipe analyzes player movements frame by frame
- **Video Annotation**: Creates new video files with overlays
- **Processing Time**: 2-5 minutes for a typical 30-second tennis video

### The Solution

**Background tasks** allow the API to:

1. **Return immediately** with a task ID instead of blocking for minutes
2. **Process videos asynchronously** without timing out HTTP requests
3. **Provide progress updates** so users know what's happening
4. **Handle multiple videos** concurrently with thread pools
5. **Allow task cancellation** if users change their mind

### Without Background Tasks

```python
# BAD: This would timeout and block the API
@app.post("/analyze")
def analyze_video(video_id: int):
    # This takes 3-5 minutes!
    result = analyze_video_with_yolo(video_id)
    return result  # Request would timeout
```

### With Background Tasks

```python
# GOOD: Returns immediately, processes in background
@app.post("/analyze")
def analyze_video(video_id: int):
    task_id = background_service.start_analysis_task(video_id, "ball_only")
    return {"task_id": task_id, "status": "queued"}

@app.get("/task/{task_id}/status")
def get_task_status(task_id: int):
    return background_service.get_task_status(task_id)
```

## What's Implemented

### Core Components

#### 1. BackgroundTaskService (`backend/app/services/background_service.py`)

**Purpose**: Main orchestrator for background video analysis tasks.

**Key Features**:

- **Thread Pool Management**: Uses `ThreadPoolExecutor` with configurable workers
- **Task Storage**: In-memory dictionary with thread-safe locking
- **Progress Tracking**: Real-time progress updates with stage information
- **Error Handling**: Comprehensive error capture and reporting
- **Task Cancellation**: Ability to cancel running tasks
- **Cleanup**: Automatic cleanup of old completed tasks

#### 2. Progress Utils (`backend/app/utils/progress_utils.py`)

**Purpose**: Utility functions for updating task progress from within analysis services.

**Key Features**:

- **Stage-based Progress**: Track both overall progress and current stage
- **Thread-safe Updates**: Safe progress updates from multiple threads
- **Detailed Messages**: Human-readable progress messages

#### 3. Analysis Services Integration

**Purpose**: Modular services that perform the actual analysis work.

**Integrated Services**:

- **PoseDetectionService**: MediaPipe pose estimation
- **BallDetectionService**: YOLO ball detection
- **VideoAnnotationService**: Creates annotated videos with overlays

### Supported Analysis Types

#### 1. `pose_only`

- **Purpose**: Extract player pose keypoints using MediaPipe
- **Output**: PoseDetection database records
- **Dependencies**: None (independent)
- **Processing Time**: 1-3 minutes

#### 2. `ball_only`

- **Purpose**: Detect tennis balls using YOLO
- **Output**: BallDetection database records
- **Dependencies**: None (independent)
- **Processing Time**: 2-4 minutes

#### 3. `video_annotation_only`

- **Purpose**: Create annotated videos with detection overlays
- **Output**: Annotated video files
- **Dependencies**: Requires existing ball OR pose detections
- **Processing Time**: 1-2 minutes

### Task Storage (Current Implementation)

```python
# In-memory storage with thread-safe locking
_active_tasks: Dict[int, Dict[str, Any]] = {
    1: {
        "task_id": 1,
        "video_id": 123,
        "analysis_type": "ball_only",
        "confidence_threshold": 0.7,
        "status": "processing",  # queued, processing, completed, failed, cancelled
        "progress": 45,  # 0-100
        "current_stage": "ball_detection",
        "stage_progress": 80,
        "stage_message": "Processing frame 1200 of 1500",
        "error": None,
        "result": None,
        "started_at": datetime.now(),
        "completed_at": None,
        "future": ThreadPoolExecutor.Future  # For cancellation
    }
}
```

## How It Works

### 1. Task Creation

```python
# API endpoint receives analysis request
task_id = background_service.start_analysis_task(
    video_id=123,
    analysis_type="ball_only",
    confidence_threshold=0.7
)

# Returns immediately with task ID
return {"task_id": task_id, "status": "queued"}
```

### 2. Task Execution

```python
# Background thread picks up the task
def _run_analysis_task(self, task_id, video_id, analysis_type, confidence_threshold):
    try:
        # Update status to processing
        _active_tasks[task_id]["status"] = "processing"

        # Route to appropriate analysis service
        if analysis_type == "ball_only":
            result = self._run_ball_only_analysis(...)
        elif analysis_type == "pose_only":
            result = self._run_pose_only_analysis(...)
        # ... etc

        # Mark as completed
        _active_tasks[task_id]["status"] = "completed"
        _active_tasks[task_id]["result"] = result

    except Exception as e:
        # Mark as failed
        _active_tasks[task_id]["status"] = "failed"
        _active_tasks[task_id]["error"] = str(e)
```

### 3. Progress Updates

```python
# From within analysis services
update_task_progress(
    task_id=task_id,
    current_stage="ball_detection",
    stage_progress=75,
    stage_message="Processing frame 1200 of 1500",
    overall_progress=45
)
```

### 4. Status Monitoring

```python
# Frontend polls for status updates
GET /v0/analysis/status/{task_id}

# Returns:
{
    "task_id": 1,
    "status": "processing",
    "progress": 45,
    "current_stage": "ball_detection",
    "stage_progress": 75,
    "stage_message": "Processing frame 1200 of 1500",
    "started_at": "2024-01-15T10:30:00Z",
    "completed_at": null
}
```

## Task Lifecycle

### States

1. **`queued`** - Task created, waiting for worker thread
2. **`processing`** - Task actively running in background thread
3. **`completed`** - Task finished successfully
4. **`failed`** - Task encountered an error
5. **`cancelled`** - Task was cancelled by user or system

### State Transitions

```
queued → processing → completed
  ↓         ↓           ↓
cancelled  failed    (cleanup)
```

### Lifecycle Example

```python
# 1. Task Creation
POST /v0/analysis/videos/123
→ task_id: 1, status: "queued"

# 2. Task Starts Processing
GET /v0/analysis/status/1
→ status: "processing", progress: 5

# 3. Progress Updates
GET /v0/analysis/status/1
→ status: "processing", progress: 45, stage: "ball_detection"

# 4. Task Completion
GET /v0/analysis/status/1
→ status: "completed", progress: 100, result: {...}

# 5. Cleanup (after 24 hours)
→ Task removed from memory
```

## Progress Tracking

### Two-Level Progress System

#### Overall Progress (0-100%)

- **5%**: Task initialization
- **15%**: Frame extraction
- **30-90%**: Analysis processing (varies by type)
- **95%**: Finalizing results
- **100%**: Task completed

#### Stage Progress (0-100%)

- **Current Stage**: What's happening now
- **Stage Progress**: Progress within current stage
- **Stage Message**: Human-readable description

### Progress Example

```json
{
  "progress": 45,
  "current_stage": "ball_detection",
  "stage_progress": 75,
  "stage_message": "Processing frame 1200 of 1500"
}
```

**Translation**: Overall task is 45% complete, currently in ball detection stage which is 75% complete, processing frame 1200 of 1500.

## Current Limitations

### 1. In-Memory Storage

**Problem**: Tasks are stored in memory, lost on server restart.

```python
# Current implementation
_active_tasks: Dict[int, Dict[str, Any]] = {}  # Lost on restart!
```

**Impact**:

- Server restart loses all task history
- No persistence across deployments
- Memory usage grows with task count

### 2. Single Server Limitation

**Problem**: Tasks only work on single server instance.

**Impact**:

- No horizontal scaling
- Load balancer issues
- No failover capability

### 3. No Task Persistence

**Problem**: Completed tasks are cleaned up after 24 hours.

**Impact**:

- No historical task data
- No audit trail
- No performance analytics

### 4. Limited Concurrency

**Problem**: Fixed thread pool size (default: 2 workers).

**Impact**:

- May not utilize all available CPU cores
- No dynamic scaling based on load
- No priority queuing

## Redis Migration Plan

### Why Redis?

**Benefits**:

- **Persistence**: Tasks survive server restarts
- **Scalability**: Multiple servers can share task queue
- **Performance**: Fast in-memory operations with disk persistence
- **Features**: Built-in expiration, pub/sub, clustering
- **Industry Standard**: Widely used for background task queues

### Migration Strategy

#### Phase 1: Redis Integration (2-3 weeks)

```python
# New Redis-based task storage
import redis
import json

class RedisTaskStorage:
    def __init__(self, redis_url: str):
        self.redis = redis.from_url(redis_url)
        self.task_prefix = "task:"
        self.task_ttl = 86400  # 24 hours

    def store_task(self, task_id: int, task_data: Dict[str, Any]) -> None:
        key = f"{self.task_prefix}{task_id}"
        self.redis.setex(key, self.task_ttl, json.dumps(task_data))

    def get_task(self, task_id: int) -> Optional[Dict[str, Any]]:
        key = f"{self.task_prefix}{task_id}"
        data = self.redis.get(key)
        return json.loads(data) if data else None

    def update_task_progress(self, task_id: int, updates: Dict[str, Any]) -> None:
        key = f"{self.task_prefix}{task_id}"
        current = self.get_task(task_id)
        if current:
            current.update(updates)
            self.redis.setex(key, self.task_ttl, json.dumps(current))
```

#### Phase 2: Task Queue Implementation (1-2 weeks)

```python
# Redis-based task queue
class RedisTaskQueue:
    def __init__(self, redis_url: str):
        self.redis = redis.from_url(redis_url)
        self.queue_name = "analysis_queue"

    def enqueue_task(self, task_data: Dict[str, Any]) -> int:
        task_id = self.redis.incr("task_counter")
        task_data["task_id"] = task_id
        self.redis.lpush(self.queue_name, json.dumps(task_data))
        return task_id

    def dequeue_task(self) -> Optional[Dict[str, Any]]:
        data = self.redis.brpop(self.queue_name, timeout=1)
        return json.loads(data[1]) if data else None
```

#### Phase 3: Worker Process Implementation (1-2 weeks)

```python
# Dedicated worker processes
class AnalysisWorker:
    def __init__(self, redis_url: str):
        self.queue = RedisTaskQueue(redis_url)
        self.storage = RedisTaskStorage(redis_url)

    def run(self):
        while True:
            task = self.queue.dequeue_task()
            if task:
                self.process_task(task)

    def process_task(self, task: Dict[str, Any]):
        task_id = task["task_id"]
        try:
            # Update status to processing
            self.storage.update_task_progress(task_id, {"status": "processing"})

            # Run analysis
            result = self.run_analysis(task)

            # Mark completed
            self.storage.update_task_progress(task_id, {
                "status": "completed",
                "result": result,
                "completed_at": datetime.now().isoformat()
            })
        except Exception as e:
            # Mark failed
            self.storage.update_task_progress(task_id, {
                "status": "failed",
                "error": str(e),
                "completed_at": datetime.now().isoformat()
            })
```

### Redis Configuration

#### Environment Variables

```bash
# Redis Configuration
REDIS_URL=redis://localhost:6379/0
REDIS_TASK_TTL=86400  # 24 hours
REDIS_QUEUE_NAME=analysis_queue
REDIS_MAX_CONNECTIONS=20
```

#### Docker Compose

```yaml
services:
  redis:
    image: redis:7-alpine
    ports:
      - "6379:6379"
    volumes:
      - redis_data:/data
    command: redis-server --appendonly yes

  backend:
    environment:
      - REDIS_URL=redis://redis:6379/0
    depends_on:
      - redis

volumes:
  redis_data:
```

### Migration Benefits

#### Before (In-Memory)

- ❌ Tasks lost on restart
- ❌ Single server only
- ❌ No horizontal scaling
- ❌ Memory leaks possible

#### After (Redis)

- ✅ Tasks persist across restarts
- ✅ Multiple servers supported
- ✅ Horizontal scaling
- ✅ Built-in expiration and cleanup
- ✅ Task queue with priority support
- ✅ Real-time progress via pub/sub
- ✅ Performance monitoring

## API Integration

### Starting Analysis

```python
# POST /v0/analysis/videos/{video_id}
{
    "analysis_type": "ball_only",
    "confidence_threshold": 0.7
}

# Response
{
    "analysis_id": 1,
    "video_filename": "tennis_video.mp4",
    "status": "processing",
    "message": "Analysis started successfully",
    "estimated_duration": 60.0
}
```

### Monitoring Progress

```python
# GET /v0/analysis/status/{analysis_id}
{
    "analysis_id": 1,
    "status": "processing",
    "progress": 45,
    "current_stage": "ball_detection",
    "stage_progress": 75,
    "stage_message": "Processing frame 1200 of 1500",
    "created_at": "2024-01-15T10:30:00Z",
    "completed_at": null
}
```

### Getting Results

```python
# GET /v0/analysis/{analysis_id}
{
    "id": 1,
    "video_id": 123,
    "analysis_type": "ball_only",
    "status": "completed",
    "progress": 100,
    "total_frames": 1500,
    "frames_with_balls": 1200,
    "detection_rate": 0.8,
    "processing_time": 180.5,
    "model_used": "yolov8n.pt",
    "confidence_threshold": 0.7,
    "created_at": "2024-01-15T10:30:00Z",
    "completed_at": "2024-01-15T10:33:00Z"
}
```

### Frontend Integration

```typescript
// Start analysis
const response = await api.startAnalysis(videoId, "ball_only", 0.7);
const taskId = response.analysis_id;

// Poll for status updates
const pollStatus = async () => {
  const status = await api.getAnalysisStatus(taskId);

  if (status.status === "completed") {
    // Get final results
    const results = await api.getAnalysis(taskId);
    return results;
  } else if (status.status === "failed") {
    throw new Error(status.error);
  } else {
    // Update progress UI
    updateProgressBar(status.progress);
    updateStatusMessage(status.stage_message);

    // Continue polling
    setTimeout(pollStatus, 2000);
  }
};

pollStatus();
```

## Troubleshooting

### Common Issues

#### 1. Task Stuck in "Queued" State

**Symptoms**: Task never moves from "queued" to "processing"

**Causes**:

- Thread pool exhausted (all workers busy)
- Server overloaded
- Database connection issues

**Solutions**:

```python
# Check thread pool status
stats = background_service.get_task_stats()
print(f"Active workers: {stats['active_workers']}")
print(f"Max workers: {stats['max_workers']}")

# Increase worker count if needed
background_service = BackgroundTaskService(max_workers=4)
```

#### 2. Task Fails with Database Errors

**Symptoms**: Task status shows "failed" with database-related error

**Causes**:

- Database connection timeout
- Transaction conflicts
- Schema issues

**Solutions**:

```python
# Check database connection
with get_background_db_session() as db:
    db.execute("SELECT 1")  # Test connection

# Use proper session management
@contextmanager
def get_background_db_session():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
```

#### 3. Memory Usage Growing

**Symptoms**: Server memory usage increases over time

**Causes**:

- Tasks not being cleaned up
- Memory leaks in analysis services
- Large video files in memory

**Solutions**:

```python
# Enable automatic cleanup
background_service.cleanup_completed_tasks(max_age_hours=1)

# Monitor memory usage
import psutil
memory_usage = psutil.Process().memory_info().rss / 1024 / 1024
print(f"Memory usage: {memory_usage:.2f} MB")
```

#### 4. Progress Updates Not Working

**Symptoms**: Progress stays at 0% or doesn't update

**Causes**:

- Progress utility not initialized
- Task ID mismatch
- Threading issues

**Solutions**:

```python
# Ensure progress utility is initialized
from app.utils.progress_utils import set_task_storage
set_task_storage(_active_tasks, _task_lock)

# Check task ID consistency
print(f"Task ID in progress update: {task_id}")
print(f"Task ID in storage: {list(_active_tasks.keys())}")
```

### Debugging Tools

#### 1. Task Statistics

```python
# Get comprehensive task statistics
stats = background_service.get_task_stats()
print(f"Total tasks: {stats['total_tasks']}")
print(f"Status counts: {stats['status_counts']}")
print(f"Active workers: {stats['active_workers']}")
```

#### 2. Task Inspection

```python
# Inspect specific task
task = background_service.get_task_status(task_id)
print(f"Task status: {task['status']}")
print(f"Progress: {task['progress']}%")
print(f"Current stage: {task['current_stage']}")
print(f"Error: {task.get('error', 'None')}")
```

#### 3. Log Analysis

```bash
# Monitor background task logs
tail -f logs/background_service.log | grep "Task 123"

# Check for errors
grep "ERROR" logs/background_service.log | tail -20
```

### Performance Optimization

#### 1. Worker Tuning

```python
# Adjust based on CPU cores and workload
import os
cpu_count = os.cpu_count()
max_workers = min(cpu_count, 4)  # Don't exceed 4 workers
background_service = BackgroundTaskService(max_workers=max_workers)
```

#### 2. Memory Management

```python
# Regular cleanup
import schedule
import time

def cleanup_tasks():
    cleaned = background_service.cleanup_completed_tasks(max_age_hours=1)
    print(f"Cleaned up {cleaned} old tasks")

schedule.every(30).minutes.do(cleanup_tasks)

while True:
    schedule.run_pending()
    time.sleep(60)
```

#### 3. Database Optimization

```python
# Use connection pooling
from sqlalchemy.pool import QueuePool

engine = create_engine(
    DATABASE_URL,
    poolclass=QueuePool,
    pool_size=10,
    max_overflow=20,
    pool_pre_ping=True
)
```

## Future Enhancements

### 1. Priority Queues

```python
# High priority for small videos, low priority for large ones
def calculate_priority(video_duration: float) -> int:
    if video_duration < 30:
        return 1  # High priority
    elif video_duration < 120:
        return 2  # Medium priority
    else:
        return 3  # Low priority
```

### 2. Task Dependencies

```python
# Chain analysis tasks
def start_analysis_pipeline(video_id: int):
    # Step 1: Ball detection
    ball_task = start_analysis_task(video_id, "ball_only")

    # Step 2: Pose detection (can run in parallel)
    pose_task = start_analysis_task(video_id, "pose_only")

    # Step 3: Video annotation (waits for ball OR pose)
    annotation_task = start_analysis_task(video_id, "video_annotation_only")
```

### 3. Real-time Notifications

```python
# WebSocket notifications for progress updates
class TaskNotificationService:
    def __init__(self):
        self.connections = set()

    async def notify_progress(self, task_id: int, progress: int):
        message = {
            "type": "task_progress",
            "task_id": task_id,
            "progress": progress
        }
        for connection in self.connections:
            await connection.send(json.dumps(message))
```

### 4. Task Scheduling

```python
# Schedule analysis for later
def schedule_analysis(video_id: int, run_at: datetime):
    delay = (run_at - datetime.now()).total_seconds()
    threading.Timer(delay, start_analysis_task, args=[video_id, "ball_only"]).start()
```

## Summary

The background task system is essential for handling computationally expensive video analysis operations. The current implementation provides:

- ✅ **Immediate API responses** with task tracking
- ✅ **Progress monitoring** with detailed stage information
- ✅ **Error handling** and task cancellation
- ✅ **Thread-safe operations** with proper locking
- ✅ **Modular architecture** supporting different analysis types

**Current limitations** (in-memory storage, single server) are planned to be addressed with **Redis migration**, which will provide:

- ✅ **Persistence** across server restarts
- ✅ **Horizontal scaling** with multiple servers
- ✅ **Task queues** with priority support
- ✅ **Real-time notifications** via pub/sub
- ✅ **Performance monitoring** and analytics

This system enables the Tennis Coach App to provide responsive user experience while performing complex computer vision analysis in the background.
