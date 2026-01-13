# Fly.io Worker Deployment

Deploy the Tennis Coach worker service to Fly.io for processing video analysis jobs.

## Quick Start

```bash
# 1. Install & login
brew install flyctl  # macOS
fly auth login

# 2. Create app
fly apps create tennis-coach-worker

# 3. Set secrets
fly secrets set REDIS_URL="redis://..."
fly secrets set PROFILE="production"
fly secrets set SERVICE_TYPE="worker"
fly secrets set SUPABASE_URL="https://..."
fly secrets set SUPABASE_SECRET_KEY="..."
fly secrets set SUPABASE_DB_URL="postgresql://..."
fly secrets set SUPABASE_STORAGE_BUCKET="..."

# 4. Deploy
fly deploy

# 5. Scale VM (after first deploy)
fly scale vm shared-cpu-2x --memory 1024

# 6. Verify
fly status
fly logs
```

## Required Secrets

| Variable                  | Description           |
| ------------------------- | --------------------- |
| `REDIS_URL`               | Redis connection URL  |
| `PROFILE`                 | Application profile   |
| `SERVICE_TYPE`            | Service type (`worker`) |
| `SUPABASE_URL`            | Supabase project URL  |
| `SUPABASE_SECRET_KEY`     | Supabase secret key   |
| `SUPABASE_DB_URL`         | PostgreSQL connection |
| `SUPABASE_STORAGE_BUCKET` | Storage bucket name   |

**Note**: Use Upstash Redis (public endpoint, no IP whitelisting) - see [upstash-redis-setup.md](upstash-redis-setup.md)

## VM Configuration

- **Memory**: 1024 MB (1 GB) minimum
- **CPU**: 2 shared CPUs
- **Region**: iad (Washington, D.C.) - set in `fly.toml`

Scale after first deploy:
```bash
fly scale vm shared-cpu-2x --memory 1024
```

## Automated Deployment

GitHub Actions automatically deploys when code is pushed to `main` (see `.github/workflows/deploy-flyio-worker.yml`).

**Setup**:
1. Generate Fly.io API token: `fly tokens create deploy`
2. Add to GitHub Secrets: `FLY_API_TOKEN`

**Manual deploy**: `fly deploy`

## Troubleshooting

**Worker not starting**:
- Check logs: `fly logs`
- Verify secrets: `fly secrets list`
- Check Redis connectivity

**Worker crashes**:
- Check memory: `fly metrics`
- Increase memory if needed: `fly scale vm shared-cpu-4x --memory 2048`

**Jobs stuck**:
- Verify Redis connection
- Check worker is listening: `fly logs | grep -i "listening"`

## Cost

- **Free tier**: 3 shared VMs
- **1GB RAM, 2 CPUs**: ~$0.01/hour when running
- **Scales to zero**: $0 when idle
- **Estimated**: $0-5/month

Scale to zero: `fly scale count 0`

## Related Docs

- [Background Tasks](background-tasks.md)
- [Upstash Redis Setup](upstash-redis-setup.md)
