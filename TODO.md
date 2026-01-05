# Infrastructure Fixes - Action Plan

**Goal:** Fix OOM errors and get video processing working in production  
**Budget:** $0-5/month  
**Timeline:** Week 1 (critical fixes), Week 2 (optimizations)

---

## PR 1: Critical Bug Fixes ✅ COMPLETED

**Branch:** `infrastructure/optimization-analysis`  
**Status:** Merged

### Tasks:

- ✅ Fix Ball Detection Logger Bug (all 8 instances)
- ✅ Set Production Video Limits (profile-aware)

---

## PR 2: Fly.io Worker Deployment

**Branch:** `infrastructure/flyio-worker`  
**Status:** 🟡 In Progress

### Tasks:

- ✅ Create `fly.toml` configuration
- ✅ Create `Dockerfile.worker` for worker service
- ✅ Create deployment documentation
- ✅ Create quick start guide
- ⬜ Create Fly.io account (user action required)
- ⬜ Set environment variables (user action required)
- ⬜ Deploy worker service (user action required)
- ⬜ Test worker connectivity (user action required)

**Files Created:**

- `fly.toml` - Fly.io configuration
- `Dockerfile.worker` - Worker-specific Dockerfile
- `backend/docs/flyio-deployment.md` - Complete deployment guide (includes Quick Start section)

**Time:** 2-3 hours (code complete, deployment pending)

---

## PR 3: Code Cleanup

**Branch:** `refactor/consolidate-env-vars` (to be created)  
**Status:** ⬜ Not started

### Tasks:

- Consolidate ENVIRONMENT → PROFILE
- Replace `ENVIRONMENT` checks with `PROFILE` in:
  - `backend/app/main.py`
  - `backend/app/core/redis_config.py`
- Remove or deprecate `ENVIRONMENT` from config

**Time:** 1 hour

---

## PR 4: Performance Optimizations

**Branch:** `feat/performance-optimizations` (to be created)  
**Status:** ⬜ Not started

### Tasks:

- Optimize Model Loading (only load YOLO nano in production)
- Fix Frontend N+1 Query (include analysis status in video list)

**Files:**

- `backend/app/services/ball_detection/detection_service.py`
- Backend video list endpoint
- Frontend `VideoList.tsx`

**Time:** 5-6 hours total

---

## 🟢 Future Enhancements (Later)

- Frame streaming refactor (major memory optimization)
- React Query for frontend caching
- Client-side compute preview
- MediaPipe model variant configuration

---

## How to Use This

1. Work through PRs in order (PR 1 → PR 2 → PR 3 → PR 4)
2. Create new branch for each PR
3. Test after each PR before merging
4. Mark PRs as ✅ when merged

---

**Last Updated:** 2026-01-05
