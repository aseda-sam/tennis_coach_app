# Video Streaming Architecture

## Overview

This document explains how video streaming works in the Tennis Coach App, comparing local storage vs Supabase storage approaches, cost implications, and real-world streaming best practices.

## Table of Contents

1. [Current Implementation](#current-implementation)
2. [Streaming Approaches Comparison](#streaming-approaches-comparison)
3. [Cost Analysis](#cost-analysis)
4. [Real-World Streaming Practices](#real-world-streaming-practices)
5. [Optimizations & Recommendations](#optimizations--recommendations)
6. [Implementation Details](#implementation-details)

---

## Current Implementation

### Local Storage Streaming

**How it works:**
```
User → FastAPI → FileResponse → Reads from local disk → Streams to user
```

**Technical Details:**
- FastAPI's `FileResponse` reads file from disk
- Streams data in chunks to the user
- **Supports HTTP Range Requests** (206 Partial Content) - enables video seeking
- Server CPU/RAM handles all streaming
- Bandwidth comes from your server

**Code Location:**
```python
# backend/app/api/routes/video.py (lines 189-198)
return FileResponse(
    path=str(file_path),
    media_type=db_video.content_type or "video/mp4",
    filename=get_safe_filename(db_video.filename),
)
```

**Pros:**
- ✅ No egress fees
- ✅ Full control over streaming
- ✅ Range requests work automatically
- ✅ Simple implementation

**Cons:**
- ❌ Server handles all bandwidth
- ❌ Limited scalability
- ❌ Server resources tied up during streaming
- ❌ Not ideal for many concurrent users

---

### Supabase Storage Streaming (Current)

**How it works:**
```
User → FastAPI → RedirectResponse → Supabase CDN URL → User downloads from Supabase
```

**Technical Details:**
- FastAPI redirects to Supabase public URL
- User's browser downloads directly from Supabase CDN
- **Your server is NOT in the data path** (only handles redirect)
- Supabase CDN handles delivery globally
- HTTP Range Requests supported (browser seeking works)

**Code Location:**
```python
# backend/app/api/routes/video.py (lines 172-188)
if settings.STORAGE_TYPE == "supabase":
    try:
        file_url = storage_service.get_file_url(db_video.filename)
        return RedirectResponse(url=file_url)  # Redirect to Supabase
    except:
        # FALLBACK: Downloads entire file - EXPENSIVE!
        file_data = storage_service.download_file(db_video.filename)
        return StreamingResponse(iter([file_data]), ...)
```

**Pros:**
- ✅ Server not in data path (just redirect)
- ✅ CDN delivery (fast, global)
- ✅ Range requests work
- ✅ Scalable
- ✅ Offloads bandwidth from your server

**Cons:**
- ❌ **Current fallback is expensive** (downloads entire file to RAM)
- ❌ Supabase egress costs (~$0.09/GB after free tier)
- ❌ Public URLs (security concern - should use signed URLs for private)

---

## Streaming Approaches Comparison

### Architecture Diagrams

#### Local Storage
```
┌─────────┐     ┌──────────┐     ┌──────────┐     ┌─────────┐
│  User   │────▶│ FastAPI  │────▶│  Disk    │────▶│  User   │
│ Browser │     │ Server   │     │ Storage  │     │ Browser │
└─────────┘     └──────────┘     └──────────┘     └─────────┘
                      │
                      │ All bandwidth
                      │ through server
                      ▼
```

#### Supabase Storage (Current - Redirect)
```
┌─────────┐     ┌──────────┐     ┌──────────┐     ┌─────────┐
│  User   │────▶│ FastAPI  │────▶│ Redirect │     │  User   │
│ Browser │     │ Server   │     │ (302)    │     │ Browser  │
└─────────┘     └──────────┘     └──────────┘     └─────────┘
                      │                                  │
                      │                                  │
                      │                                  ▼
                      │                          ┌──────────────┐
                      │                          │ Supabase CDN │
                      │                          │ (Direct DL)  │
                      │                          └──────────────┘
                      │
                      │ Minimal server load
                      │ (just redirect)
```

#### Supabase Storage (Fallback - Current Issue)
```
┌─────────┐     ┌──────────┐     ┌──────────┐     ┌──────────┐     ┌─────────┐
│  User   │────▶│ FastAPI  │────▶│ Download │────▶│  Memory  │────▶│  User   │
│ Browser │     │ Server   │     │ Entire   │     │  Buffer  │     │ Browser │
│         │     │          │     │ File      │     │          │     │         │
└─────────┘     └──────────┘     └──────────┘     └──────────┘     └─────────┘
                      │
                      │ EXPENSIVE!
                      │ Downloads entire file
                      │ to server RAM first
                      ▼
```

---

## Cost Analysis

### Scenario: 100 users watch a 500MB video

#### Option 1: Through Your Server (Local Storage)
- **Bandwidth:** 100 × 500MB = **50GB** through your server
- **Cost:** 
  - Render bandwidth costs (if applicable)
  - Server CPU/RAM usage
  - Potential server scaling needs
- **Performance:** Limited by server capacity
- **Scalability:** Poor - server becomes bottleneck

#### Option 2: Supabase Redirect (Current - Good)
- **Bandwidth:** 50GB through Supabase CDN
- **Cost:** 
  - Supabase: ~$4.50 (50GB × $0.09/GB, after free tier)
  - Your server: Minimal (just redirects)
- **Performance:** Fast (CDN edge locations globally)
- **Scalability:** Excellent - CDN handles load

#### Option 3: Supabase Fallback (Current Code if Redirect Fails)
- **If redirect fails:** Downloads 50GB to server RAM
- **Then streams:** 50GB through your server
- **Cost:** 
  - Server RAM: High (entire file in memory)
  - Server bandwidth: 50GB
  - Supabase egress: 50GB (download) + 50GB (stream) = 100GB
  - **Total: Very expensive**
- **Performance:** Slow (downloads entire file first)

### Cost Comparison Table

| Approach | Server Load | Bandwidth Cost | Scalability | Performance |
|----------|------------|----------------|--------------|-------------|
| Local Storage | High | Your server | Poor | Limited |
| Supabase Redirect | Low | Supabase CDN | Excellent | Fast |
| Supabase Fallback | Very High | Both (expensive) | Poor | Slow |

---

## Real-World Streaming Practices

### How Major Platforms Do It

#### Option A: Direct Object Storage URLs (What You're Doing)
```
User → CDN/Storage → Direct download
```
**Examples:** YouTube (simplified), Vimeo, many SaaS apps
- ✅ Fast, scalable, cheap
- ✅ Works well for your use case
- ✅ Simple implementation

#### Option B: Streaming Protocols (HLS/DASH)
```
User → CDN → Adaptive bitrate segments
```
**Examples:** Netflix, YouTube (adaptive), Twitch
- ✅ Multiple quality levels
- ✅ Adaptive bitrate (adjusts to connection)
- ❌ More complex
- ❌ Better for large scale

#### Option C: Through Application Server
```
User → Your Server → Storage → Stream
```
**Examples:** Small apps, internal tools
- ✅ Full control
- ❌ Not scalable
- ❌ Expensive at scale
- ❌ Server becomes bottleneck

### HTTP Range Requests (206 Partial Content)

**What it is:**
- Allows clients to request specific byte ranges of a file
- Essential for video seeking/scrubbing
- Browser automatically uses this for `<video>` tags

**How it works:**
```
Client Request:
GET /video.mp4
Range: bytes=0-1023

Server Response:
HTTP/1.1 206 Partial Content
Content-Range: bytes 0-1023/5000000
Content-Length: 1024
```

**Current Support:**
- ✅ **Local Storage:** FastAPI `FileResponse` supports automatically
- ✅ **Supabase Redirect:** Supabase CDN supports automatically
- ❌ **Supabase Fallback:** `StreamingResponse` doesn't support (needs fix)

---

## Optimizations & Recommendations

### ✅ Keep Current Redirect Approach

**Why:**
- Efficient - bypasses your server
- CDN handles delivery globally
- HTTP Range Requests work automatically
- Scalable architecture

### ⚠️ Fix Expensive Fallback

**Current Problem:**
```python
except:
    file_data = storage_service.download_file(db_video.filename)  # Downloads ENTIRE file
    return StreamingResponse(iter([file_data]), ...)  # Streams from memory
```

**Issues:**
- Downloads entire video to server RAM (e.g., 500MB)
- Then streams through your server
- Very expensive and slow

**Recommended Fix:**
```python
except (ValueError, RuntimeError, OSError) as e:
    logger.error(f"Failed to get Supabase URL: {e}")
    # Don't proxy through server - return error instead
    raise HTTPException(
        status_code=503,
        detail="Video streaming temporarily unavailable. Please try again later."
    )
```

**Alternative (if you need fallback):**
- Use signed URLs instead of public URLs
- Implement proper error handling
- Consider retry logic

### 🔒 Use Signed URLs for Private Buckets

**Current (Public URLs):**
```python
.get_public_url(file_path)  # Anyone with URL can access
```

**Recommended (Private Buckets):**
```python
.create_signed_url(file_path, expires_in=3600)  # Expires in 1 hour, secure
```

**Benefits:**
- More secure
- URLs expire automatically
- Better for private apps
- Can add authentication checks before generating

### 📊 Add Caching Headers (If Serving Through Server)

**For local storage or fallback:**
```python
headers = {
    "Cache-Control": "public, max-age=3600",  # Cache for 1 hour
    "Accept-Ranges": "bytes",  # Support range requests
    "Content-Length": str(file_size)
}
```

**Note:** With Supabase redirect, CDN handles caching automatically.

### 🎯 Future Optimizations

1. **Video Transcoding:**
   - Multiple quality levels (1080p, 720p, 480p)
   - Adaptive bitrate streaming (HLS/DASH)
   - Better for mobile users

2. **CDN Caching:**
   - Supabase CDN already caches
   - Consider Cloudflare for additional caching

3. **Compression:**
   - Optimize video encoding (H.264, H.265)
   - Reduce file sizes before upload
   - Lower storage and bandwidth costs

4. **Progressive Loading:**
   - Stream metadata first
   - Load video on demand
   - Better initial page load

---

## Implementation Details

### Current Code Structure

**Storage Service:**
- Location: `backend/app/services/storage_service.py`
- Methods:
  - `upload_file()` - Uploads to local or Supabase
  - `download_file()` - Downloads from local or Supabase
  - `get_file_url()` - Gets URL for streaming
  - `delete_file()` - Deletes from storage

**Video Routes:**
- Location: `backend/app/api/routes/video.py`
- Endpoint: `GET /videos/{video_id}/stream`
- Logic:
  1. Gets video from database
  2. Checks storage type
  3. For Supabase: Redirects to public URL
  4. For Local: Uses FileResponse

### Database Storage

**Local Storage:**
- `file_path` column: Full path (e.g., `../data/videos/raw/video.mp4`)

**Supabase Storage:**
- `file_path` column: Just filename (e.g., `video.mp4`)
- Full path handled by Supabase bucket structure

### Environment Configuration

**Local Development:**
```bash
STORAGE_TYPE=local
```

**Production (Supabase):**
```bash
STORAGE_TYPE=supabase
SUPABASE_STORAGE_URL=https://xxxxx.supabase.co
SUPABASE_KEY=eyJhbGc...
SUPABASE_STORAGE_BUCKET=tennis-videos
```

---

## Summary

### Current Status

| Aspect | Local Storage | Supabase (Current) | Supabase (Optimized) |
|--------|---------------|-------------------|---------------------|
| Server Load | High | Low | Low |
| Bandwidth Cost | Your server | Supabase CDN | Supabase CDN |
| Performance | Limited | Fast (CDN) | Fast (CDN) |
| Scalability | Poor | Good | Excellent |
| Range Requests | ✅ Yes | ✅ Yes | ✅ Yes |
| Fallback Cost | N/A | ❌ Expensive | ✅ Fixed |
| Security | ✅ Good | ⚠️ Public URLs | ✅ Signed URLs |

### Key Takeaways

1. **Supabase redirect approach is good** - keeps server out of data path
2. **Fix expensive fallback** - don't download entire files to RAM
3. **Use signed URLs** - more secure for private apps
4. **CDN benefits** - global edge locations, fast delivery
5. **Cost effective** - Supabase egress cheaper than server bandwidth at scale

### Next Steps

1. ✅ Remove expensive fallback in streaming route
2. ✅ Implement signed URLs for private buckets
3. ✅ Add proper error handling
4. 🔄 Monitor Supabase egress costs
5. 🔄 Consider video transcoding for multiple qualities (future)

---

## References

- [Supabase Storage Documentation](https://supabase.com/docs/guides/storage)
- [FastAPI FileResponse](https://fastapi.tiangolo.com/advanced/custom-response/#fileresponse)
- [HTTP Range Requests (MDN)](https://developer.mozilla.org/en-US/docs/Web/HTTP/Range_requests)
- [Video Streaming Best Practices](https://web.dev/fast/)

---

**Last Updated:** 2024
**Author:** Tennis Coach App Development Team

