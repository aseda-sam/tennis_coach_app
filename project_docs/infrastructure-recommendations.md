# Infrastructure Recommendations & Codebase Review

**Date:** January 4, 2026  
**Context:** Production deployment on Render free tier experiencing OOM (Out of Memory) errors and worker processing issues  
**Budget Target:** $0-10/month (willing to go slightly higher if necessary)  
**Video Characteristics:** 30 seconds to 5 minutes, can enforce smaller file size/FPS limits

---

## Executive Summary

The application is experiencing **Out of Memory (OOM) errors** on Render's free tier (512MB RAM). The worker process starts correctly but cannot complete video analysis tasks due to insufficient memory. Render's **Starter tier ($7/month) still only provides 512MB RAM** - the memory jump only occurs at **Standard tier ($25/month with 2GB RAM)**.

**Root Cause Identified:** The code loads ALL video frames into memory before processing. A 5-minute video at 30fps requires ~13GB+ of RAM—no cloud tier can handle this pattern efficiently. The fix is to stream frames one at a time instead of loading all at once.

**Recommended Solution:**

1. **Short-term:** Hybrid deployment with worker on Fly.io (~$0-5/month) + aggressive video limits
2. **Medium-term:** Code optimizations (only load needed models, consistent frame skipping)
3. **Long-term:** Implement frame streaming to reduce memory from GB to ~50MB
4. **Future option:** Client-side compute (browser-based processing) - can reduce costs by 50-90% while improving UX

---

## Current Situation

### Issues Identified

1. **OOM Errors on Render Free Tier**

   - Error: `Ran out of memory (used over 512MB) while running your code`
   - Occurs during video analysis (YOLO + MediaPipe + frame processing)
   - Free tier has 512MB RAM limit
   - Starter tier ($7/month) also has 512MB RAM - not sufficient

2. **Worker Startup Behavior**

   - ✅ Worker starts correctly: `Starting RQ worker process`
   - ⚠️ On restart, detects existing worker: `Found 1 existing workers, skipping startup`
   - This is expected behavior (prevents duplicate workers)
   - Worker is functioning but crashes due to OOM

3. **Code Issues Found**
   - **Critical Bug:** `BallDetectionService` uses `self.logger.info()` but `self.logger` is never defined (only module-level `logger` exists)
   - **Worker Logging:** Worker stdout/stderr is piped but not logged, making debugging difficult
   - **Environment Variable Duplication:** `PROFILE=production` vs `ENVIRONMENT=production` - both do the same thing but accessed inconsistently. Recommendation: consolidate to `PROFILE` only.

### Current Architecture

- **API Service:** Render free tier (512MB RAM, 0.5 CPU)
- **Redis:** Render Key Value free tier (25MB RAM, 10 connections)
- **Database:** Supabase PostgreSQL
- **Storage:** Supabase Storage
- **Frontend:** GitHub Pages (static)

### Resource Requirements

**Memory Usage Breakdown:**

- YOLO models (nano): ~100MB
- YOLO models (small): ~200MB
- MediaPipe pose detection: ~100MB
- OpenCV frame buffers: ~50-200MB (depends on video)
- Python runtime + dependencies: ~100MB
- **Total minimum:** ~450MB (just for models + runtime)
- **With video processing:** Easily exceeds 512MB

**CPU Requirements:**

- Video analysis is CPU-intensive
- Current timeouts: 3-6 minutes (may be too aggressive for 0.5 CPU)
- Realistic processing time on low-end CPU: 10-30 minutes for 5-minute videos

---

## Infrastructure Options Analysis

### Option 1: Fly.io Worker (Recommended) ⭐

**Cost:** ~$0-5/month  
**Complexity:** Medium  
**Reliability:** High

**Architecture:**

- Keep API on Render free tier ($0)
- Deploy worker to Fly.io (scales to zero when idle)
- Both connect to same Render Redis
- Both use same Supabase database/storage

**Pros:**

- Generous free tier (3 shared VMs, can combine)
- Pay-as-you-go: ~$0.01/hour for 1GB RAM machine
- Scales to zero when idle (no cost when not processing)
- Docker-based (easy deployment)
- Good documentation

**Cons:**

- Requires separate deployment setup
- Need to manage two services

**Setup Requirements:**

- Create `fly.toml` for worker service
- Deploy worker container with `python scripts/start_rq_worker.py`
- Set environment variables (REDIS_URL, ENVIRONMENT, etc.)

**Estimated Monthly Cost:**

- Light usage (10 users, few times/month): ~$0-2/month
- Moderate usage: ~$3-5/month
- Heavy usage: ~$5-8/month

---

### Option 2: Railway Worker

**Cost:** ~$5-10/month  
**Complexity:** Low  
**Reliability:** High

