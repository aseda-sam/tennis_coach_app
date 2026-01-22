# Backend Deployment: Fly.io Consolidation Guide

This guide covers consolidating the Tennis Coach backend onto Fly.io. It focuses on a simple, low-risk path using Fly.io for both API and Worker, while keeping Supabase (DB/Auth/Storage) and Upstash Redis.

## Scope

- **Backend API**: FastAPI service on Fly.io
- **Background Worker**: RQ worker for video analysis on Fly.io
- **Redis**: Upstash (external)
- **Database/Auth/Storage**: Supabase (keep as-is)

---

## Prerequisites

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

- Works seamlessly with Fly.io
- Public endpoint, no IP allow-listing required
- TLS supported with `rediss://`

**Do you need to rethink Redis?**  
If you want London or near-London regions for all services, see the [Region Migration Steps](#region-migration-steps-london) section below to create a new Upstash Redis database in **`eu-west-2` (London)** or **`eu-west-1` (Ireland)**. Otherwise keep it as-is.

### Region Targets (London or Close)

- **Fly.io**: `lhr` (London)
- **Upstash**: `eu-west-2` (London) or `eu-west-1` (Ireland)
- **Supabase**: `London` (if creating a new project; region is not changeable in-place)

---

## Region Migration Steps (London)

If you're migrating existing services to London, follow this order to minimize downtime.

### Step 1: Create New Upstash Redis (London)

1. **Go to Upstash Dashboard**: https://console.upstash.com
2. **Create New Database**:
   - Name: `tennis-coach-redis-london`
   - Type: Redis
   - **Region**: `eu-west-2` (London) or `eu-west-1` (Ireland)
   - TLS: Enabled (recommended)
3. **Get Connection String**:
   - Copy the `rediss://` connection string
   - Format: `rediss://default:password@region.upstash.io:6379`
4. **Keep Old Redis Running**: Don't delete the old database yet until migration is verified.

**Note**: Any queued jobs in the old Redis will be lost. For a clean migration, wait for current jobs to complete before switching.

### Step 2: Check Supabase Region

1. **Go to Supabase Dashboard**: https://app.supabase.com
2. **Check Current Region**: Project Settings → Infrastructure → Region
3. **Recommendation**: Unless you're experiencing latency issues, keep your existing Supabase project regardless of region. Moving it requires a new project and data migration.

### Step 3: Update Existing Worker to London

**Important**: Fly.io does NOT automatically move existing machines when you change `primary_region`. You must destroy existing machines first, then deploy to create new ones in the target region.

If your worker is already on Fly.io:

```bash
# 1. Update fly.toml
# Change: primary_region = "lhr"

# 2. List current machines to see their IDs
fly machines list -a tennis-coach-worker

# 3. Destroy existing machines in old region (e.g., IAD)
# Replace <machine-id> with actual machine IDs from step 2
fly machines destroy <machine-id-1> -a tennis-coach-worker
fly machines destroy <machine-id-2> -a tennis-coach-worker

# OR destroy all machines at once:
fly machines list -a tennis-coach-worker | grep -E "^[0-9a-f]" | awk '{print $1}' | xargs -I {} fly machines destroy {} -a tennis-coach-worker

# 4. Deploy - this will create NEW machines in LHR (based on primary_region)
fly deploy -a tennis-coach-worker

# 5. Update Redis URL to new London Upstash (if applicable)
fly secrets set REDIS_URL="rediss://..." -a tennis-coach-worker

# 6. Verify machines are now in London
fly status -a tennis-coach-worker
```

**Alternative (Zero-Downtime Approach):**

If you want to avoid downtime, create new machines in London first, then destroy old ones:

```bash
# 1. List machines to get an existing machine ID
fly machines list -a tennis-coach-worker

# 2. Clone a machine to London (creates new machine in LHR)
fly machines clone <existing-machine-id> --region lhr -a tennis-coach-worker

# 3. Verify new machine is running
fly status -a tennis-coach-worker

# 4. Destroy old machines in IAD
fly machines destroy <old-machine-id-1> -a tennis-coach-worker
fly machines destroy <old-machine-id-2> -a tennis-coach-worker
```

**Why this is necessary**: `primary_region` only affects **new machines** created during deployment. Existing machines stay in their current region until destroyed. `fly deploy` updates machines in place; it does not migrate them to a new region.

### Step 4: Migration Order (Recommended)

1. Create new Upstash Redis (London)
2. Update existing worker to London + new Redis
3. Create new API app in London with new Redis
4. Test both services
5. Update frontend API URL (pointing to new Fly.io API)
6. Delete old Redis (after 24-48 hours of stability)

### Step 5: Update All Services to New Redis

After creating the London Upstash Redis, update `REDIS_URL` in:

- Fly.io Worker: `fly secrets set REDIS_URL="rediss://..." -a tennis-coach-worker`
- Fly.io API: `fly secrets set REDIS_URL="rediss://..." -a tennis-coach-api`

### Step 6: Verify Region Migration

Check all services are in London:

- **Fly.io**: `fly status` should show `lhr` region
- **Upstash**: Dashboard should show `eu-west-2` or `eu-west-1`
- **Test**: Upload a video and verify processing works end-to-end

---

## Implementation: Fly.io Setup

**Before starting**: If you want London regions, complete [Region Migration Steps](#region-migration-steps-london) first.

You will run **two Fly.io apps**:

- `tennis-coach-api` (new)
- `tennis-coach-worker` (existing)

### 1. Prepare API App

Create a new Fly app for the API:

```bash
fly apps create tennis-coach-api
```

Create a `fly.api.toml` file. Suggested minimal config:

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
fly deploy -a tennis-coach-api --config fly.api.toml
```

### 4. Scale API

```bash
fly scale vm shared-cpu-1x --memory 512 -a tennis-coach-api
```

### 5. Worker (Existing)

If migrating an existing worker to London, see [Step 3 in Region Migration Steps](#step-3-update-existing-worker-to-london). **Important**: You must destroy existing machines before deploying to a new region.

If creating a new worker, follow the same pattern as the API but use `Dockerfile.worker`, `fly.toml`, and set `SERVICE_TYPE=worker`.

---

## Recommended Validation Checklist

- [ ] API `/health` returns OK
- [ ] Upload a video from frontend/app
- [ ] Worker picks up a job (check `fly logs -a tennis-coach-worker`)
- [ ] Processed outputs appear in Supabase storage
- [ ] Database records are updated with analysis results

---

## Rollback Plan

1. Keep old services (e.g., on Render) running during the cutover.
2. If issues arise, switch the frontend `REACT_APP_API_URL` back to the old URL.
3. Delete old services only after 48 hours of verified stability.
