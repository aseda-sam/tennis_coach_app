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

### Redis (Upstash) & Supabase

**Upstash Redis**: Already in London region - no migration needed.

**Supabase**: In Stockholm (North EU) - close enough to London for acceptable latency. No migration needed.

Both services are already optimally located for London-based Fly.io services.

---

## Region Migration Steps (London)

If you're migrating existing services to London, follow this order to minimize downtime.

### Step 1: Verify Upstash Redis Region (Skip if Already in London)

**If your Redis is already in London**: Skip this step and proceed to Step 2.

**If your Redis is in a different region** and you want to move it to London:

1. **Go to Upstash Dashboard**: https://console.upstash.com
2. **Check Current Region**: View your existing database → Details → Region
3. **If not in London**, create a new database:
   - Name: `tennis-coach-redis-london`
   - Type: Redis
   - **Region**: `eu-west-2` (London) or `eu-west-1` (Ireland)
   - TLS: Enabled (recommended)
4. **Get Connection String**:
   - Copy the `rediss://` connection string
   - Format: `rediss://default:password@region.upstash.io:6379`
5. **Keep Old Redis Running**: Don't delete the old database yet until migration is verified.

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

# 5. Scale worker to prevent startup timeout (CRITICAL)
# The worker needs 2GB RAM to start properly with PyTorch/OpenCV dependencies
fly scale vm shared-cpu-2x --memory 2048 -a tennis-coach-worker

# 6. Verify machines are now in London and running
fly status -a tennis-coach-worker
fly logs -a tennis-coach-worker
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

**Assuming Redis is already in London:**

1. Update existing worker to London (see Step 3)
2. Create new API app in London
3. Verify both services connect to existing London Redis
4. Test both services
5. Update frontend API URL (pointing to new Fly.io API)

**If you created a new Redis in Step 1:**

1. Update existing worker to London + new Redis connection string
2. Create new API app in London with new Redis connection string
3. Test both services
4. Update frontend API URL
5. Delete old Redis (after 24-48 hours of stability)

### Step 5: Verify Redis Connection

**If Redis is already in London**: Verify that your existing `REDIS_URL` secrets are correct:

```bash
# Check current Redis URL
fly secrets list -a tennis-coach-worker
fly secrets list -a tennis-coach-api
```

**If you created a new Redis in Step 1**: Update `REDIS_URL` in both services:

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
  SUPABASE_DEMO_BUCKET="demo-videos" \
  REDIS_URL="rediss://..." \
  PROFILE="production" \
  SERVICE_TYPE="api" \
  -a tennis-coach-api
```

**Note**: `SUPABASE_DEMO_BUCKET` is optional but recommended if you plan to use the demo video feature. Create a public bucket named `demo-videos` in Supabase Storage first.

### 3. Deploy API

```bash
fly deploy -a tennis-coach-api --config fly.api.toml
```

### 4. Scale API

```bash
fly scale vm shared-cpu-1x --memory 512 -a tennis-coach-api
```

### 5. Run Database Migrations

After first deployment, run Alembic migrations:

```bash
# Option 1: Via SSH console
fly ssh console -a tennis-coach-api
cd /app
python -m alembic upgrade head
exit

# Option 2: Via fly ssh command
fly ssh console -a tennis-coach-api -C "cd /app && python -m alembic upgrade head"
```

**Verify migrations:**
```bash
fly ssh console -a tennis-coach-api -C "cd /app && python -m alembic current"
```

**Note**: Migrations only need to be run once per database. If you're using an existing Supabase database, migrations may already be applied.

### 6. Worker (Existing)

If migrating an existing worker to London, see [Step 3 in Region Migration Steps](#step-3-update-existing-worker-to-london). **Important**: You must destroy existing machines before deploying to a new region.

**After deploying worker, scale it immediately:**
```bash
# Worker requires 2GB RAM to start properly (prevents startup timeout)
fly scale vm shared-cpu-2x --memory 2048 -a tennis-coach-worker
```

If creating a new worker, follow the same pattern as the API but use `Dockerfile.worker`, `fly.toml`, and set `SERVICE_TYPE=worker`.

**Worker VM Requirements:**
- **Memory**: 2048 MB (2 GB) minimum - required for PyTorch/OpenCV startup
- **CPU**: 2 shared CPUs minimum
- **Region**: `lhr` (London)

---

## Recommended Validation Checklist

- [ ] API `/health` returns OK (`curl https://tennis-coach-api.fly.dev/health`)
- [ ] Database migrations applied (`fly ssh console -a tennis-coach-api -C "cd /app && python -m alembic current"`)
- [ ] All secrets configured (`fly secrets list -a tennis-coach-api` and `fly secrets list -a tennis-coach-worker`)
- [ ] Worker scaled to 2GB RAM (`fly status -a tennis-coach-worker`)
- [ ] Upload a video from frontend/app
- [ ] Worker picks up a job (check `fly logs -a tennis-coach-worker`)
- [ ] Processed outputs appear in Supabase storage
- [ ] Database records are updated with analysis results

---

## Troubleshooting

### Worker Startup Timeout

**Error**: `timeout reached waiting for machine's state to change`

**Cause**: Worker machine doesn't have enough memory to start with PyTorch/OpenCV dependencies.

**Solution**:
```bash
# Scale worker to 2GB RAM (required minimum)
fly scale vm shared-cpu-2x --memory 2048 -a tennis-coach-worker

# Then check logs
fly logs -a tennis-coach-worker
```

**Prevention**: Always scale worker to 2GB RAM immediately after first deploy.

### Worker Not Starting

- Check logs: `fly logs -a tennis-coach-worker`
- Verify secrets: `fly secrets list -a tennis-coach-worker`
- Check Redis connectivity (worker should connect to Upstash Redis)
- Verify memory allocation: `fly status -a tennis-coach-worker`

### Worker Crashes

- Check memory usage: `fly metrics -a tennis-coach-worker`
- Increase memory if needed: `fly scale vm shared-cpu-4x --memory 4096 -a tennis-coach-worker`
- Check logs for errors: `fly logs -a tennis-coach-worker`

---

## Rollback Plan

1. Keep old services (e.g., on Render) running during the cutover.
2. If issues arise, switch the frontend `REACT_APP_API_URL` back to the old URL.
3. Delete old services only after 48 hours of verified stability.
