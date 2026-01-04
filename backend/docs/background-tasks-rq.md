# Background Tasks with Redis Queue (RQ)

Complete guide to the background task system using Redis Queue (RQ) in the Tennis Coach App. This system replaces the in-memory `ThreadPoolExecutor` with a robust, scalable solution that works across multiple servers and survives restarts.

**This is the primary documentation for background task processing.** For information about the deprecated ThreadPoolExecutor system, see [Background Tasks (Legacy)](background-tasks.md).

**Legacy System Reference**: The previous `BackgroundTaskService` implementation using ThreadPoolExecutor can be found in [`backend/app/services/background_service.py`](../app/services/background_service.py). This file contains the original analysis methods (`_run_pose_only_analysis`, `_run_ball_only_analysis`, etc.) that have been migrated to RQ task functions.

## Table of Contents

- [Overview](#overview)
- [Architecture](#architecture)
- [How RQ Works](#how-rq-works)
- [Local Development Setup](#local-development-setup)
- [Production Setup (Render)](#production-setup-render)
- [Worker Deployment](#worker-deployment)
- [Configuration](#configuration)
- [Task Implementation](#task-implementation)
- [Monitoring](#monitoring)
- [Troubleshooting](#troubleshooting)

## Overview

### Why Redis Queue?

**RQ (Redis Queue)** is a simple Python library for queueing jobs and processing them in the background with workers. It provides:

- ✅ **Persistence**: Tasks survive server restarts
- ✅ **Scalability**: Multiple workers can process tasks in parallel
- ✅ **Reliability**: Failed jobs are tracked and can be retried
- ✅ **Monitoring**: Built-in dashboard for job status
- ✅ **Simplicity**: Much simpler than Celery for our use case

### What Tasks Use RQ?

RQ is used for **CPU and memory-intensive operations** that would block the API:

- **Pose Detection**: MediaPipe pose estimation (1-3 minutes)
- **Ball Detection**: YOLO ball detection (2-4 minutes)
- **Video Annotation**: Creating annotated videos with overlays (1-2 minutes)
- **Combined Analysis**: Pose detection + annotation pipeline

**Not used for**: Fast operations like database queries, simple API responses, or file uploads.

## Architecture

### System Overview

```
┌─────────────────┐
│   FastAPI App   │  ← Enqueues jobs to Redis
│  (API Server)   │     Returns job_id immediately
└────────┬────────┘
         │
         │ enqueue()
         ▼
┌─────────────────┐
│     Redis       │  ← Job queue storage
│   (Message      │     Job status tracking
│    Broker)      │     Job results storage
└────────┬────────┘
         │
         │ dequeue()
         ▼
┌─────────────────┐
│  RQ Workers     │  ← Process jobs
│  (Separate      │     Execute analysis tasks
│   Processes)     │     Update job status
└─────────────────┘
```

### Key Concepts

- **Queue**: Named list of jobs (e.g., "analysis", "default")
- **Job**: Single task to be executed
- **Worker**: Process that executes jobs from queues
- **Redis**: Stores queues, job data, and results

## How RQ Works

### Job Storage in Redis

RQ does **not** store Python code or machine code. It stores:

1. **Function reference**: Module path + function name (string)
   - Example: `"app.services.analysis.analyze_video_rq"`
2. **Arguments**: Serialized function arguments (JSON/pickle)
   - Example: `[123]` and `{"confidence_threshold": 0.7}`

**What gets stored in Redis:**

```json
{
  "func": "app.services.analysis.analyze_video_rq",
  "args": [123],
  "kwargs": { "confidence_threshold": 0.7 },
  "job_id": "abc123-def456-...",
  "status": "queued"
}
```

### Worker Execution Flow

```
1. API enqueues job
   ↓
2. RQ stores in Redis:
   - Function path: "app.services.analysis.analyze_video_rq"
   - Arguments: [123], {"confidence_threshold": 0.7}
   ↓
3. Worker (separate process) polls Redis
   ↓
4. Worker reads job data
   ↓
5. Worker imports function:
   from app.services.analysis import analyze_video_rq
   ↓
6. Worker executes:
   result = analyze_video_rq(123, confidence_threshold=0.7)
   ↓
7. Worker stores result in Redis
   ↓
8. Client polls API → API reads result from Redis
```

### Worker Process Requirements

**Critical**: Workers must have access to the **same codebase** as the API:

- ✅ Same source code (same repository, same functions)
- ✅ Same Python dependencies installed
- ✅ Same imports available
- ✅ Network access to Redis
- ✅ Access to shared resources (database, storage)

**Workers can run on**:

- Same machine (different processes) - **Local development**
- Same server (different processes) - **Render (same service)**
- Separate Render service - **Render (separate service)**
- Separate machines/instances - **EC2, other cloud providers**

## Local Development Setup

### Prerequisites

- Docker Desktop (for Redis)
- Python 3.8+
- Redis client: `pip install redis rq`

### Quick Start

```bash
# 1. Start Redis
docker-compose up redis -d

# 2. Configure environment (.env file)
REDIS_URL=redis://localhost:6379/0
ENVIRONMENT=development

# 3. Start worker
cd backend
./scripts/start_rq_worker.sh

# 4. (Optional) Start dashboard
rq-dashboard --redis-url=redis://localhost:6379/0 --port 9181
```

### Worker Configuration

For M1 MacBook Pro (8 cores, 8GB RAM):

- **Recommended**: 2-4 workers
- Start multiple workers in separate terminals for parallel processing

**Note for macOS**: The startup script automatically sets `OBJC_DISABLE_INITIALIZE_FORK_SAFETY=YES` to handle fork() conflicts with Objective-C runtime.

## Production Setup (Render)

### Render Key Value Service

1. Create Key Value instance in Render dashboard (same region as API service)
2. **Important**: Set **Maxmemory Policy** to `noeviction` (recommended for job queues to prevent job loss)
3. Get **internal URL** from Render Dashboard (format: `redis://red-xxxxx:6379`)
   - Use internal URL for lower latency and private network communication
   - Internal URL doesn't require authentication by default
4. Set environment variable: `REDIS_URL=redis://red-xxxxx:6379/0`
5. Set `ENVIRONMENT=production`

**Instance Configuration:**
- **Free tier**: 25MB RAM, 10 connections, no persistence (data lost on restart)
- **Paid tier**: More RAM, more connections, persists data to disk every second
- Choose instance type based on workload
- API service and Key Value must be in same region and workspace

### Worker Deployment Options

#### Option 1: Same Service (Free Tier)

Run worker in the same Render service as API using FastAPI's `lifespan` context manager:

```python
# In backend/app/main.py
import os
import subprocess
from contextlib import asynccontextmanager
from fastapi import FastAPI
from rq import Worker

@asynccontextmanager
async def lifespan(app: FastAPI) -> None:
    # Startup
    worker_process = None
    if os.getenv("ENVIRONMENT") == "production":
        worker_process = start_rq_worker()
    
    yield
    
    # Shutdown
    if worker_process:
        worker_process.terminate()
        worker_process.wait()

def start_rq_worker() -> subprocess.Popen:
    """Start RQ worker process with duplicate check."""
    # Check for existing workers to prevent duplicates
    try:
        from app.core.redis_config import redis_conn
        existing_workers = Worker.all(connection=redis_conn)
        if existing_workers:
            logger.warning(f"Found {len(existing_workers)} existing workers, skipping startup")
            return None
    except Exception as e:
        logger.warning(f"Could not check for existing workers: {e}")
    
    redis_url = os.getenv("REDIS_URL")
    if not redis_url:
        raise ValueError("REDIS_URL not set in production")
    
    logger.info("Starting RQ worker process")
    return subprocess.Popen([
        "rq", "worker", "analysis", "default",
        "--url", redis_url
    ])

app = FastAPI(lifespan=lifespan)
```

**Integration Steps:**
1. Add worker startup function to `backend/app/main.py`
2. Integrate into `lifespan` context manager
3. Worker auto-starts when API service starts
4. Worker gracefully terminates on API shutdown

**Limitations**: Free tier (512MB RAM, 0.5 CPU) - **1 worker only**

#### Option 2: Separate Service (Paid Tier)

Create separate Render service for workers:

1. **New Web Service** → Same repo
2. **Start Command**: `rq worker analysis default --url $REDIS_URL`
3. **Environment**: Same Redis URL as main service

**Benefits**: Independent scaling, better resource allocation

### Render Considerations

**Free Tier**:

- Single worker recommended
- Monitor memory usage (video analysis is memory-intensive)

**Paid Tier**:

- Can run multiple workers
- Better resource allocation
- Horizontal scaling possible

## Worker Deployment

### Deployment Architectures

#### Local Development

```
┌─────────────────────────────────┐
│      Your Machine (MacBook)     │
│                                 │
│  Process 1: FastAPI (port 8000)│
│  Process 2: RQ Worker          │
│  Process 3: RQ Worker          │
│  Docker: Redis (port 6379)     │
└─────────────────────────────────┘
```

#### Production: Same Service (Render Free Tier)

```
┌─────────────────────────────────┐
│      Render Service             │
│                                 │
│  Process 1: FastAPI            │
│  Process 2: RQ Worker          │
│                                 │
│  → Render Redis (separate)      │
└─────────────────────────────────┘
```

## Configuration

### Redis Connection

Configuration in `backend/app/core/redis_config.py`:

```python
import logging
import os
from redis import Redis
from rq import Queue

logger = logging.getLogger(__name__)

REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379/0")

try:
    redis_conn = Redis.from_url(REDIS_URL)
    redis_conn.ping()  # Test connection
    logger.info(f"Connected to Redis at {REDIS_URL}")
except Exception as e:
    logger.error(f"Failed to connect to Redis: {e}")
    raise

# Create queues
analysis_queue = Queue("analysis", connection=redis_conn)
default_queue = Queue("default", connection=redis_conn)
```

### Queue Strategy

- **`analysis`**: Video analysis tasks (CPU/memory intensive, 2-5 min)
- **`default`**: General tasks (lighter, faster)

### Environment Variables

| Variable      | Description                          | Default                    | Required |
| ------------- | ------------------------------------ | -------------------------- | -------- |
| `REDIS_URL`   | Redis connection string for RQ       | `redis://localhost:6379/0` | Yes      |
| `ENVIRONMENT` | Environment (development/production) | `development`              | No       |

## Task Implementation

### Task Functions

Tasks are regular Python functions:

```python
from pathlib import Path
from typing import Any, Dict

def analyze_pose_detection(
    video_id: int,
    video_path: str,
    confidence_threshold: float = 0.5,
) -> Dict[str, Any]:
    """Analyze video for pose detection."""
    from app.services.pose_detection import PoseDetectionService

    service = PoseDetectionService()
    results = service.analyze_video_file(
        video_path=Path(video_path),
        confidence_threshold=confidence_threshold,
    )

    return {
        "status": "completed",
        "video_id": video_id,
        "results": results,
    }
```

### Enqueuing Tasks

```python
from typing import Dict, Any
from app.core.redis_config import analysis_queue
from app.services.rq_tasks import analyze_pose_detection

def start_analysis_task(
    video_id: int,
    video_path: str,
    confidence_threshold: float = 0.5,
) -> Dict[str, Any]:
    """Enqueue analysis task."""
    job = analysis_queue.enqueue(
        analyze_pose_detection,
        video_id=video_id,
        video_path=video_path,
        confidence_threshold=confidence_threshold,
        job_timeout=300,  # 5 minutes
    )
    return {"job_id": job.id, "status": "queued"}
```

### Job Options

- `job_timeout`: Maximum execution time (seconds)
- `job_id`: Custom job identifier
- `result_ttl`: How long to keep result (default: 500 seconds)

### Retry Configuration

RQ supports automatic retries for failed jobs. Configure retries per task type:

```python
from rq import Retry

# Pose detection: 2 retries with 60s interval
job = analysis_queue.enqueue(
    analyze_pose_detection_rq,
    video_id=video_id,
    video_path=video_path,
    retry=Retry(max=2, interval=60),
    job_timeout=300,
)

# Ball detection: 2 retries with 60s interval
job = analysis_queue.enqueue(
    analyze_ball_detection_rq,
    video_id=video_id,
    video_path=video_path,
    retry=Retry(max=2, interval=60),
    job_timeout=300,
)

# Video annotation: 1 retry with 30s interval
job = analysis_queue.enqueue(
    create_video_annotation_rq,
    video_id=video_id,
    video_path=video_path,
    retry=Retry(max=1, interval=30),
    job_timeout=180,
)

# Combined tasks: 1 retry with 90s interval
job = analysis_queue.enqueue(
    analyze_pose_with_annotation_rq,
    video_id=video_id,
    video_path=video_path,
    retry=Retry(max=1, interval=90),
    job_timeout=360,
)
```

### Failure Handling

**Error Handling in Tasks:**
- Tasks should log errors before re-raising
- RQ automatically marks jobs as failed when exceptions are raised
- Failed jobs can be inspected and retried

**Failure Callbacks:**
```python
def on_failure(job, exc_type, exc_value, traceback):
    """Handle job failure."""
    logger.error(f"Job {job.id} failed: {exc_value}")
    # Could send alert, update database, etc.

job = analysis_queue.enqueue(
    analyze_pose_detection_rq,
    video_id=video_id,
    on_failure=on_failure,
)
```

**Job Timeout Handling:**
- Jobs exceeding `job_timeout` are automatically killed
- Worker marks job as failed
- Timeout should be set based on analysis type (pose: 300s, ball: 300s, annotation: 180s)

**Result TTL:**
- Results are stored in Redis with TTL (time-to-live)
- Default: 500 seconds
- Expired results return `None` when fetching job result
- Set `result_ttl` based on how long results need to be accessible

**Monitoring Failed Jobs:**
- Use RQ Dashboard to view failed jobs
- Use `rq-monitoring` utilities to list and requeue failed jobs
- Failed jobs can be manually retried via API endpoint

## Monitoring

### RQ Dashboard

```bash
# Local development
rq-dashboard --redis-url=redis://localhost:6379/0 --port 9181
# Access at: http://localhost:9181
```

**Production**: Not recommended to expose publicly. Use Render logs or internal monitoring.

### Queue Statistics

```python
from typing import Dict, Any
from app.core.redis_config import analysis_queue, redis_conn
from rq import Worker

def get_queue_stats() -> Dict[str, Any]:
    """Get queue and worker statistics."""
    queue_length = len(analysis_queue)
    workers = Worker.all(connection=redis_conn)
    worker_count = len(workers)
    return {
        "queue_length": queue_length,
        "worker_count": worker_count,
    }
```

### Redis CLI

```bash
docker exec -it tennis-coach-redis redis-cli

# Check queue length
LLEN rq:queue:analysis

# Check job status
HGETALL rq:job:<job_id>
```

## Troubleshooting

### Jobs Stuck in "Queued"

**Causes**: No workers running, workers crashed, Redis connection issues

**Solutions**:

1. Check workers: `ps aux | grep rq worker`
2. Check worker logs for errors
3. Verify Redis: `redis-cli ping`
4. Restart workers

### Jobs Failing Immediately

**Causes**: Import errors, missing dependencies, fork issues (macOS)

**Solutions**:

1. Check worker logs for error messages
2. Test task function directly (not via RQ)
3. Ensure all imports available in worker environment
4. On macOS: Set `OBJC_DISABLE_INITIALIZE_FORK_SAFETY=YES`

### Memory Issues

**Causes**: Too many workers, large video files, memory leaks

**Solutions**:

1. Reduce worker count
2. Process smaller videos
3. Monitor memory: `docker stats` or Render metrics
4. Check for memory leaks

### Redis Connection Errors

**Causes**: Redis not running, wrong Redis URL, network issues

**Solutions**:

1. Verify Redis: `docker ps | grep redis`
2. Check Redis URL: `echo $REDIS_URL`
3. Test connection: `redis-cli -u $REDIS_URL ping`
4. Check firewall/network settings (production)

### macOS Fork Issues

**Symptoms**: `objc[pid]: +[NSNumber initialize] may have been in progress`

**Solution**: Set environment variable before starting worker:

```bash
export OBJC_DISABLE_INITIALIZE_FORK_SAFETY=YES
rq worker analysis default
```

Or use the startup script which handles this automatically.

## Using Redis for Multiple Purposes

**Note**: Currently, Redis is only used for RQ. Caching is not yet implemented but can be added later using the same Redis instance.

A single Redis instance can handle multiple use cases using different databases:

- **Database 0**: RQ task queues and job data (current)
- **Database 1**: Application caching (future)

**Configuration**:

```python
# RQ uses database 0
REDIS_URL=redis://localhost:6379/0

# Caching would use database 1 (future)
REDIS_CACHE_URL=redis://localhost:6379/1
```

**Benefits**: One Redis instance, logical separation, cost-effective.

## Migration from ThreadPoolExecutor

### Current System (To Be Deprecated)

The current `BackgroundTaskService` uses:

- **ThreadPoolExecutor**: Threads in same process as API
- **In-memory storage**: `_active_tasks` dictionary
- **Single server**: No horizontal scaling
- **Tasks lost on restart**: No persistence

### Migration Strategy

Migrate gradually, one analysis type at a time, allowing both systems to coexist:

```
┌─────────────────────────────────────────────────────────────┐
│                    Migration Timeline                       │
└─────────────────────────────────────────────────────────────┘

Phase 1: Setup (✅ Complete)
┌─────────────────────────────────────────────────────────┐
│ • Redis configured in docker-compose                    │
│ • RQ infrastructure ready                               │
│ • Test tasks working                                    │
└─────────────────────────────────────────────────────────┘
         │
         ▼
Phase 2: Parallel Operation (Current)
┌─────────────────────────────────────────────────────────┐
│  API Endpoint                                           │
│  ┌──────────────────────────────────────┐              │
│  │  POST /analysis/videos/{id}          │              │
│  └──────────────┬───────────────────────┘              │
│                 │                                       │
│        ┌────────┴────────┐                              │
│        │                 │                              │
│        ▼                 ▼                              │
│  ┌──────────┐      ┌──────────┐                        │
│  │ ThreadPool│      │   RQ     │                        │
│  │ Executor  │      │  Queue   │                        │
│  │ (Old)     │      │  (New)   │                        │
│  └──────────┘      └──────────┘                        │
│        │                 │                              │
│        │                 │                              │
│        ▼                 ▼                              │
│  ┌──────────┐      ┌──────────┐                        │
│  │ In-Memory│      │  Redis    │                        │
│  │ Storage  │      │  Storage  │                        │
│  └──────────┘      └──────────┘                        │
│                                                          │
│  Both systems active, migrate one type at a time        │
└─────────────────────────────────────────────────────────┘
         │
         ▼
Phase 3: Gradual Migration
┌─────────────────────────────────────────────────────────┐
│  Step 1: Migrate pose_only                              │
│    • Create RQ task: analyze_pose_detection()            │
│    • Update API to use RQ for pose_only                 │
│    • Test thoroughly                                    │
│    • Keep ThreadPoolExecutor for other types            │
│                                                          │
│  Step 2: Migrate ball_only                              │
│    • Create RQ task: analyze_ball_detection()            │
│    • Update API to use RQ for ball_only                 │
│    • Test thoroughly                                    │
│                                                          │
│  Step 3: Migrate video_annotation_only                  │
│    • Create RQ task: create_video_annotation()          │
│    • Update API to use RQ                               │
│                                                          │
│  Step 4: Migrate pose_with_annotation                   │
│    • Create RQ task: analyze_pose_with_annotation()     │
│    • Update API to use RQ                               │
└─────────────────────────────────────────────────────────┘
         │
         ▼
Phase 4: Deprecation (Final)
┌─────────────────────────────────────────────────────────┐
│  • All analysis types using RQ                          │
│  • Remove ThreadPoolExecutor code                      │
│  • Remove BackgroundTaskService                        │
│  • Remove in-memory task storage                        │
│  • Clean up old API endpoints                           │
│                                                          │
│  ┌──────────────────────────────────────┐              │
│  │  API Endpoint                         │              │
│  │  POST /analysis/videos/{id}          │              │
│  └──────────────┬───────────────────────┘              │
│                 │                                       │
│                 ▼                                       │
│          ┌──────────┐                                   │
│          │   RQ     │                                   │
│          │  Queue   │                                   │
│          └────┬─────┘                                   │
│               │                                         │
│               ▼                                         │
│          ┌──────────┐                                   │
│          │  Redis   │                                   │
│          │  Storage │                                   │
│          └──────────┘                                   │
│                                                          │
│  Only RQ system active                                   │
└─────────────────────────────────────────────────────────┘
```

### Migration Implementation

#### Step 1: Create RQ Task Functions

Convert existing analysis methods to RQ tasks:

```python
# backend/app/services/rq_tasks.py (create this file for RQ task functions)

import logging
from pathlib import Path
from typing import Any, Dict, Optional

from app.core.database import SessionLocal
from app.services.pose_detection import PoseDetectionService

logger = logging.getLogger(__name__)

def analyze_pose_detection_rq(
    video_id: int,
    video_path: str,
    confidence_threshold: float = 0.5,
    task_id: Optional[str] = None,
) -> Dict[str, Any]:
    """
    RQ task for pose detection analysis.

    Replaces: BackgroundTaskService._run_pose_only_analysis()

    Args:
        video_id: Video ID from database
        video_path: Path to video file
        confidence_threshold: Detection confidence threshold
        task_id: Optional task identifier for tracking

    Returns:
        Analysis results dictionary

    Raises:
        ValueError: If video not found or analysis fails
        RuntimeError: If pose detection service fails
    """
    try:
        with SessionLocal() as db:
            service = PoseDetectionService()
            results = service.analyze_video_file(
                video_path=Path(video_path),
                confidence_threshold=confidence_threshold,
            )

            if "error" in results:
                raise RuntimeError(f"Pose detection failed: {results['error']}")

            pose_detection = service.save_detection_results(
                db=db, video_id=video_id, detection_results=results
            )

            return {
                "status": "completed",
                "pose_detection_id": pose_detection.id,
                "results": results,
            }
    except Exception as e:
        logger.error(f"RQ task failed for video {video_id}: {e}")
        raise
```

#### Step 2: Update API Endpoint (Gradual)

Add RQ support alongside existing system:

```python
# backend/app/api/routes/analysis.py

from typing import Dict, Any
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.redis_config import analysis_queue
from app.services.rq_tasks import analyze_pose_detection_rq
from app.services.background_service import background_service

router = APIRouter()

@router.post("/videos/{video_id}")
async def start_analysis(
    video_id: int,
    analysis_type: str,
    use_rq: bool = True,  # Feature flag for gradual migration
    db: Session = Depends(get_db),
) -> Dict[str, Any]:
    """
    Start analysis - supports both old and new systems.

    During migration, use_rq flag allows gradual transition.
    """
    # Get video to validate it exists and get path
    from app.services import video_service
    video = video_service.get_video_by_id(db, video_id)
    if not video:
        raise ValueError(f"Video {video_id} not found")

    if use_rq and analysis_type == "pose_only":
        # Use RQ (new system)
        job = analysis_queue.enqueue(
            analyze_pose_detection_rq,
            video_id=video_id,
            video_path=video.file_path,
            confidence_threshold=0.5,
            job_timeout=300,
        )
        return {"job_id": job.id, "status": "queued", "system": "rq"}
    else:
        # Use ThreadPoolExecutor (old system - during migration)
        task_id = background_service.start_analysis_task(
            video_id=video_id,
            analysis_type=analysis_type,
        )
        return {"task_id": task_id, "status": "queued", "system": "threadpool"}
```

#### Step 3: Unified Status Endpoint

Create endpoint that works with both systems:

```python
import logging
from typing import Dict, Any
from rq.job import Job
from redis.exceptions import ConnectionError as RedisConnectionError

from app.core.redis_config import redis_conn
from app.services.background_service import background_service

logger = logging.getLogger(__name__)

@router.get("/status/{task_id}")
async def get_analysis_status(task_id: str) -> Dict[str, Any]:
    """
    Get status - works with both RQ and ThreadPoolExecutor.

    Tries RQ first, falls back to ThreadPoolExecutor during migration.
    """
    # Try RQ first
    try:
        job = Job.fetch(task_id, connection=redis_conn)
        return {
            "task_id": task_id,
            "status": job.get_status(),
            "system": "rq",
            "result": job.result if job.is_finished else None,
        }
    except (ValueError, RedisConnectionError) as e:
        # Job not found in RQ or Redis connection error
        logger.debug(f"RQ job {task_id} not found, trying ThreadPoolExecutor: {e}")
        # Fall back to ThreadPoolExecutor (during migration)
        try:
            status = background_service.get_task_status(int(task_id))
            if status:
                return {**status, "system": "threadpool"}
        except (ValueError, TypeError) as e:
            logger.debug(f"ThreadPoolExecutor task {task_id} not found: {e}")

    return {"error": "Task not found", "task_id": task_id}
```

### Migration Checklist

- [ ] **Phase 1: Setup** ✅

  - [x] Redis configured
  - [x] RQ infrastructure ready
  - [x] Test tasks working

- [ ] **Phase 2: Migrate pose_only**

  - [ ] Create `analyze_pose_detection_rq()` task
  - [ ] Update API endpoint to use RQ for pose_only
  - [ ] Test thoroughly
  - [ ] Monitor in production

- [ ] **Phase 3: Migrate ball_only**

  - [ ] Create `analyze_ball_detection_rq()` task
  - [ ] Update API endpoint
  - [ ] Test thoroughly

- [ ] **Phase 4: Migrate video_annotation_only**

  - [ ] Create `create_video_annotation_rq()` task
  - [ ] Update API endpoint
  - [ ] Test thoroughly

- [ ] **Phase 5: Migrate pose_with_annotation**

  - [ ] Create combined RQ task
  - [ ] Update API endpoint
  - [ ] Test thoroughly

- [ ] **Phase 6: Deprecation**
  - [ ] All analysis types migrated
  - [ ] Remove `BackgroundTaskService`
  - [ ] Remove ThreadPoolExecutor code
  - [ ] Remove in-memory task storage
  - [ ] Update documentation

### Benefits After Migration

**Before (ThreadPoolExecutor)**:

- ❌ Tasks lost on restart
- ❌ Single server only
- ❌ No horizontal scaling
- ❌ Memory leaks possible
- ❌ Fixed worker count

**After (RQ)**:

- ✅ Tasks persist across restarts
- ✅ Multiple servers supported
- ✅ Horizontal scaling
- ✅ Built-in expiration and cleanup
- ✅ Dynamic worker scaling
- ✅ Better monitoring

## Summary

RQ provides a robust, scalable solution for background task processing:

- ✅ **Simple**: Easier than Celery, perfect for our needs
- ✅ **Reliable**: Tasks persist, can be retried
- ✅ **Scalable**: Multiple workers, multiple servers/instances
- ✅ **Monitorable**: Built-in dashboard and Redis inspection
- ✅ **Production-ready**: Works with Render's managed Redis

The system supports workers on the same machine, same service, separate services, or completely separate instances (EC2, etc.) as long as they have access to the same codebase and can connect to Redis.
