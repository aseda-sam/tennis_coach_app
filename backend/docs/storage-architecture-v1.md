# Storage Architecture for V1 - Temporary Document

**Status**: Temporary document for planning. Will be consolidated later.

## Current Architecture Decision

### Approach: Pre-process and Store

**What we're doing:**

1. Upload raw video → Store it
2. Process video → Generate annotated video → Store it
3. Serve pre-processed videos when users request them

**Decision**: Keep this approach for V1.

### Why This Works for V1

✅ **Pre-processing = Fast Serving**

- No on-the-fly processing when users request videos
- Videos are ready to stream immediately
- Better user experience

✅ **Supabase CDN Handles Delivery**

- Your server just redirects to Supabase public URL
- Supabase CDN streams directly to users
- Your server bandwidth is minimal (only handles redirect)

✅ **Simple Implementation**

- Straightforward code path
- Easy to maintain and debug
- No complex caching logic needed

✅ **Reasonable Storage Cost**

- Raw + processed = ~2x storage
- But videos aren't huge files
- Acceptable for V1 scale

### Current Issues (Need Fixing)

#### Issue 1: Directory Structure Mismatch

**Local Storage:**

- Raw videos: `../data/videos/raw/filename.mp4`
- Processed videos: `../data/videos/processed/filename_annotated.mp4`

**Supabase Storage (Current - Broken):**

- Raw videos: `filename.mp4` (should be `raw/filename.mp4`)
- Processed videos: Not uploaded at all (only stored locally)

**Fix Needed:**

- Add `raw/` prefix for raw video uploads to Supabase
- Upload processed videos to Supabase with `processed/` prefix

#### Issue 2: Processed Videos Not Using Storage Service

**Current Behavior:**

- Annotation service writes directly to local filesystem
- Never uploads to Supabase
- Annotated video streaming endpoint only looks at local filesystem

**Fix Needed:**

- Use `storage_service.upload_file()` for processed videos
- Update annotated streaming endpoint to support Supabase
- Store processed videos in `processed/` subfolder

### Supabase Features We're Using

✅ **CDN Delivery** - Automatic with public URLs
✅ **Storage Buckets** - Using this
❌ **Video Transformations** - Not available (we do our own processing)

### Implementation Plan

1. **Fix Raw Video Upload**

   - Modify upload endpoint to use `raw/filename.mp4` for Supabase
   - Keep local behavior as-is (already uses `UPLOAD_DIR`)

2. **Fix Processed Video Upload**

   - Update annotation service to use `storage_service.upload_file()`
   - Upload to `processed/filename_annotated.mp4` in Supabase
   - Keep local behavior as-is (already uses `PROCESSED_DIR`)

3. **Fix Annotated Video Streaming**
   - Update streaming endpoint to use storage service
   - Support both local and Supabase paths
   - Use `storage_service.get_file_url()` or `download_file()` as appropriate

### Future Considerations (Not for V1)

- Lazy processing (generate on-demand) - More complex, not needed yet
- Video compression/optimization - Can add later if needed
- Multiple annotation styles - Current approach supports this
- CDN caching strategies - Supabase handles this automatically

## Summary

**For V1**: Keep pre-processing approach, just fix the bugs so it works correctly with Supabase storage.

**Key Principle**: Simple, working code that serves videos fast. Optimize later if needed.
