# Backend Deployment & Consolidation Guide

This guide consolidates backend deployment for the Tennis Coach app. It focuses on a simple, low-risk path and keeps Supabase (DB/Auth/Storage) and Upstash Redis.

## Scope

- **Backend API**: FastAPI service
- **Background Worker**: RQ worker for video analysis
- **Redis**: Upstash (external)
- **Database/Auth/Storage**: Supabase (keep as-is)

## Choose a Consolidation Path

### Option A: Consolidate on Fly.io (API + Worker)

**Best for:** Keeping both services in one platform while retaining flexible CPU/RAM control.

**Pros**
- One platform for API + worker
- Easy to scale worker separately from API
- Good fit for CPU-heavy workloads

**Cons**
- Slightly more hands-on than Render
- Requires a second Fly.io app for the API

### Option B: Consolidate on Render (API + Worker)

**Best for:** Simplest managed experience (fewest moving parts).

**Pros**
- Very managed experience
- Simple deploy workflow from GitHub
- Easy UI-based configuration

**Cons**
- Less granular scaling options
- Worker pricing is fixed to instance tiers

---

## Common Prereqs (Both Paths)

### Required Environment Variables

You already use these in both API and worker:

- `SUPABASE_URL`
- `SUPABASE_SECRET_KEY`
- `SUPABASE_DB_URL`
- `SUPABASE_STORAGE_BUCKET`
- `PROFILE=production`
- `REDIS_URL` (Upstash)

### Redis (Upstash) Guidance

Keep Upstash as-is:

- Works with Fly.io and Render
- Public endpoint, no IP allow-listing
- TLS supported with `rediss://`

