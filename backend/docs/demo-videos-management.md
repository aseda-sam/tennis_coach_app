# Demo Videos Guide

Complete guide for managing demo videos: setup, uploading, and rotating active demos.

## Table of Contents

1. [Quick Start](#quick-start)
2. [Common Workflows](#common-workflows)
3. [Setup](#setup)
4. [Uploading Demo Videos](#uploading-demo-videos)
5. [Managing Active Demo](#managing-active-demo)
6. [Testing](#testing)
7. [Troubleshooting](#troubleshooting)
8. [Reference](#reference)

---

## Common Workflows

### Adding a New Demo Video

1. **Upload via app** (recommended):
   - Open the app and click "Upload Video"
   - Check **"Upload as demo video"** checkbox
   - Upload completes automatically with correct metadata

2. **Set as active**:
   ```bash
   python backend/scripts/set_active_demo.py --video-id <new_video_id>
   ```

### Rotating to a Different Active Demo

1. **List all demo videos**:
   ```bash
   python backend/scripts/set_active_demo.py --list
   ```

2. **Set different video as active**:
   ```bash
   python backend/scripts/set_active_demo.py --video-id <different_video_id>
   ```

   This automatically:
   - Unsets the previous active demo
   - Sets the new video as active
   - Verifies file exists in demo bucket (copies if missing)

---

## Quick Start

**For local development:**
```bash
cd backend
python -m alembic upgrade head  # Run migrations
# Upload video via app with "Upload as demo video" checked
python scripts/set_active_demo.py --video-id <id>  # Set as active
```

**For production:**
1. Create public `demo-videos` bucket in Supabase
2. Set `SUPABASE_DEMO_BUCKET=demo-videos` environment variable
3. Run migrations: `python -m alembic upgrade head`
4. Upload demo video via app (checkbox) or manually
5. Set active: `python scripts/set_active_demo.py --video-id <id>`

---

## Setup

### Step 1: Run Migrations

The demo feature requires these migrations:
- `4212cb7567aa` - Adds `is_demo` and `original_user_id` columns
- `d1f0ec4cf292` - Adds `is_active_demo` column

**Check current status:**
```bash
cd backend
python -m alembic current
```

**Run migrations:**
```bash
python -m alembic upgrade head
```

**Verify:**
```bash
python -m alembic current  # Should show d1f0ec4cf292
```

**If migrations fail** (e.g., RLS issues in Supabase), see [Manual SQL Application](#manual-sql-application) below.

### Step 2: Configure Demo Bucket (Production Only)

**In Supabase Dashboard:**
1. Go to Storage → Create bucket
2. Name: `demo-videos` (or your preferred name)
3. **Important**: Set bucket to **Public** (not private)
4. Click "Create bucket"

**Set environment variable:**
```bash
# Fly.io
fly secrets set SUPABASE_DEMO_BUCKET=demo-videos

# Heroku
heroku config:set SUPABASE_DEMO_BUCKET=demo-videos

# Or add to your .env/production config
SUPABASE_DEMO_BUCKET=demo-videos
```

**Note**: Local development doesn't require a demo bucket (uses local storage).

---

## Uploading Demo Videos

### ✅ Recommended: Upload via App

The app supports uploading demo videos directly with accurate metadata:

1. **In the app**: When uploading a video, check the **"Upload as demo video"** checkbox
   - **Local dev**: Checkbox is always visible
   - **Production**: Only visible to authorized users (your user ID: `ca4a6fcc-4cdf-435c-a22f-1c8c02ce4c5f`)

2. The video will automatically:
   - Upload to `demo/` folder in public demo bucket (or local `demo/` directory)
   - Set `is_demo = True` in database
   - Compute all metadata (duration, fps, width, height, etc.) correctly

3. **Set as active demo**:
   ```bash
   python backend/scripts/set_active_demo.py --video-id <video_id>
   ```

### Alternative: Manual SQL Methods

If you need to create demo records manually (not recommended), you need:
- `is_demo = True`
- `file_path` starting with `demo/` (e.g., `demo/video1.mp4`)
- `user_id` = demo user ID (`00000000-0000-0000-0000-000000000001`)

**Clone metadata from existing video:**
```sql
INSERT INTO videos (
    filename, file_path, file_size, content_type,
    duration, fps, width, height, status, user_id, is_demo
)
SELECT
    'demo_serve.mp4' AS filename,
    'demo/demo_serve.mp4' AS file_path,
    file_size, content_type,
    duration, fps, width, height, status,
    '00000000-0000-0000-0000-000000000001' AS user_id,
    true AS is_demo
FROM videos
WHERE id = <source_video_id>;
```

**Note**: The file must exist in storage at `demo/demo_serve.mp4` or the `set_active_demo.py` copy step will fail.

---

## Managing Active Demo

Only one demo video can be active at a time. Use the admin script to manage:

**List all demo videos:**
```bash
python backend/scripts/set_active_demo.py --list
```

**Set a video as active demo:**
```bash
python backend/scripts/set_active_demo.py --video-id <video_id>
```

The script will:
- Verify video is eligible (`is_demo=True`, `file_path` starts with `demo/`)
- Check if file exists in demo bucket (copy from private bucket if missing)
- Set `is_active_demo=True` for selected video
- Unset any previous active demo

**Eligibility requirements:**
- Video must have `is_demo = True`
- Video's `file_path` must start with `demo/`

---

## Testing

### Backend Testing

**Test demo endpoint:**
```bash
curl -H "Authorization: Bearer <token>" \
  http://localhost:8000/v0/videos/demo
```

Should return the active demo video with `is_active_demo: true`.

**Test demo video URL:**
```bash
curl -H "Authorization: Bearer <token>" \
  http://localhost:8000/v0/videos/<demo_id>/url
```

For active demo videos, should return public demo bucket URL (no signed URL).

### Frontend Testing

1. **Demo Landing Page**:
   - Homepage should show demo landing by default
   - "Try Demo" button navigates to Demo Dashboard

2. **Demo Dashboard**:
   - Video player loads and plays demo video
   - Ball contacts display correctly
   - Metrics show calculated values
   - "Upload Your Video" CTA works

3. **Demo Access**:
   - Demo video accessible to all authenticated users
   - Demo video does NOT appear in user's library
   - Demo video uses public bucket URL (no signed URL)

4. **Demo Rotation**:
   ```bash
   python scripts/set_active_demo.py --video-id <other_demo_id>
   ```
   - Previous demo: `is_active_demo = false`
   - New demo: `is_active_demo = true`
   - Frontend shows new demo video

---

## Troubleshooting

### Migration Issues

**Problem**: Migration fails with "column already exists"
- **Solution**: Check if migration was already applied manually
- Verify: `SELECT column_name FROM information_schema.columns WHERE table_name='videos' AND column_name='is_demo';`

**Problem**: Migration fails with RLS/permissions
- **Solution**: Use [Manual SQL Application](#manual-sql-application) below

**Problem**: Migration reports success but columns missing
- **Solution**: Check RLS on `alembic_version` table, use manual SQL script

### Demo Bucket Issues

**Problem**: "SUPABASE_DEMO_BUCKET not set" warning
- **Solution**: Set environment variable in production
- For Fly.io: `fly secrets set SUPABASE_DEMO_BUCKET=demo-videos`

**Problem**: Demo video returns 404
- **Solution**: 
  1. Verify video exists in demo bucket with correct path
  2. Check `file_path` in database matches bucket path
  3. Verify bucket is public (not private)

**Problem**: Demo video uses signed URL instead of public URL
- **Solution**: 
  1. Verify `is_active_demo=True` for the video
  2. Check `SUPABASE_DEMO_BUCKET` is set
  3. Verify `file_path` starts with `demo/`

### Script Issues

**Problem**: Script says "not eligible" for demo video
- **Solution**: Ensure `file_path` starts with `demo/` in database
- Update: `UPDATE videos SET file_path = 'demo/' || filename WHERE id = <id>;`

**Problem**: Script fails to copy to demo bucket
- **Solution**: 
  1. Verify source video exists in private bucket
  2. Check Supabase credentials are correct
  3. Verify demo bucket exists and is accessible

### Frontend Issues

**Problem**: "No demo video available"
- **Solution**: 
  1. Check that a video has `is_active_demo = true`
  2. Query: `SELECT * FROM videos WHERE is_active_demo = true;`
  3. Set active demo: `python scripts/set_active_demo.py --video-id <id>`

**Problem**: Demo video not loading
- **Solution**:
  1. Check backend logs for errors
  2. Verify video file exists at the path in database
  3. For production: Check if demo bucket is configured
  4. Verify demo bucket is public (not private)
  5. Check CORS settings if using different origins

---

## Reference

### Manual SQL Application

If `alembic upgrade head` doesn't work due to RLS or permissions issues:

1. **Open Supabase SQL Editor**:
   - Go to Supabase Dashboard → SQL Editor → New Query

2. **Copy and run the SQL script**:
   ```bash
   cat backend/scripts/apply_demo_migrations_manual.sql
   ```
   Copy contents and paste into Supabase SQL Editor, then run.

3. **Verify**:
   ```sql
   -- Check columns exist
   SELECT column_name FROM information_schema.columns 
   WHERE table_name = 'videos' 
   AND column_name IN ('is_demo', 'is_active_demo', 'original_user_id');
   -- Should return 3 rows
   
   -- Check version
   SELECT version_num FROM alembic_version;
   -- Should return: d1f0ec4cf292
   ```

The script is **idempotent** - safe to run multiple times.

### Verification Queries

**Check migration status:**
```sql
SELECT version_num FROM alembic_version;
```

**List demo videos:**
```sql
SELECT id, filename, file_path, is_demo, is_active_demo 
FROM videos 
WHERE is_demo = true;
```

**Verify only one active demo:**
```sql
SELECT COUNT(*) FROM videos WHERE is_active_demo = true;
-- Should return 1 (or 0 if none set)
```

### Quick Reference Commands

```bash
# Check migration status
python -m alembic current

# Run migrations
python -m alembic upgrade head

# List demo videos
python scripts/set_active_demo.py --list

# Set active demo
python scripts/set_active_demo.py --video-id <id>

# Test demo endpoint
curl -H "Authorization: Bearer <token>" http://localhost:8000/v0/videos/demo
```

### Rollback (If Needed)

If you need to rollback the migration:

```bash
# Rollback one migration
python -m alembic downgrade -1

# Or rollback to specific version
python -m alembic downgrade 4212cb7567aa
```

**Warning**: This will remove the `is_active_demo` column. Make sure to unset active demos first:
```sql
UPDATE videos SET is_active_demo = false;
```

---

## Success Criteria

You're done when:
- ✅ Migrations applied (`d1f0ec4cf292`)
- ✅ Demo bucket created and public (production)
- ✅ `SUPABASE_DEMO_BUCKET` environment variable set (production)
- ✅ Demo video uploaded (via app or manually)
- ✅ Demo video set as active (`is_active_demo = true`)
- ✅ Demo endpoint returns active demo video
- ✅ Demo video URL is public (not signed)
- ✅ Frontend demo experience works
- ✅ Can rotate between demo videos
