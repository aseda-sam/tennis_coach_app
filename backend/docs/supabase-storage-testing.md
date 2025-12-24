# Testing Supabase Storage Locally

## Quick Setup Guide

### Step 1: Install Supabase Python Client

```bash
cd backend
pip install supabase
```

### Step 2: Get Your Supabase Credentials

1. Go to your Supabase project dashboard
2. **Settings → API**:
   - Copy **Project URL** (e.g., `https://xxxxx.supabase.co`)
   - Copy **Service Role Key** (keep this secret!)
3. **Storage → Buckets**:
   - Note your bucket name (e.g., `tennis-videos`)

### Step 3: Create Local `.env` File

Create or update `backend/.env`:

```bash
# Storage Configuration
STORAGE_TYPE=supabase

# Supabase Storage
SUPABASE_URL=https://xxxxx.supabase.co/
SUPABASE_KEY=eyJhbGc...  # Your Service Role Key
SUPABASE_STORAGE_BUCKET=tennis-videos

# Database (keep your existing setup)
DATABASE_URL=sqlite:///../data/database/tennis_coach.db
# OR if testing with Supabase DB:
# SUPABASE_DB_URL=postgresql://postgres:[PASSWORD]@[HOST]:5432/postgres
```

### Step 4: Restart Your Backend

```bash
cd backend
python -m uvicorn app.main:app --reload
```

The storage service will automatically:
- Detect `STORAGE_TYPE=supabase`
- Initialize Supabase client
- Use Supabase Storage for all file operations

### Step 5: Test Upload

1. Start your backend
2. Upload a video via your frontend or API
3. Check Supabase dashboard → Storage → `tennis-videos` bucket
4. You should see the uploaded file!

### Step 6: Verify Database Connection

Check that the database record was created:
- Query your database (SQLite or Supabase)
- The `file_path` column should contain just the filename (e.g., `video_123.mp4`)
- Not the full path like local storage

## Switching Back to Local Storage

To switch back to local storage:

```bash
# In backend/.env
STORAGE_TYPE=local
# (Remove or comment out Supabase variables)
```

Then restart your backend.

## Troubleshooting

### Error: "Supabase client not initialized"
- Check that `SUPABASE_URL` and `SUPABASE_KEY` are set correctly
- Verify the Service Role Key (not the anon key)
- Ensure `SUPABASE_URL` has a trailing slash (e.g., `https://xxxxx.supabase.co/`)

### Error: "SUPABASE_STORAGE_BUCKET must be set"
- Make sure `SUPABASE_STORAGE_BUCKET` matches your bucket name exactly
- Check bucket exists in Supabase dashboard

### Error: "supabase package is required"
- Run: `pip install supabase`
- Or: `pip install -e .` (installs all dependencies)

### Files not appearing in Supabase
- Check bucket permissions (should be Public for now, or Private with proper RLS)
- Verify Service Role Key has storage access
- Check backend logs for errors

## Bucket Permissions

### For Testing (Public Bucket)
- Go to Storage → Buckets → `tennis-videos`
- Set to **Public**
- Files will be accessible via public URLs

### For Production (Private Bucket - Recommended)
- Set bucket to **Private**
- Update code to use signed URLs (future enhancement)
- Add authentication before generating URLs

## What Gets Stored Where

### Local Storage (`STORAGE_TYPE=local`)
- **File**: Saved to `../data/videos/raw/video.mp4`
- **Database**: `file_path = "../data/videos/raw/video.mp4"` (full path)

### Supabase Storage (`STORAGE_TYPE=supabase`)
- **File**: Uploaded to Supabase bucket `tennis-videos/video.mp4`
- **Database**: `file_path = "video.mp4"` (just filename)

The storage service handles the difference automatically!