**Do you need to rethink Redis?**  
If you want London or near-London regions for all services, see the [Region Migration Steps](#region-migration-steps-london) section below to create a new Upstash Redis database in **`eu-west-2` (London)** or **`eu-west-1` (Ireland)**. Otherwise keep it as-is.

### Region Targets (London or Close)

- **Fly.io**: `lhr` (London)
- **Render**: `London` (or `Ireland` if London is unavailable)
- **Upstash**: `eu-west-2` (London) or `eu-west-1` (Ireland)
- **Supabase**: `London` (if creating a new project; region is not changeable in-place)

---

## Region Migration Steps (London)

If you're migrating existing services to London, follow this order to minimize downtime.

### Step 1: Create New Upstash Redis (London)

1. **Go to Upstash Dashboard**: https://console.upstash.com
2. **Create New Database**:
   - Name: `tennis-coach-redis-london` (or your preferred name)
   - Type: Redis
   - **Region**: `eu-west-2` (London) or `eu-west-1` (Ireland)
   - TLS: Enabled (recommended)
3. **Get Connection String**:
   - Copy the `rediss://` connection string from the database details
   - Format: `rediss://default:password@region.upstash.io:6379`
4. **Keep Old Redis Running**: Don't delete the old database yet

**Note**: Any queued jobs in the old Redis will be lost. For a clean migration, wait for current jobs to complete before switching.

### Step 2: Check Supabase Region

1. **Go to Supabase Dashboard**: https://app.supabase.com
2. **Check Current Region**:
   - Project Settings → Infrastructure → Region
3. **If Already London/EU**: No action needed, keep using existing project
4. **If US Region**: You have two options:
   - **Option A (Recommended)**: Keep current Supabase. Latency from London to US Supabase is usually acceptable (<100ms).
   - **Option B**: Create new Supabase project in London region and migrate data (complex, only if latency is an issue)

**Recommendation**: Unless you're experiencing latency issues, keep your existing Supabase project regardless of region.

### Step 3: Update Existing Worker to London (If on Fly.io)

If your worker is already on Fly.io:

```bash
# 1. Update fly.toml
# Change: primary_region = "lhr"

# 2. Deploy to move machines to London
# Fly.io Machines will automatically follow the primary_region in fly.toml
fly deploy -a tennis-coach-worker

# 3. Update Redis URL to new London Upstash (if applicable)
fly secrets set REDIS_URL="rediss://..." -a tennis-coach-worker

# 4. Verify
fly status -a tennis-coach-worker
```

**Note**: `fly regions set` is deprecated. Fly.io now manages regions based on where your Machines are placed, which is driven by `fly deploy` and your `fly.toml` config.

### Step 4: Migration Order (Recommended)

**If consolidating on Fly.io:**
1. Create new Upstash Redis (London) ← Do this first
2. Update existing worker to London + new Redis
3. Create new API app in London with new Redis
4. Test both services
5. Update frontend API URL
6. Delete old Redis (after 24-48 hours of stability)

**If consolidating on Render:**
1. Create new Upstash Redis (London) ← Do this first
2. Create new API service in London with new Redis
3. Create new Worker service in London with new Redis
4. Test both services
5. Update frontend API URL
6. Delete old services and old Redis (after 24-48 hours)

### Step 5: Update All Services to New Redis

After creating the London Upstash Redis, update `REDIS_URL` in:

- Fly.io Worker: `fly secrets set REDIS_URL="rediss://..." -a tennis-coach-worker`
- Fly.io API: `fly secrets set REDIS_URL="rediss://..." -a tennis-coach-api`
- Render API: Dashboard → Environment → Update `REDIS_URL`
- Render Worker: Dashboard → Environment → Update `REDIS_URL`

### Step 6: Verify Region Migration

Check all services are in London:

- **Fly.io**: `fly status` should show `lhr` region
- **Render**: Dashboard → Service → Region should show `London`
- **Upstash**: Dashboard → Database → Region should show `eu-west-2` or `eu-west-1`
- **Test**: Upload a video and verify processing works end-to-end

---

## Option A: Consolidate on Fly.io

**Before starting**: If you want London regions, complete [Region Migration Steps](#region-migration-steps-london) first (especially creating London Upstash Redis).

You will run **two Fly.io apps**:

- `tennis-coach-api` (new)
- `tennis-coach-worker` (existing)

### 1. Prepare API App

Create a new Fly app for the API:

```bash
fly apps create tennis-coach-api
```

Add a new `fly.api.toml` file (kept separate from worker config) or reuse the default `fly.toml` with a distinct app name.

Suggested minimal config:

```toml
app = "tennis-coach-api"
primary_region = "lhr"

[build]
  dockerfile = "Dockerfile"

[env]
  SERVICE_TYPE = "api"
  PROFILE = "production"

[http_service]
  internal_port = 8000
  force_https = true
  auto_stop_machines = true
  auto_start_machines = true
  min_machines_running = 0
```

### 2. Set API Secrets

```bash
fly secrets set \
  SUPABASE_URL="https://..." \
  SUPABASE_SECRET_KEY="..." \
  SUPABASE_DB_URL="postgresql://..." \
  SUPABASE_STORAGE_BUCKET="..." \
  REDIS_URL="rediss://..." \
  PROFILE="production" \
  SERVICE_TYPE="api" \
  -a tennis-coach-api
```

### 3. Deploy API

```bash
fly deploy -a tennis-coach-api
```

### 4. Scale API

Start small:

```bash
fly scale vm shared-cpu-1x --memory 512 -a tennis-coach-api
```

### 5. Worker (Existing)

If migrating an existing worker to London, see [Step 3 in Region Migration Steps](#step-3-update-existing-worker-to-london-if-on-flyio).

If creating a new worker, follow the same pattern as the API but use `Dockerfile.worker` and set `SERVICE_TYPE=worker`.

Reference:

- `backend/docs/flyio-deployment.md`

### 6. Update Frontend API URL

Point `REACT_APP_API_URL` to the new Fly.io API hostname.

---

## Option B: Consolidate on Render

**Before starting**: If you want London regions, complete [Region Migration Steps](#region-migration-steps-london) first (especially creating London Upstash Redis).

You will run **two Render services**:

- `tennis-coach-api` (web service)
- `tennis-coach-worker` (background worker)

### 1. Create API Service (Web Service)

- Region: `London` (or `Ireland`)
- Runtime: Docker
- Root directory: repo root
- Dockerfile: `Dockerfile`
- Start command: `uvicorn app.main:app --host 0.0.0.0 --port 8000`

### 2. Create Worker Service (Background Worker)

- Region: same as API (`London` or `Ireland`)
- Runtime: Docker
- Root directory: repo root
- Dockerfile: `Dockerfile.worker`
- Start command: `python scripts/start_rq_worker.py`

### 3. Set Environment Variables

Apply the same secrets to both API and worker:

- `SUPABASE_URL`
- `SUPABASE_SECRET_KEY`
- `SUPABASE_DB_URL`
- `SUPABASE_STORAGE_BUCKET`
- `PROFILE=production`
- `REDIS_URL`
- `SERVICE_TYPE` (`api` or `worker`)

### 4. Update Frontend API URL

Point `REACT_APP_API_URL` to the new Render API URL.

---

## Recommended Validation Checklist

- API `/health` returns OK
- Upload a video
- Worker picks up a job (check logs)
- Processed outputs appear in Supabase storage

---

## Rollback Plan (Simple)

1. Keep old services running during the cutover
2. Switch frontend API URL back if needed
3. Delete new services only after verifying stability

