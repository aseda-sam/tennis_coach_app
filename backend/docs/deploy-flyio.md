# Deploy (Fly.io) — optional notes

If you deploy, keep it simple:

- **API**: Fly.io app
- **Worker**: Fly.io app (RQ worker)
- **Redis**: Upstash
- **DB/Auth/Storage**: Supabase

## Required env vars (API + worker)

```bash
PROFILE=production
SERVICE_TYPE=api   # or worker

SUPABASE_DB_URL=postgresql://...
SUPABASE_URL=https://...
SUPABASE_SECRET_KEY=...
SUPABASE_STORAGE_BUCKET=...

REDIS_URL=rediss://...
```

## First deploy checklist

- Deploy API + worker
- Scale worker memory (CV deps can be heavy)
- Run Alembic migrations once against the prod DB

