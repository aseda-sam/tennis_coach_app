---
name: Deprecate Legacy Background Service
overview: Remove deprecated BackgroundTaskService (ThreadPoolExecutor) and migrate remaining legacy routes to RQ. Clean up all references and remove old code.
todos:
  - id: migrate-pose-detection-route
    content: Migrate pose_detection.py route to use RQ instead of BackgroundTaskService
    status: pending
  - id: migrate-ball-detection-route
    content: Migrate ball_detection.py route to use RQ instead of BackgroundTaskService
    status: pending
  - id: update-scripts
    content: Update regenerate_annotated_videos.py script to use RQ if still needed
    status: pending
  - id: remove-background-service
    content: Remove BackgroundTaskService class and background_service.py file
    status: pending
  - id: remove-progress-utils
    content: Remove or update progress_utils.py if only used by BackgroundTaskService
    status: pending
  - id: update-tests
    content: Remove or update test_background_service.py and test_background_service_integration.py
    status: pending
  - id: update-docs
    content: Update documentation to remove BackgroundTaskService references
    status: pending
  - id: cleanup-imports
    content: Remove ThreadPoolExecutor imports and related code
    status: pending
isProject: false
---

# Deprecate Legacy Background Service Plan

## Overview

Remove the deprecated `BackgroundTaskService` (ThreadPoolExecutor-based) and complete the migration to RQ. All analysis tasks should use RQ, and the old service should be fully removed.

## Current Status

**RQ Migration Status:** ✅ Complete for unified analysis endpoint (`/v0/analysis/videos/{video_id}`)

**Remaining Legacy Code:**

- `backend/app/api/routes/pose_detection.py` - Still uses `BackgroundTaskService`
- `backend/app/api/routes/ball_detection.py` - Still uses `BackgroundTaskService`
- `backend/app/services/background_service.py` - Deprecated service class
- `backend/app/utils/progress_utils.py` - May only be used by BackgroundTaskService
- `backend/scripts/regenerate_annotated_videos.py` - Uses BackgroundTaskService
- `backend/tests/test_background_service.py` - Tests for deprecated service
- `backend/tests/test_background_service_integration.py` - Integration tests

## Implementation Steps

### Phase 1: Migrate Legacy Routes to RQ

#### 1.1 Migrate Pose Detection Route

**File:** `backend/app/api/routes/pose_detection.py`

**Current Implementation:**

- Uses `background_service.start_analysis_task()` with `analysis_type="pose_only"`
- Returns `task_id` (integer)

**New Implementation:**

- Use RQ: `analysis_queue.enqueue(analyze_pose_detection_rq, ...)`
- Return `job_id` (string UUID)
- Update response schema to use `job_id` instead of `task_id`
- Use same RQ retry/timeout config as unified endpoint

**Changes:**

```python
# Remove
from app.services.background_service import background_service
task_id = background_service.start_analysis_task(...)

# Add
from app.core.redis_config import analysis_queue
from app.services.rq_tasks import analyze_pose_detection_rq
from rq import Retry

job = analysis_queue.enqueue(
    analyze_pose_detection_rq,
    video_id=video_id,
    video_path=video_path,
    confidence_threshold=request.confidence_threshold,
    retry=Retry(max=2, interval=60),
    job_timeout=3600,
)
```

**Response Schema Update:**

- Update `PoseDetectionStartResponse` to include `job_id: str` instead of/in addition to `task_id`
- Keep backward compatibility if needed (deprecate `task_id` field)

#### 1.2 Migrate Ball Detection Route

**File:** `backend/app/api/routes/ball_detection.py`

**Same approach as pose detection:**

- Replace `background_service.start_analysis_task()` with RQ
- Use `analyze_ball_detection_rq` task
- Update response to use `job_id`

### Phase 2: Update Scripts

#### 2.1 Update regenerate_annotated_videos.py

**File:** `backend/scripts/regenerate_annotated_videos.py`

**Options:**

1. **Migrate to RQ:** Update script to enqueue RQ jobs instead of using BackgroundTaskService
2. **Remove script:** If annotated videos are deprecated (per remove_encoding plan), remove this script entirely
3. **Keep as-is temporarily:** If script is rarely used, mark as deprecated and remove later

**Recommendation:** Check if script is still needed. If annotated videos are deprecated, remove the script.

### Phase 3: Remove BackgroundTaskService

#### 3.1 Remove Service Class

**File:** `backend/app/services/background_service.py`

**Actions:**

- Delete entire file
- Remove all methods: `start_analysis_task()`, `_run_pose_only_analysis()`, `_run_ball_only_analysis()`, etc.
- Remove `_active_tasks` global dictionary
- Remove ThreadPoolExecutor usage