**Architecture:**

- Keep API on Render free tier
- Deploy worker to Railway
- Both connect to same Redis

**Pros:**

- $5 free credit/month
- Simple deployment (similar to Render)
- Good for hobby projects
- Pay-as-you-go after free credit

**Cons:**

- Minimum 512MB (may still be tight)
- More expensive than Fly.io for similar resources

**Estimated Monthly Cost:**

- After free credit: ~$5-10/month

---

### Option 3: Hetzner VPS

**Cost:** ~$4/month (fixed)  
**Complexity:** High  
**Reliability:** Medium

**Architecture:**

- Keep API on Render free tier
- Deploy worker to Hetzner VPS
- Run worker in Docker container

**Pros:**

- Cheapest fixed-cost option
- 2GB RAM, 1 vCPU guaranteed
- Predictable pricing

**Cons:**

- Most manual setup required
- You manage updates, monitoring
- Less "managed" than PaaS options

**Estimated Monthly Cost:**

- Fixed: ~$4/month (CPX11 instance)

---

### Option 4: Stay on Render + Aggressive Limits (Not Recommended)

**Cost:** $0-7/month  
**Complexity:** Low  
**Reliability:** Low

**Approach:**

- Enforce strict video limits (1 minute, 480p, 20MB)
- Force nano YOLO model only
- High frame skip ratio (every 4th frame)

**Pros:**

- No migration needed
- Lowest cost

**Cons:**

- Still likely to OOM on longer videos
- Poor user experience (strict limits)
- Unreliable for production

**Assessment:** Even with aggressive limits, 512MB is marginal. Short videos (10-15 seconds) might work, but 5-minute videos will likely fail.

---

## Recommended Solution: Hybrid Deployment

### Architecture

```
┌─────────────────┐
│  Render Free    │  API Service (HTTP, auth, enqueue jobs)
│  512MB RAM      │  $0/month
└────────┬────────┘
         │
         │ (Redis Queue)
         │
┌────────▼────────┐
│  Render Redis   │  Job Queue
│  25MB RAM       │  $0/month
└────────┬────────┘
         │
         │ (Process jobs)
         │
┌────────▼────────┐
│  Fly.io Worker  │  Video Analysis (YOLO + MediaPipe)
│  1GB+ RAM       │  ~$0-5/month (scales to zero)
└─────────────────┘
```

### Implementation Steps

1. **Keep API on Render** (no changes needed)
2. **Consolidate configuration** (simplify env vars)
   - Use `PROFILE=production` only (remove `ENVIRONMENT` dependency)
   - Update code to use `settings.PROFILE` consistently
3. **Deploy worker to Fly.io**
   - Create `fly.toml` configuration
   - Set environment variables (`PROFILE=production`, `REDIS_URL`, etc.)
   - Deploy Docker container
4. **Enforce video limits** (reduce OOM risk)
   - Max duration: 2 minutes
   - Max file size: 50MB
   - Frame skip ratio: 3 (every 3rd frame)
5. **Fix code bugs** (ball detection logger issue)

### Cost Breakdown

- Render API: $0/month
- Render Redis: $0/month
- Fly.io Worker: ~$0-5/month (scales to zero)
- Supabase: Already using
- **Total: ~$0-5/month** ✅

---

## Code Issues to Fix

### 1. Critical: Ball Detection Logger Bug

**Location:** `backend/app/services/ball_detection/detection_service.py`

**Issue:** Line 138 uses `self.logger.info()` but `self.logger` is never defined.

**Current Code:**

```python
self.logger.info(
    f"Using YOLO model: {selected_model} (quality: {video_quality_level or 'unknown'})"
)
```

**Fix:**

```python
logger.info(
    f"Using YOLO model: {selected_model} (quality: {video_quality_level or 'unknown'})"
)
```

**Impact:** Will cause `AttributeError` when ball detection runs, crashing the worker.

---

### 2. Worker Logging Visibility

**Location:** `backend/app/main.py` (lines 80-84)

**Issue:** Worker stdout/stderr is piped but not logged, making debugging difficult.

**Current Code:**

```python
return subprocess.Popen(
    ["rq", "worker", "analysis", "default", "--url", redis_url],
    stdout=subprocess.PIPE,
    stderr=subprocess.PIPE,
)
```

**Recommended Fix:** Add logging threads to forward worker output to main logger (see detailed implementation in code review notes).

**Impact:** Makes debugging worker issues much easier.

---

### 3. Environment Variable Consolidation: PROFILE vs ENVIRONMENT

**Issue:** Two similar variables doing essentially the same thing:

- `PROFILE=production` (controls database/storage/auth/docs - well-integrated)
- `ENVIRONMENT=production` (controls worker startup - inconsistently used)

**Current State:**

