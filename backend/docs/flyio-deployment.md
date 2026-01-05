# Fly.io Worker Deployment Guide

This guide walks you through deploying the Tennis Coach worker service to Fly.io for processing video analysis jobs.

## Overview

The worker service runs separately from the API service and processes background jobs from the Redis queue. This architecture allows:

- **API Service**: Runs on Render free tier (handles HTTP requests)
- **Worker Service**: Runs on Fly.io (processes video analysis - memory intensive)
- **Both connect to**: Same Redis instance (Render) and Supabase database/storage

## Prerequisites

1. **Fly.io Account**: Sign up at [fly.io](https://fly.io) (free 7-day trial)
2. **Fly CLI**: Install the Fly.io command-line tool (see Step 1)
3. **Existing Infrastructure**:
   - Render API service (already deployed)
   - Render Redis instance (already deployed)
   - Supabase database and storage (already configured)

---

## Quick Start (TL;DR)

**For experienced users who just need the commands:**

```bash
# 1. Install & login
brew install flyctl  # macOS
fly auth login

# 2. Create app
fly apps create tennis-coach-worker

# 3. Set secrets (get values from Render/Supabase dashboards)
fly secrets set REDIS_URL="redis://..."
fly secrets set PROFILE="production"
fly secrets set SERVICE_TYPE="worker"
fly secrets set SUPABASE_URL="https://..."
fly secrets set SUPABASE_SECRET_KEY="..."
fly secrets set SUPABASE_DB_URL="postgresql://..."
fly secrets set SUPABASE_STORAGE_BUCKET="..."

# 4. Deploy (uses default VM size initially)
fly deploy

# 5. Scale VM to 1GB RAM (after first deploy)
fly scale vm shared-cpu-2x --memory 1024

# 6. Verify
fly status
fly logs

# 7. (Optional) Scale to zero to save costs
fly scale count 0
```

**Need more details?** Continue reading below for step-by-step instructions, troubleshooting, and advanced topics.

---

## Deployment Steps (Detailed)

**Important**: The `fly.toml` configuration file already exists in this repository. We will **NOT** use `fly launch` - instead, we'll create the app directly and use the existing configuration.

**Quick Summary:**

1. Install Fly CLI
2. Login to Fly.io
3. Create app: `fly apps create tennis-coach-worker`
4. Set secrets (Redis, Supabase, etc.)
5. Deploy: `fly deploy` (uses default VM size initially)
6. Configure VM: `fly scale vm shared-cpu-2x --memory 1024` (after deploy)
7. Verify: `fly status` and `fly logs`
8. (Optional) Scale to zero: `fly scale count 0`

### Step 1: Install Fly CLI

```bash
# macOS
brew install flyctl

# Linux
curl -L https://fly.io/install.sh | sh

# Windows (PowerShell)
iwr https://fly.io/install.ps1 -useb | iex

# Verify installation
fly version
```

### Step 2: Login to Fly.io

```bash
fly auth login
```

This will open a browser window for authentication. Complete the login in your browser.

**Verify login:**

```bash
fly auth whoami
```

### Step 3: Create the Fly.io App

Since `fly.toml` already exists, we need to create the app in Fly.io's system:

```bash
# From project root directory
fly apps create tennis-coach-worker

# If the app name is taken, choose a different name:
# fly apps create tennis-coach-worker-<yourname>
```

**Important**: If you choose a different app name, update `app = "tennis-coach-worker"` in `fly.toml` to match.

### Step 4: Set Environment Variables (Secrets)

Set all required environment variables as Fly.io secrets:

```bash
# Redis connection (from your Render Redis instance)
fly secrets set REDIS_URL="redis://default:<password>@<host>:<port>/0"

# Profile (production mode)
fly secrets set PROFILE="production"

# Supabase configuration
fly secrets set SUPABASE_URL="https://your-project.supabase.co"
fly secrets set SUPABASE_SECRET_KEY="your-secret-key"
fly secrets set SUPABASE_DB_URL="postgresql://postgres:password@db.xxx.supabase.co:5432/postgres"
fly secrets set SUPABASE_STORAGE_BUCKET="your-bucket-name"

# Service type (tells app to run as worker, not API)
fly secrets set SERVICE_TYPE="worker"

# Optional: Environment variable (for compatibility - will be removed in PR 3)
fly secrets set ENVIRONMENT="production"
```

**Important**:

- Get `REDIS_URL` from your Render Redis dashboard
- Get Supabase credentials from your Supabase project settings
- Never commit secrets to git!

### View Current Secrets

```bash
fly secrets list
```

### Update a Secret

```bash
fly secrets set KEY="new-value"
```

### Remove a Secret

```bash
fly secrets unset KEY
```

### Step 5: Deploy Worker Service

**Note**: We'll configure VM resources after the first deploy (see Step 7). The first deploy will use default settings (256MB RAM, 1 CPU), which is fine for the initial deployment.

Deploy from the project root directory:

Deploy from the project root directory:

```bash
fly deploy
```

**What happens during deployment:**

1. Builds the Docker image using `Dockerfile.worker` (optimized, ~2GB compressed)
2. Pushes to Fly.io registry
3. Deploys the worker service
4. Starts the worker process
5. Models download automatically on first use (not included in image)

**First deployment may take 5-10 minutes** (building and pushing the image).

**Note:** The Docker image is optimized to exclude ML models (~200-400MB savings). Models are downloaded automatically at runtime when first needed. This keeps the image under Fly.io's 8GB unpacked limit.

### Step 6: Configure VM Resources (After First Deploy)

After the first deploy succeeds, scale the VM to the recommended size:

```bash
# Set to 1GB RAM with 2 shared CPUs (recommended for video processing)
fly scale vm shared-cpu-2x --memory 1024

# Verify configuration
fly scale show
```

**Why after deploy?** Fly.io requires at least one machine to exist before you can configure VM resources. The first deploy creates that machine with default settings.

### Step 7: Verify Deployment

### Check Worker Status

```bash
# View app status
fly status

# View worker logs
fly logs

# Follow logs in real-time
fly logs --follow
```

### Test Worker Connectivity

The worker should:

1. Connect to Redis successfully
2. Start listening on queues: `default`, `analysis`
3. Process jobs from the queue

Look for these log messages:

```
RQ Worker Startup
Environment: production
Starting 1 worker
Listening on queues: default, analysis
```

### Step 8: Configure Scaling (Optional)

By default, the worker will run continuously. To save costs by scaling to zero when idle:

```bash
# Scale to zero when idle (recommended for cost savings)
fly scale count 0

# To always keep 1 instance running:
fly scale count 1
```

**Note**: When scaled to zero, Fly.io will automatically start the worker when jobs are queued (may take 10-30 seconds to start).

### Step 9: Monitor and Scale

### View Metrics

```bash
# Open Fly.io dashboard in browser
fly dashboard

# View metrics in terminal
fly metrics
```

### Resource Configuration

Default configuration:

- **Memory**: 1024 MB (1 GB)
- **CPU**: 2 shared CPUs
- **Region**: iad (Washington, D.C.) - set in `fly.toml`

To change resources:

```bash
# Increase memory (if needed for larger videos)
fly scale vm shared-cpu-2x --memory 2048

# Change CPU tier
fly scale vm shared-cpu-4x --memory 1024
```

## Troubleshooting

### Worker Not Starting

**Check logs:**

```bash
fly logs
```

**Common issues:**

1. **Redis connection failed**: Verify `REDIS_URL` secret is correct
2. **Missing environment variables**: Check `fly secrets list`
3. **Import errors**: Verify all dependencies are in `pyproject.toml`

### Worker Crashes on Job Processing

**Check memory usage:**

```bash
fly metrics
```

**Solutions:**

1. Increase memory: `fly scale vm shared-cpu-4x --memory 2048`
2. Check video limits in `config.py` (production profile has stricter limits)
3. Review worker logs for OOM errors

### Jobs Stuck in Queue

**Check Redis connectivity:**

```bash
# From worker logs
fly logs | grep -i redis
```

**Verify queue status:**

- Check Render Redis dashboard
- Verify jobs are being enqueued from API service

### Worker Not Processing Jobs

**Check worker is listening:**

```bash
fly logs | grep -i "listening"
```

**Verify queue names match:**

- Worker listens on: `default`, `analysis`
- API enqueues to: `analysis` queue

## Cost Management

### Current Configuration Cost

- **Free tier**: 3 shared VMs (can combine)
- **1GB RAM, 2 CPUs**: ~$0.01/hour when running
- **Scales to zero**: $0 when idle
- **Estimated monthly**: $0-5/month (depends on usage)

### Cost Optimization Tips

1. **Scale to zero**: Already configured (min_machines = 0)
2. **Monitor usage**: Use `fly metrics` to track runtime
3. **Optimize video limits**: Stricter limits = faster processing = less runtime
4. **Batch processing**: Process multiple videos in one session

### View Costs

```bash
# View usage
fly dashboard

# Check billing
fly billing
```

## Updating the Worker

### Deploy Updates

```bash
# Make code changes
git add .
git commit -m "feat: update worker configuration"

# Deploy
fly deploy
```

### Rollback

```bash
# View deployment history
fly releases

# Rollback to previous version
fly releases rollback <release-id>
```

## Architecture Diagram

```
┌─────────────────┐
│  Render Free    │  API Service (HTTP, auth, enqueue jobs)
│  512MB RAM      │  $0/month
└────────┬────────┘
         │
         │ (Redis Queue)
         │
┌────────▼────────┐
│  Render Redis   │  Job Queue
│  25MB RAM       │  $0/month
└────────┬────────┘
         │
         │ (Process jobs)
         │
┌────────▼────────┐
│  Fly.io Worker  │  Video Analysis (YOLO + MediaPipe)
│  1GB RAM        │  ~$0-5/month (scales to zero)
└─────────────────┘
         │
         │ (Store results)
         │
┌────────▼────────┐
│  Supabase       │  Database + Storage
│  PostgreSQL     │  (existing)
└─────────────────┘
```

## Environment Variables Reference

### Required Secrets

| Variable                  | Description           | Example                            |
| ------------------------- | --------------------- | ---------------------------------- |
| `REDIS_URL`               | Redis connection URL  | `redis://default:pass@host:6379/0` |
| `PROFILE`                 | Application profile   | `production`                       |
| `SERVICE_TYPE`            | Service type          | `worker`                           |
| `SUPABASE_URL`            | Supabase project URL  | `https://xxx.supabase.co`          |
| `SUPABASE_SECRET_KEY`     | Supabase secret key   | `xxx...`                           |
| `SUPABASE_DB_URL`         | PostgreSQL connection | `postgresql://...`                 |
| `SUPABASE_STORAGE_BUCKET` | Storage bucket name   | `videos`                           |

### Optional Secrets

| Variable      | Description          | Default      |
| ------------- | -------------------- | ------------ |
| `ENVIRONMENT` | Environment (legacy) | `production` |
| `DEBUG`       | Debug mode           | `False`      |
| `LOG_LEVEL`   | Logging level        | `INFO`       |

## Next Steps

After deploying the worker:

1. **Test video upload and analysis** from the frontend
2. **Monitor worker logs** for any errors
3. **Check job processing** in Render Redis dashboard
4. **Optimize video limits** if needed (see `config.py`)
5. **Consider PR 3**: Consolidate `ENVIRONMENT` → `PROFILE` (code cleanup)

---

## Automated Deployment with GitHub Actions (Future Enhancement)

Once the CLI deployment is working and tested, you can set up automatic deployments via GitHub Actions. This allows deployments to happen automatically when code is merged to `main`.

### When to Use GitHub Actions vs CLI

| Task                           | CLI    | GitHub Actions        |
| ------------------------------ | ------ | --------------------- |
| Initial setup                  | ✅ Yes | ❌ No                 |
| Testing changes                | ✅ Yes | ⚠️ Slow (push → wait) |
| Production deploy              | ✅ Yes | ✅ Better (automatic) |
| Configuration (secrets, scale) | ✅ Yes | ❌ No                 |
| One-off fixes                  | ✅ Yes | ⚠️ Overkill           |

### Setup Steps

#### Step 1: Generate Fly.io API Token

```bash
# Generate a deploy token (one-time setup)
fly tokens create deploy

# Save this token - you'll add it to GitHub secrets
```

#### Step 2: Add GitHub Secret

1. Go to your GitHub repo → **Settings** → **Secrets and variables** → **Actions**
2. Click **"New repository secret"**
3. Name: `FLY_API_TOKEN`
4. Value: The token from Step 1
5. Click **"Add secret"**

#### Step 3: Create GitHub Actions Workflow

Create `.github/workflows/deploy-flyio-worker.yml`:

```yaml
name: Deploy Fly.io Worker

on:
  push:
    branches: [main]
    paths:
      - "backend/**"
      - "Dockerfile.worker"
      - "fly.toml"
      - ".github/workflows/deploy-flyio-worker.yml"

jobs:
  deploy:
    runs-on: ubuntu-latest
    steps:
      - name: Checkout code
        uses: actions/checkout@v4

      - name: Setup Fly.io
        uses: superfly/flyctl-actions/setup-flyctl@master

      - name: Deploy to Fly.io
        run: flyctl deploy --remote-only
        env:
          FLY_API_TOKEN: ${{ secrets.FLY_API_TOKEN }}
```

### How It Works

1. **Code pushed to `main`** → Triggers workflow
2. **GitHub Actions** → Checks out code, sets up Fly CLI
3. **Builds Docker image** → Uses `Dockerfile.worker` (specified in `fly.toml`)
4. **Deploys to Fly.io** → Uses `fly.toml` configuration
5. **Worker restarts** → With new code

### Benefits

- ✅ **Automatic**: Deploys on merge to `main`
- ✅ **Consistent**: Same process every time
- ✅ **History**: See all deployments in GitHub Actions tab
- ✅ **Safety**: Only deploys after PR review
- ✅ **Team-friendly**: Anyone can merge, deployment is automatic

### Recommended Workflow

**Development/Testing:**

```bash
# Make changes locally
# Test locally
fly deploy  # Manual deploy via CLI
```

**Production:**

```bash
# Make changes
git add .
git commit -m "feat: update worker logic"
git push

# Create PR
# After PR review and merge to main:
# → GitHub Actions automatically deploys
```

### Important Notes

- **Secrets**: Still managed via CLI (`fly secrets set`)
- **Scaling**: Still managed via CLI (`fly scale`)
- **Configuration**: `fly.toml` changes are automatically picked up
- **Rollback**: Use `fly releases rollback` if needed

### Troubleshooting GitHub Actions Deployments

**Deployment fails:**

- Check GitHub Actions logs
- Verify `FLY_API_TOKEN` secret is set correctly
- Ensure `fly.toml` is valid: `fly config validate`

**Deployment succeeds but worker doesn't start:**

- Check worker logs: `fly logs`
- Verify secrets are set: `fly secrets list`
- Check VM resources: `fly scale show`

## Related Documentation

- [Infrastructure Recommendations](../project_docs/infrastructure-recommendations.md)
- [Background Tasks with RQ](background-tasks-rq.md)
- [Profile Configuration](profile-configuration.md)

## Support

- **Fly.io Docs**: https://fly.io/docs
- **Fly.io Community**: https://community.fly.io
- **Project Issues**: GitHub Issues
