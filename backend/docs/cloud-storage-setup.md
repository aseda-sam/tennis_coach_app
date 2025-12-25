# Cloud Storage Setup

## Overview

This guide explains how to configure cloud object storage for video files. The app supports both local filesystem storage (development) and cloud storage (production).

## Supported Storage Types

- **local** - Local filesystem (default, for development)
- **supabase** - Supabase Storage
- **s3** - AWS S3 (future)
- **cloudinary** - Cloudinary (future)

## Quick Setup Guide

### Step 1: Choose Your Storage Provider

Set `STORAGE_TYPE` in your `.env` file:

```bash
# For local development
STORAGE_TYPE=local

# For cloud storage (e.g., Supabase, S3)
STORAGE_TYPE=supabase  # or s3, cloudinary
```

### Step 2: Configure Storage Credentials

Add the required environment variables for your chosen storage type:

#### For Supabase Storage:

```bash
STORAGE_TYPE=supabase
SUPABASE_URL=https://your-project.supabase.co/
SUPABASE_KEY=your-service-role-key
SUPABASE_STORAGE_BUCKET=your-bucket-name
```

#### For AWS S3 (future):

```bash
STORAGE_TYPE=s3
AWS_ACCESS_KEY_ID=your-access-key
AWS_SECRET_ACCESS_KEY=your-secret-key
AWS_S3_BUCKET=your-bucket-name
AWS_REGION=us-east-1
```

### Step 3: Restart Your Backend

```bash
cd backend
python -m uvicorn app.main:app --reload
```

The storage service will automatically:

- Detect `STORAGE_TYPE` from configuration
- Initialize the appropriate storage client
- Use cloud storage for all file operations

### Step 4: Test Upload

1. Start your backend
2. Upload a video via your frontend or API
3. Check your storage provider's dashboard
4. You should see the uploaded file!

### Step 5: Verify Database Records

Check that the database record was created:

- Query your database
- The `file_path` column will contain:
  - **Local storage**: Full path (e.g., `../data/videos/raw/video.mp4`)
  - **Cloud storage**: Just filename (e.g., `video.mp4`)

## Storage Behavior

### Local Storage (`STORAGE_TYPE=local`)

- **File**: Saved to `../data/videos/raw/video.mp4`
- **Database**: `file_path = "../data/videos/raw/video.mp4"` (full path)
- **No additional configuration needed**

### Cloud Storage (`STORAGE_TYPE=supabase`, `s3`, etc.)

- **File**: Uploaded to cloud storage bucket
- **Database**: `file_path = "video.mp4"` (just filename)
- **Requires**: Storage provider credentials and bucket configuration

The storage service handles the difference automatically!

## Switching Storage Types

To switch between storage types:

```bash
# In backend/.env
STORAGE_TYPE=local      # Use local filesystem
STORAGE_TYPE=supabase   # Use cloud storage
```

Then restart your backend. No code changes needed!

## Troubleshooting

### Error: "Storage client not initialized"

- Check that required environment variables are set correctly
- Verify credentials are valid
- Ensure bucket/container exists

### Error: "Storage bucket must be set"

- Make sure bucket name matches your storage provider exactly
- Check bucket exists in your storage provider's dashboard

### Files not appearing in cloud storage

- Check bucket permissions (public/private settings)
- Verify credentials have storage access
- Check backend logs for errors

### Error: "package is required"

- Install the required package for your storage type:
  - Supabase: `pip install supabase`
  - S3: `pip install boto3`
- Or install all dependencies: `pip install -e .`

## Production Considerations

### Public vs Private Buckets

**Public Buckets:**

- Files accessible via direct URLs
- Simpler setup
- Less secure (anyone with URL can access)

**Private Buckets (Recommended):**

- Files require authentication
- More secure
- May require signed URLs for access

### Performance

- Cloud storage uses CDN for fast global delivery
- Offloads bandwidth from your server
- Better scalability than local storage

## Summary

1. ✅ Set `STORAGE_TYPE` in `.env`
2. ✅ Add storage provider credentials
3. ✅ Restart backend
4. ✅ Test upload
5. ✅ Verify files in storage provider dashboard

**The storage service automatically handles differences between local and cloud storage!**