**PROFILE (well-integrated):**

- Accessed via `settings.PROFILE` (consistent)
- Used in 10+ places throughout codebase
- Controls: database selection, storage type, auth requirement, API docs visibility
- Has helper properties: `is_production`, `auth_required`
- Well-designed abstraction

**ENVIRONMENT (inconsistent):**

- Accessed via `os.getenv("ENVIRONMENT")` directly (bypasses settings)
- Only used in 3 places:
  1. `main.py:111` - Worker startup logic
  2. `redis_config.py:82` - Worker count recommendation
  3. `redis_config.py:107` - Worker info dict
- Not consistently accessed (sometimes `os.getenv`, sometimes `settings.ENVIRONMENT`)

**The Problem:**

They're doing the same thing but accessed differently, creating confusion:

- Which one should I set?
- Why do I need both?
- What if they differ?

**Recommendation: Consolidate to PROFILE Only**

**Why PROFILE is better:**

1. ✅ Already well-integrated — used consistently via `settings.PROFILE`
2. ✅ Better abstraction — has helper properties (`is_production`, `auth_required`)
3. ✅ More semantic — "profile" describes the configuration mode
4. ✅ Single source of truth — one variable controls everything

**The Fix:**

Replace all `ENVIRONMENT` checks with `PROFILE`:

**Current (main.py:111):**

```python
if os.getenv("ENVIRONMENT") == "production" and service_type == "api":
```

**Should be:**

```python
if settings.PROFILE == "production" and service_type == "api":
```

**Current (redis_config.py:82):**

```python
env = os.getenv("ENVIRONMENT", "development").lower()
if env == "production":
```

**Should be:**

```python
from app.core.config import settings
if settings.PROFILE == "production":
```

**Migration Steps:**

1. Update the 3 places that use `ENVIRONMENT` to use `settings.PROFILE`
2. Remove `ENVIRONMENT` from `config.py` (or mark as deprecated)
3. Update documentation to only mention `PROFILE`
4. Update deployment docs (Render env vars only need `PROFILE=production`)

**Impact:** Simplifies configuration, removes confusion, single source of truth.

---

## Video Processing Limits

### Current Limits (from config.py)

```python
MAX_VIDEO_DURATION: int = 300  # 5 minutes
MAX_VIDEO_RESOLUTION: tuple[int, int] = (3840, 2160)  # 4K
MAX_FPS: int = 60
FRAME_SKIP_RATIO: int = 1  # Process every frame
MAX_FILE_SIZE: int = 104857600  # 100MB
```

### Recommended Limits for Production (512MB-1GB RAM)

```python
# Conservative (for 512MB)
MAX_VIDEO_DURATION: int = 60  # 1 minute
MAX_VIDEO_RESOLUTION: tuple[int, int] = (720, 480)  # 480p
MAX_FPS: int = 24
FRAME_SKIP_RATIO: int = 4  # Every 4th frame
MAX_FILE_SIZE: int = 20971520  # 20MB

# Moderate (for 1GB+ RAM)
MAX_VIDEO_DURATION: int = 120  # 2 minutes
MAX_VIDEO_RESOLUTION: tuple[int, int] = (1280, 720)  # 720p
MAX_FPS: int = 30
FRAME_SKIP_RATIO: int = 3  # Every 3rd frame
MAX_FILE_SIZE: int = 52428800  # 50MB
```

### Implementation

These can be set via environment variables or enforced in `backend/app/core/config.py`. The limits are already checked in `backend/app/utils/file_validation.py`.

---

## Deployment Checklist

### Phase 1: Quick Fixes (Before Migration)

- [ ] Fix ball detection logger bug
- [ ] Add `ENVIRONMENT=production` to Render API env vars (if not already set)
- [ ] Enforce stricter video limits (test with short videos)
- [ ] Monitor for OOM errors

### Phase 2: Fly.io Worker Setup

- [ ] Create Fly.io account
- [ ] Install Fly CLI
- [ ] Create `fly.toml` configuration
- [ ] Set up environment variables
- [ ] Deploy worker service
- [ ] Test worker connectivity to Redis
- [ ] Monitor worker logs

### Phase 3: Optimization

- [ ] Tune video limits based on actual usage
- [ ] Add worker health monitoring
- [ ] Set up alerts for failed jobs
- [ ] Document deployment process

---

## Alternative: Render Background Worker Service

**Note:** Render Background Worker service appears to be paid tier only (Starter $7/month = 512MB, Standard $25/month = 2GB).

**Assessment:** Not cost-effective for this use case. Fly.io provides better value for worker-only deployment.

---

## Cost Comparison Summary

