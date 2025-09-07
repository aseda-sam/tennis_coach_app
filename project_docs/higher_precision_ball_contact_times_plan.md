# Frame-Accurate Ball Contact Positioning - Feature Plan

## Problem Analysis

### Issue 1: Precision Loss in User Interface

**Root Cause**: Range slider uses `step="0.1"` which forces rounding to 0.1s increments

- HTML5 video element has high precision (`1.234567` seconds)
- Range slider constrains user to `0.0, 0.1, 0.2, 0.3...` positions
- When user drags slider, `handleSeek` sets `video.currentTime = roundedValue`
- Result: Database stores `1.200000` instead of `1.234567`

**Impact**:

- At 30fps: 0.1s = 3 frames (imprecise)
- At 60fps: 0.1s = 6 frames (very imprecise)
- User can't mark exact frame they're viewing

### Issue 2: Frame vs Timestamp Storage Architecture

**Current State**:

- Store `video_timestamp` as primary, `frame_number` always null
- Backend services convert timestamps to frames: `int(timestamp * fps)`
- No canonical frame representation

**Question**: Should we store frames as primary and derive timestamps, or vice versa?

## Current State Analysis

### Database Layer

- ✅ `video_timestamp` stored as `Float` in `ball_contacts` table
- ✅ `frame_number` column exists but unused (always null)
- ✅ Backend schemas support both fields
- ✅ No database schema changes needed

### Frontend Issues

- ❌ Range slider `step="0.1"` forces 0.1s rounding
- ❌ Display formatting rounds to 1 decimal place
- ❌ No frame number display or input

## Solution Overview

**Two-Part Solution:**

### Part 1: Fix Precision Loss

- Change range slider `step` from `"0.1"` to frame-based increments (`1/fps`)
- This preserves exact timestamp precision from HTML5 video element

### Part 2: Choose Storage Architecture

- **Recommendation**: Keep timestamps as primary storage (simpler implementation)
- Compute and store `frame_number` for services that need it
- Display both timestamp and frame number in UI

## Implementation Plan

### Phase 1: Fix Range Slider Precision

**Files to modify:**

- `frontend/src/components/VideoPlayer.tsx`

**Changes:**

1. Calculate frame-based step: `const frameStep = 1 / videoFps`
2. Update range slider: `step={frameStep}`
3. Ensure slider can position at exact frame boundaries

### Phase 2: Backend Frame Computation

**Files to modify:**

- `backend/app/services/ball_contact_service.py`
- `backend/app/services/posture_analysis.py`

**Changes:**

1. On create/update: compute `frame_number = round(timestamp * fps)`
2. Prefer `frame_number` in services when available
3. Fall back to `round(timestamp * fps)` when frame_number is null

### Phase 3: UI Display Enhancement

**Files to modify:**

- `frontend/src/components/BallContactMarker.tsx`
- `frontend/src/components/BallContactModal.tsx`

**Changes:**

1. Display both timestamp (3 decimal places) and frame number
2. Show format: "1.234s (Frame 37)"
3. Update input fields to support higher precision

### Phase 4: Backfill Existing Data

**Files to create:**

- `scripts/backfill_ball_contact_frames.py`

**Changes:**

1. One-time script to populate `frame_number` for existing contacts
2. Use `round(timestamp * fps)` calculation

## Technical Details

### Precision Requirements

- **Range slider**: Frame-based steps (e.g., 0.033s for 30fps, 0.017s for 60fps)
- **Display**: 3 decimal places for timestamps + frame numbers
- **Storage**: Keep timestamps as primary, add computed frame_number

### UI/UX Considerations

- Slider moves in frame increments (smooth for user)
- Display shows both time and frame for clarity
- Input fields accept high precision but snap to frames on save

### Database Impact

- No schema changes required
- Add computed `frame_number` for existing and new records
- Backward compatibility maintained

## Success Criteria

1. ✅ Range slider positions at exact frame boundaries
2. ✅ Database stores precise timestamps (not rounded to 0.1s)
3. ✅ UI displays both timestamp and frame number
4. ✅ Backend services use frame numbers when available
5. ✅ Works correctly with 30fps, 60fps, and 29.97fps videos
6. ✅ Existing data backfilled with frame numbers

## Files to Modify

### Frontend

- `frontend/src/components/VideoPlayer.tsx` - Fix range slider step
- `frontend/src/components/BallContactMarker.tsx` - Display time + frame
- `frontend/src/components/BallContactModal.tsx` - High precision input

### Backend

- `backend/app/services/ball_contact_service.py` - Compute frame_number
- `backend/app/services/posture_analysis.py` - Use frame_number
- `scripts/backfill_ball_contact_frames.py` - Backfill existing data

## Implementation Notes

- **Keep changes minimal and focused**
- **Maintain existing API contracts**
- **Ensure no breaking changes**
- **Frame-first approach for services, timestamp-first for storage**
