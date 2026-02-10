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
- Alembic migrations run automatically on API deploy via Fly `release_command`
  (`fly.api.toml`), before new API machines are started.

## Pre-deploy checklist (local Docker only)

Before pushing to `main`, run these checks against your local Docker Postgres:

1. Start services:

```bash
docker compose up -d postgres redis
```

2. Run latest migrations:

```bash
cd backend && alembic upgrade head
```

3. Run a focused backend check:

```bash
cd backend && pytest -q
```

4. Smoke test key flows (manual):
   - Upload a video
   - Trigger analysis
   - Open progress endpoint/page

5. Confirm no pending migration mismatch:

```bash
cd backend && alembic current && alembic heads
```

`alembic current` should match `alembic heads` before you push.

## Notes

- Migrations are tied to the **API app only** (`fly.api.toml`) to avoid duplicate
  runs during worker deploys.

## Migration failed playbook

If Fly deploy fails during `release_command` (`alembic upgrade head`):

1. Confirm the current production Alembic version:

```bash
fly ssh console -a tennis-coach-api -C "cd /app/backend && alembic current"
```

2. List available revisions:

```bash
fly ssh console -a tennis-coach-api -C "cd /app/backend && alembic heads && alembic history --verbose"
```

3. Re-run migration manually to see the exact error:

```bash
fly ssh console -a tennis-coach-api -C "cd /app/backend && alembic upgrade head"
```

4. If migration still fails:
   - Fix the migration/code in a new commit.
   - Push to `main` to trigger a new deploy.
   - Do **not** run `alembic downgrade` in production unless you have a reviewed rollback plan.

5. Verify success after fix:

```bash
fly ssh console -a tennis-coach-api -C "cd /app/backend && alembic current"
```