| Solution              | Monthly Cost | RAM    | Reliability | Complexity |
| --------------------- | ------------ | ------ | ----------- | ---------- |
| **Fly.io Worker** ⭐  | $0-5         | 1GB+   | High        | Medium     |
| Railway Worker        | $5-10        | 512MB+ | High        | Low        |
| Hetzner VPS           | $4           | 2GB    | Medium      | High       |
| Render Starter        | $7           | 512MB  | Low         | Low        |
| Render Standard       | $25          | 2GB    | High        | Low        |
| Stay on Free + Limits | $0           | 512MB  | Very Low    | Low        |

**Recommendation:** Fly.io Worker provides best balance of cost, reliability, and complexity.

---

## Next Steps

1. **Review this document** and decide on approach
2. **Fix critical bugs** (ball detection logger)
3. **Test with aggressive limits** on current setup
4. **If OOM persists:** Proceed with Fly.io worker deployment
5. **Monitor costs** and adjust as needed

---

## References

- [Render Pricing](https://render.com/pricing)
- [Fly.io Pricing](https://fly.io/docs/about/pricing/)
- [Railway Pricing](https://railway.app/pricing)
- [Hetzner Cloud Pricing](https://www.hetzner.com/cloud)

---

## Codebase Optimization Analysis

This section documents a deep-dive code review focused on memory and CPU efficiency.

### 🚨 Critical Issue: All Frames Loaded Into Memory

**This is the root cause of OOM errors.** The memory problem isn't just about Render's 512MB—the code uses orders of magnitude more memory than necessary.

#### What's Happening

All three frame extraction methods return `List[np.ndarray]`, loading ALL frames into memory before processing:

**video_service.py (lines 230-314):**

```python
frames = []
while frame_count < total_frames:
    ret, frame = cap.read()
    frames.append(frame)  # ← Every frame stays in memory
return frames
```

**ball_detection/detection_service.py (lines 345-391):**

```python
frames = []
while True:
    ret, frame = cap.read()
    frames.append(frame)  # ← Same problem
return frames
```

**pose_detection/detection_service.py (lines 465-505):**

```python
frames = []
while True:
    ret, frame = cap.read()
    frames.append(frame)  # ← Same problem
return frames
```

#### The Math

| Video                 | Frames | Per Frame (1080p) | Total Memory |
| --------------------- | ------ | ----------------- | ------------ |
| 5 min @ 30fps         | 9,000  | ~6MB              | ~54GB        |
| 5 min @ 30fps, skip 4 | 2,250  | ~6MB              | ~13.5GB      |
| 2 min @ 30fps, skip 4 | 900    | ~6MB              | ~5.4GB       |
| 1 min @ 30fps, skip 4 | 450    | ~6MB              | ~2.7GB       |

**Key insight:** Even with aggressive frame skipping, loading all frames before processing requires gigabytes of RAM. No cloud tier can handle this efficiently.

#### The Fix: Stream Frames

Process frames one at a time, never storing more than a few in memory:

```python
# CURRENT (problematic):
frames = extract_all_frames(video)  # 13GB in memory
results = detect_in_frames(frames)  # Process after loading

# RECOMMENDED (streaming):
results = []
cap = cv2.VideoCapture(video)
while True:
    ret, frame = cap.read()
    if not ret:
        break
    result = detect_in_frame(frame)  # Process immediately
    results.append(result)           # Store small result, not 6MB frame
    # frame goes out of scope → garbage collected
```

**Memory impact:** From ~13GB → ~50MB (one frame + model + overhead)

---

### 🔶 Medium Issue: Loading All YOLO Models

**Location:** `ball_detection/detection_service.py` (lines 40-53)

```python
for model_name, model_path in settings.YOLO_MODELS.items():
    self.yolo_models[model_name] = YOLO(model_path)  # Loads BOTH nano AND small
```

**Problem:** Both models are loaded even though only one is used per request.

| Model            | RAM Usage  |
| ---------------- | ---------- |
| YOLO nano        | ~100MB     |
| YOLO small       | ~200MB     |
| **Total loaded** | **~300MB** |

**Fix:** Only load the model that will be used. In production, always use nano.

---

### 🔶 Medium Issue: MediaPipe Heavy Model by Default

**Location:** `pose_detection/detection_service.py` (lines 77-78)

```python
model_url = "https://...pose_landmarker_heavy..."
```

**Model Options:**

| Model | Download Size | RAM Usage | Accuracy                          |
| ----- | ------------- | --------- | --------------------------------- |
| Heavy | ~30MB         | ~150MB    | Highest                           |
| Full  | ~15MB         | ~100MB    | High                              |
| Lite  | ~6MB          | ~50MB     | Good (recommended for production) |

**Fix:** Make model variant configurable via `MEDIAPIPE_MODEL_VARIANT` setting.

---

### 🔶 Medium Issue: Frame Skip Not Applied Consistently

- `video_service.extract_frames()` → respects `FRAME_SKIP_RATIO` ✅
- `BallDetectionService._extract_frames()` → calculates own interval ⚠️
- `PoseDetectionService._extract_frames()` → **doesn't skip at all** ❌

Even if `FRAME_SKIP_RATIO=4`, pose detection still processes every frame.

**Fix:** Ensure all services use the same frame skip configuration.

---

### 🔶 Medium Issue: No max_frames Safety Limit

**Location:** `rq_tasks.py` (lines 95-100)

```python
pose_results = pose_service.analyze_video_file(
    video_path=Path(local_path),
    max_frames=None,  # ← No limit!
)
```

A 5-minute, 60fps video = 18,000 frames. With no limit, this can explode memory usage.

**Fix:** Add `MAX_FRAMES_TO_PROCESS` config option and apply it in production.

---

## Recommended Configuration Changes

### New Settings for config.py

```python
# Production memory optimization settings
MAX_FRAMES_TO_PROCESS: int = 500  # Hard cap on frames to process
YOLO_PRODUCTION_MODEL: str = "nano"  # Only load this model in production
YOLO_LOAD_ALL_MODELS: bool = False  # Set True only for local dev
MEDIAPIPE_MODEL_VARIANT: str = "lite"  # "lite", "full", or "heavy"
PRODUCTION_FRAME_SKIP_RATIO: int = 4  # Higher skip ratio for production
```

### Configuration Comparison

| Setting                   | Current     | Recommended (Production) | Impact                  |
| ------------------------- | ----------- | ------------------------ | ----------------------- |
| `FRAME_SKIP_RATIO`        | 1           | 4-6                      | 4-6x fewer frames       |
| `MAX_FRAMES_TO_PROCESS`   | None        | 300-500                  | Hard safety cap         |
| `YOLO_PRODUCTION_MODEL`   | both loaded | "nano" only              | Save ~100-200MB         |
| `MEDIAPIPE_MODEL_VARIANT` | "heavy"     | "lite"                   | Save ~100MB             |
| `MAX_VIDEO_DURATION`      | 300s        | 120s                     | Fewer frames to process |
| `MAX_VIDEO_RESOLUTION`    | 4K          | 720p                     | 9x smaller per frame    |

### Expected Memory Savings

| Optimization                     | Memory Saved            |
| -------------------------------- | ----------------------- |
| Frame streaming (vs loading all) | **~10GB+** (critical)   |
| Only load one YOLO model         | ~100-200MB              |
| Use MediaPipe lite               | ~100MB                  |
| Lower resolution limit           | 4-9x smaller per frame  |
| Hard frame cap                   | Prevents runaway memory |

---

## Implementation Priority

### Quick Wins (Config Only)

1. Add `MAX_FRAMES_TO_PROCESS` setting
2. Add `YOLO_PRODUCTION_MODEL` setting (only load nano)
3. Add `MEDIAPIPE_MODEL_VARIANT` setting (use lite)
4. Increase `FRAME_SKIP_RATIO` for production
5. Enforce stricter `MAX_VIDEO_DURATION` and `MAX_VIDEO_RESOLUTION`

### Code Changes (Small)

1. Apply frame skip consistently across all services
2. Add safety limit to RQ tasks (`max_frames` parameter)
3. Conditionally load only the needed YOLO model
4. Make MediaPipe model configurable

### Code Changes (Larger Refactor)

1. **Implement frame streaming** — biggest memory win, most code change
   - Refactor `_extract_frames()` to be a generator
   - Update detection services to process frames one at a time
   - This is the long-term solution for memory efficiency

---

## RAM vs CPU Explained

### RAM (Memory)

RAM is your workspace—how much you can work on at once.

- **Current usage:** Loading all frames at once = need huge desk
- **With streaming:** One frame at a time = small desk works fine

### CPU (Processing Speed)

CPU is how fast you process each item.

- **0.5 CPU on Render:** Slow but functional (if RAM is sufficient)
- **Processing time:** Expect 10-30 minutes for long videos on low-end CPU

### The Relationship

```
1. Small RAM → can't fit everything → OOM crash (your current issue)
2. Enough RAM, slow CPU → works, just takes longer (acceptable)
3. Enough RAM, fast CPU → works quickly (ideal)
```

**Priority:** Fix RAM first (streaming), then optimize for speed if needed.

---

## Future Architecture Options: Client-Side Compute

### Overview

**The Idea:** Offload video processing to the user's browser/device instead of your servers. This is increasingly common in modern web apps and can dramatically reduce compute costs while improving user experience.

**Is it possible?** ✅ Yes - Modern browsers support WebAssembly, Web Workers, WebGPU, and ML frameworks like TensorFlow.js and MediaPipe for Web.

**Is it common?** ✅ Yes - Examples: Google Photos (face detection), Figma (design tools), Photopea (image editing), Runway ML (video editing).

---

### Option A: Client-Side Preview (Recommended First Step) ⭐

**Concept:** Quick analysis in browser for instant feedback, full analysis still in cloud.

**Architecture:**

```
User's Browser:
├── Upload video (stays in browser)
├── Quick pose detection (MediaPipe Web) → Instant preview
├── Show results immediately
└── Option: "Run full analysis" → Sends to cloud backend
```

**Implementation:**

- Use **MediaPipe for Web** (official web version, mature)
- Process first 30-60 frames in browser
- Show preview results immediately
- User can then choose "Full Analysis" for cloud processing

**Benefits:**

- ✅ **Zero compute cost** for preview users
- ✅ **Instant feedback** (no waiting for server)
- ✅ **Better UX** (users see if video is good before full analysis)
- ✅ **Reduces server load** (many users won't need full analysis)
- ✅ **Privacy-friendly** (preview data stays local)

**Technical Stack:**

```javascript
// Frontend dependencies
{
  "@mediapipe/pose": "^0.5.0",  // Pose detection in browser
  "ffmpeg.wasm": "^0.11.0"      // Video decoding in browser
}
```

**Complexity:** Low-Medium  
**Time Estimate:** 2-4 weeks  
**Cost Impact:** Reduces server load by ~50-70% (many users satisfied with preview)

---

### Option B: Full Client-Side Processing

**Concept:** Complete analysis pipeline in browser, optional cloud sync for results.

**Architecture:**

```
User's Browser:
├── Upload video
├── Load models (YOLO + MediaPipe) - cached after first load
├── Process all frames in Web Worker
├── Show results immediately
└── Optionally sync metadata to backend (just results, not video)
```

**Implementation:**

- **MediaPipe Web** for pose detection ✅ (already has web version)
- **TensorFlow.js** for YOLO ball detection ⚠️ (needs model conversion)
- **Web Workers** for background processing
- **IndexedDB** for model caching

**Benefits:**

- ✅ **Zero compute costs** for client-side users
- ✅ **Fast processing** (no network latency)
- ✅ **Complete privacy** (data never leaves device)
- ✅ **Scales automatically** (each user uses their own device)
- ✅ **Works offline** (after models load)
- ✅ **No OOM issues** (browser manages memory better)

**Challenges:**

- ⚠️ **Model loading time** (first load: 10-30 seconds, then cached)
- ⚠️ **Device variability** (older devices may be slow)
- ⚠️ **Battery drain** (intensive processing)
- ⚠️ **Model conversion** (YOLO needs conversion to TensorFlow.js)
- ⚠️ **Browser compatibility** (WebGPU not everywhere yet)

**Technical Stack:**

```javascript
// Full client-side stack
{
  "@mediapipe/pose": "^0.5.0",        // ✅ Mature, works well
  "@tensorflow/tfjs": "^4.0.0",       // ⚠️ Need YOLO conversion
  "@tensorflow/tfjs-converter": "^4.0.0",  // For model conversion
  "ffmpeg.wasm": "^0.11.0",          // Video processing
  "idb": "^7.0.0"                     // IndexedDB for caching
}
```

**Complexity:** High  
**Time Estimate:** 2-3 months  
**Cost Impact:** ~80-90% reduction (most users process locally)

---

### Option C: Hybrid Approach (Best of Both Worlds) ⭐⭐⭐

**Concept:** Let users choose processing location, default to client-side with cloud fallback.

**Architecture:**

```
┌─────────────────────────────────────┐
│  User's Device (Browser)            │
│  ✅ Quick preview (always)          │
│  ✅ Full analysis (if capable)      │
│  ✅ Real-time feedback               │
└─────────────────────────────────────┘
              ↓ (fallback)
┌─────────────────────────────────────┐
│  Your Cloud (Backend)                │
│  ✅ Heavy processing                 │
│  ✅ Long videos (>2 minutes)         │
│  ✅ Video annotation                 │
│  ✅ Older device fallback            │
└─────────────────────────────────────┘
```

**User Experience:**

1. User uploads video
2. **Automatic:** Quick preview runs in browser (instant)
3. **User choice:**
   - "Process Locally" → Full analysis in browser (free, fast)
   - "Process in Cloud" → Full analysis on server (reliable, handles long videos)
4. Results sync to backend (just metadata, not video)

**Benefits:**

- ✅ **Best UX** (instant preview + choice)
- ✅ **Cost efficient** (most users choose local)
- ✅ **Reliable** (cloud fallback for edge cases)
- ✅ **Progressive** (works on all devices)
- ✅ **Privacy option** (users can keep everything local)

**Complexity:** Medium-High  
**Time Estimate:** 2-3 months (can start with Option A, add Option B later)  
**Cost Impact:** ~70-85% reduction

---

## Client-Side Compute: Implementation Roadmap

### Phase 1: Client-Side Preview (2-4 weeks)

**Goal:** Add instant preview using MediaPipe Web

**Steps:**

1. Install MediaPipe for Web in frontend
2. Add video upload handler (keep video in browser)
3. Process first 30-60 frames in Web Worker
4. Display preview results immediately
5. Add "Full Analysis" button (sends to cloud)

**Code Example:**

```typescript
// In your React app
import { PoseLandmarker } from "@mediapipe/pose";

async function quickPreviewAnalysis(videoFile: File) {
  // Load model (cached after first load)
  const poseModel = await loadPoseModel();

  // Process in Web Worker
  const worker = new Worker("pose-processor.ts");
  worker.postMessage({ videoFile, model: poseModel });

  worker.onmessage = (result) => {
    // Update UI with preview results
    setPreviewResults(result.data);
  };
}
```

**Impact:**

- Instant feedback for users
- ~50-70% reduction in server requests
- Better user experience

---

### Phase 2: Full Client-Side Option (2-3 months)

**Goal:** Complete analysis pipeline in browser

**Steps:**

1. Convert YOLO models to TensorFlow.js format
2. Implement ball detection in browser
3. Add full pipeline (pose + ball + annotation)
4. Add "Process Locally" vs "Process in Cloud" toggle
5. Implement result syncing (metadata only)

**Challenges:**

- YOLO model conversion (YOLOv8 → TensorFlow.js)
- Video annotation encoding (heavy on mobile)
- Device capability detection (when to suggest cloud)

**Impact:**

- ~80-90% reduction in compute costs
- Complete privacy option
- Works offline

---

### Phase 3: Hybrid Enhancement (1-2 months)

**Goal:** Smart routing based on device/video characteristics

**Steps:**

1. Detect device capabilities (CPU, memory, WebGPU support)
2. Auto-suggest processing location based on:
   - Video length (>2 min → suggest cloud)
   - Device capability (older device → suggest cloud)
   - User preference (remember choice)
3. Seamless fallback (if local fails, auto-retry in cloud)

**Impact:**

- Optimal experience for all users
- Automatic cost optimization
- Best reliability

---

## Client-Side Compute: Technical Feasibility

### What Works Well ✅

| Feature               | Library       | Status    | Performance     |
| --------------------- | ------------- | --------- | --------------- |
| Pose Detection        | MediaPipe Web | ✅ Mature | ~50-100ms/frame |
| Video Decoding        | ffmpeg.wasm   | ✅ Stable | Good            |
| Background Processing | Web Workers   | ✅ Native | Excellent       |
| Model Caching         | IndexedDB     | ✅ Native | Fast            |

### What's Challenging ⚠️

| Feature             | Library       | Status              | Notes                  |
| ------------------- | ------------- | ------------------- | ---------------------- |
| YOLO Ball Detection | TensorFlow.js | ⚠️ Needs conversion | YOLOv8 → TF.js         |
| Video Annotation    | Canvas API    | ⚠️ Heavy            | May throttle on mobile |
| Long Videos (5 min) | All           | ⚠️ Device dependent | Older devices struggle |

### Browser Memory Limits

| Browser | Memory Limit   | Notes             |
| ------- | -------------- | ----------------- |
| Chrome  | ~2GB per tab   | Varies by device  |
| Firefox | ~2GB per tab   | Similar to Chrome |
| Safari  | ~1.5GB per tab | More conservative |

**Key Insight:** Browser memory is better than 512MB server, but still need frame streaming (don't load all frames).

---

## Client-Side Compute: Cost Analysis

### Current Costs (Cloud Only)

- Render API: $0/month (free tier)
- Fly.io Worker: ~$0-5/month
- Supabase Storage: ~$0-5/month (depends on usage)
- **Total: ~$0-10/month**

### With Client-Side Preview (Option A)

- Render API: $0/month
- Fly.io Worker: ~$0-2/month (50-70% reduction)
- Supabase Storage: ~$0-5/month
- **Total: ~$0-7/month** (30-50% reduction)

### With Full Client-Side (Option B)

- Render API: $0/month
- Fly.io Worker: ~$0-1/month (80-90% reduction)
- Supabase Storage: ~$0-3/month (only metadata)
- **Total: ~$0-4/month** (60-80% reduction)

### With Hybrid (Option C)

- Render API: $0/month
- Fly.io Worker: ~$0-2/month (70-85% reduction)
- Supabase Storage: ~$0-4/month
- **Total: ~$0-6/month** (40-60% reduction)

**Note:** Cost savings increase with user growth. At 100 users, savings could be $50-100/month.

---

## Client-Side Compute: Recommendation

### Immediate (Next 2 Weeks)

1. ✅ Fix current server issues (frame streaming + Fly.io)
2. ✅ Get stable baseline

### Short-Term (1-2 Months)

1. ✅ **Implement Option A: Client-Side Preview**
   - Add MediaPipe Web for instant pose detection
   - Quick preview in browser
   - "Full Analysis" still goes to cloud
   - **Impact:** Better UX + 50-70% cost reduction

### Medium-Term (3-6 Months)

2. ✅ **Add Option B: Full Client-Side Processing**
   - Convert YOLO to TensorFlow.js
   - Complete pipeline in browser
   - User choice: local vs cloud
   - **Impact:** 80-90% cost reduction

### Long-Term (6+ Months)

3. ✅ **Enhance with Option C: Hybrid Intelligence**
   - Smart routing based on device/video
   - Automatic fallback
   - **Impact:** Optimal experience + maximum savings

---

## Why Client-Side Compute Makes Sense

1. **Solves cost problem** - Zero compute for client-side users
2. **Better UX** - Instant feedback, no waiting
3. **Privacy-friendly** - Data stays local (important for sports videos)
4. **Scalable** - Each user brings their own compute
5. **Progressive** - Can start with preview, add full processing later
6. **Modern pattern** - Aligns with current web app trends

**Bottom Line:** This is a viable, increasingly common approach that can dramatically reduce costs while improving user experience. Start with preview (Option A), then add full processing (Option B) as time allows.

---

## Deployment Checklist (Updated)

### Phase 1: Quick Fixes (Before Migration)

- [ ] Fix ball detection logger bug (`self.logger` → `logger`)
- [ ] Consolidate to `PROFILE` only (remove `ENVIRONMENT` dependency)
- [ ] Add `PROFILE=production` to Render API env vars (if not already set)
- [ ] Add `MAX_FRAMES_TO_PROCESS=500` env var
- [ ] Set `FRAME_SKIP_RATIO=4` for production
- [ ] Set stricter video duration/resolution limits
- [ ] Test with short video (10-15 seconds)

### Phase 2: Code Optimizations

- [ ] Replace `ENVIRONMENT` checks with `PROFILE` in 3 locations:
  - [ ] `main.py:111` - Worker startup
  - [ ] `redis_config.py:82` - Worker count
  - [ ] `redis_config.py:107` - Worker info
- [ ] Remove `ENVIRONMENT` from `config.py` (or mark deprecated)
- [ ] Only load the YOLO model that will be used
- [ ] Make MediaPipe model variant configurable
- [ ] Apply frame skip consistently across all services
- [ ] Add max_frames parameter to RQ tasks

### Phase 3: Fly.io Worker Setup

- [ ] Create Fly.io account
- [ ] Install Fly CLI
- [ ] Create `fly.toml` configuration
- [ ] Set environment variables
- [ ] Deploy worker service
- [ ] Test worker connectivity to Redis
- [ ] Monitor worker logs

### Phase 4: Long-term Optimization

- [ ] Implement frame streaming (generator pattern)
- [ ] Add worker health monitoring
- [ ] Set up alerts for failed jobs
- [ ] Document deployment process

### Phase 5: Client-Side Compute (Future Enhancement)

- [ ] Research MediaPipe Web integration
- [ ] Implement client-side preview (Option A)
- [ ] Add "Process Locally" vs "Process in Cloud" toggle
- [ ] Convert YOLO models to TensorFlow.js (if pursuing full client-side)
- [ ] Add device capability detection
- [ ] Implement hybrid routing logic

---

## Notes

- Video analysis is memory-intensive (YOLO + MediaPipe + frame buffers)
- 512MB RAM is insufficient for reliable video processing
- Worker can run separately from API (both connect to same Redis)
- Current job timeouts (3-6 min) may be too aggressive for low-end CPU
- **Frame streaming is the biggest optimization opportunity** — reduces memory from GB to MB

---

## Teaching Summary

### Why This Happened

The code was written for local development with 8GB+ RAM. Patterns like "load all data, then process" work fine locally but fail on constrained cloud environments.

### The Principle: Stream, Don't Batch

When processing large data:

1. Read one item
2. Process it
3. Store the small result
4. Let the input go out of scope (garbage collected)
5. Repeat

### Production Mindset

- **Local dev** optimizes for developer speed (load everything, inspect easily)
- **Production** optimizes for resource efficiency (use minimum memory/CPU)

The existing `config.py` profile pattern is excellent for switching behavior between local and production.

---

**Document Status:** Updated January 4, 2026 - Includes codebase optimization analysis
