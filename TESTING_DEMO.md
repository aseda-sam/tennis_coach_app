# Manual Testing Guide for Demo Experience

## Prerequisites

1. **Backend running** on `http://localhost:8000`
2. **Frontend running** on `http://localhost:3000`
3. **Database migrated** with demo fields

## Step 1: Run Database Migration

```bash
cd backend
alembic upgrade head
```

This adds the `is_demo` and `original_user_id` fields to the videos table.

## Step 2: Prepare a Demo Video

You need a video that:
- Has been uploaded and analyzed (has pose detection and/or ball contacts)
- Belongs to a user ID in `ALLOWED_DEMO_SOURCE_USERS` (see `backend/app/core/config.py`)

**Option A: Use existing video**
1. Upload a video through the app
2. Run pose analysis
3. Add some ball contacts
4. Note the video ID

**Option B: Add your user ID to allowlist**
1. Edit `backend/app/core/config.py`
2. Add your user ID to `ALLOWED_DEMO_SOURCE_USERS`:
   ```python
   ALLOWED_DEMO_SOURCE_USERS = [
       DEMO_USER_ID,
       "your-user-id-here",  # Add this
   ]
   ```

## Step 3: Promote Video to Demo

```bash
cd backend
python scripts/promote_video_to_demo.py --video-id <VIDEO_ID>
```

Example:
```bash
python scripts/promote_video_to_demo.py --video-id 42
```

Expected output:
```
🎯 Promoting video 42 to demo status...
   Backed up original user_id: <your-user-id>
✅ Video 42 promoted successfully
   Demo user_id: 00000000-0000-0000-0000-000000000001
   Original user_id (backed up): <your-user-id>
```

## Step 4: Test Frontend

### Test First-Visit Detection

1. **Clear localStorage** (to simulate first visit):
   ```javascript
   // In browser console:
   localStorage.removeItem('hasVisitedApp')
   ```

2. **Refresh the page** - You should see the Demo Landing page

3. **Click "Try Interactive Demo"** - Should navigate to Demo Dashboard

4. **Verify demo banner** appears at top: "🎾 Demo Mode - Explore features without saving changes"

5. **Verify demo video loads** - Should show the promoted video

### Test Demo Dashboard

1. **Video player** - Should play the demo video
2. **Ball contacts** - Should display existing contacts from the demo video
3. **Metrics** - Should show metrics calculated from persisted contacts
4. **Back button** - Should return to demo landing
5. **"Upload Your Video" button** - Should navigate to upload page

### Test Demo Protection

1. **Try to modify a contact** - Should be blocked (if we implement this)
2. **Try to delete a contact** - Should be blocked (if we implement this)
3. **Try to start analysis** - Should be hidden/disabled (if we implement this)

### Test Demo Video Access

1. **Log in as different user** - Demo video should still be accessible
2. **Check video list** - Demo video should NOT appear in user's library
3. **Access demo directly** - `GET /v0/videos/demo` should return the demo video

## Step 5: Test Unpromote (Optional)

```bash
python scripts/promote_video_to_demo.py --video-id <VIDEO_ID> --unpromote
```

This should:
- Restore original `user_id`
- Set `is_demo=False`
- Demo endpoint should return 404

## Troubleshooting

### "No demo video available"
- Check that a video was promoted: `SELECT * FROM videos WHERE is_demo = true;`
- Verify the demo endpoint: `curl http://localhost:8000/v0/videos/demo`

### "PRIVACY VIOLATION" error when promoting
- Your user ID is not in `ALLOWED_DEMO_SOURCE_USERS`
- Add it to the config file and restart backend

### Demo landing doesn't show
- Check localStorage: `localStorage.getItem('hasVisitedApp')`
- Clear it: `localStorage.removeItem('hasVisitedApp')`
- Refresh page

### Demo video not loading
- Check backend logs for errors
- Verify video file exists at the path in database
- Check CORS settings if using different origins

## Next Steps (Not Yet Implemented)

- Ephemeral contacts (frontend-only, not persisted)
- Guided tour
- Read-only mode for VideoPlayer
- Demo mode indicators in BallContactModal