#### 3.2 Check progress_utils.py

**File:** `backend/app/utils/progress_utils.py`

**Check if still needed:**

- Search codebase for `progress_utils` imports
- If only used by BackgroundTaskService, remove it
- If used elsewhere, keep but remove BackgroundTaskService-specific code

### Phase 4: Update Tests

#### 4.1 Remove/Update test_background_service.py

**File:** `backend/tests/test_background_service.py`

**Options:**

1. **Delete:** If all functionality is tested via RQ tests
2. **Keep as legacy tests:** Mark as deprecated, keep for reference
3. **Migrate to RQ tests:** Convert relevant tests to test RQ tasks

**Recommendation:** Delete the file since RQ tests cover the same functionality.

#### 4.2 Update test_background_service_integration.py

**File:** `backend/tests/test_background_service_integration.py`

**Current:** Tests deprecated BackgroundTaskService

**Action:**

- Delete file (RQ integration tests already exist in `test_rq_tasks.py`)
- Or mark as deprecated and remove later

### Phase 5: Update Documentation

#### 5.1 Update background-tasks.md

**File:** `backend/docs/background-tasks.md`

**Actions:**

- Add deprecation notice at top
- Mark ThreadPoolExecutor approach as deprecated
- Point to `background-tasks-rq.md` as current approach
- Keep for historical reference or remove entirely

#### 5.2 Update background-tasks-rq.md

**File:** `backend/docs/background-tasks-rq.md`

**Actions:**

- Remove references to "legacy system" or "migration"
- Update to reflect RQ as the only system
- Remove migration context sections

#### 5.3 Update API Documentation

**Files:** Any API docs that reference BackgroundTaskService

**Actions:**

- Remove references to deprecated service
- Update examples to show RQ usage

### Phase 6: Cleanup Imports and Code

#### 6.1 Remove ThreadPoolExecutor Imports

**Search for:**

- `from concurrent.futures import ThreadPoolExecutor`
- `ThreadPoolExecutor` usage
- Remove all references

#### 6.2 Remove Global Task Storage

**Remove:**

- `_active_tasks` dictionary
- `_task_counter` variable
- `_task_lock` threading lock
- Any task storage utilities only used by BackgroundTaskService

#### 6.3 Remove Rollback Mechanism

**If exists:**

- Remove `USE_RQ_FOR_ANALYSIS` environment variable
- Remove any conditional logic for RQ vs ThreadPoolExecutor

## Implementation Order

1. **Migrate legacy routes** (pose_detection, ball_detection) - High priority
2. **Update scripts** - Medium priority
3. **Remove BackgroundTaskService** - After routes migrated
4. **Update tests** - After service removed
5. **Update documentation** - After code removed
6. **Final cleanup** - Remove imports, globals, etc.

## Verification Checklist

After completion:

- [ ] All analysis endpoints use RQ (unified + legacy routes)
- [ ] No imports of `BackgroundTaskService` in codebase
- [ ] No `ThreadPoolExecutor` usage for analysis tasks
- [ ] All tests pass (RQ tests, no BackgroundTaskService tests)
- [ ] Documentation updated
- [ ] Scripts updated or removed
- [ ] No references to `background_service` in active code

## Files to Modify/Delete

### Delete:

- `backend/app/services/background_service.py`
- `backend/tests/test_background_service.py`
- `backend/tests/test_background_service_integration.py` (or mark deprecated)

### Modify:

- `backend/app/api/routes/pose_detection.py` - Migrate to RQ
- `backend/app/api/routes/ball_detection.py` - Migrate to RQ
- `backend/scripts/regenerate_annotated_videos.py` - Update or remove
- `backend/app/utils/progress_utils.py` - Check and clean if needed
- `backend/docs/background-tasks.md` - Add deprecation notice
- `backend/docs/background-tasks-rq.md` - Remove migration context

### Check:

- Any other files importing `BackgroundTaskService`
- Any other scripts using background_service

## Notes

- **Backward Compatibility:** Consider if legacy routes need to maintain backward compatibility with `task_id` responses. If so, add deprecation warnings.
- **Testing:** Ensure all RQ tests pass before removing BackgroundTaskService
- **Documentation:** Keep historical docs if useful, but clearly mark as deprecated
- **Scripts:** Verify `regenerate_annotated_videos.py` is still needed before updating

## Success Criteria

- ✅ All analysis tasks use RQ exclusively
- ✅ BackgroundTaskService completely removed
- ✅ No ThreadPoolExecutor usage for analysis
- ✅ All tests pass
- ✅ Documentation updated
- ✅ Codebase cleaner and simpler
