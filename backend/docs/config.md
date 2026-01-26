# Configuration (PROFILE-based)

The backend uses a **profile-based** config model: set one `PROFILE` and the app selects which services/vars matter.

## Profiles

- `PROFILE=local`
  - **Auth**: disabled (mock user)
  - **DB**: `DATABASE_URL` if set, otherwise SQLite default
  - **Storage**: local filesystem
- `PROFILE=production`
  - **Auth**: required
  - **DB**: requires `SUPABASE_DB_URL`
  - **Storage**: Supabase (requires bucket + keys)

## Minimal env vars

### Local (recommended)

```bash
PROFILE=local
```

### Production (or “prod services locally”)

```bash
PROFILE=production
SUPABASE_DB_URL=postgresql://...

SUPABASE_URL=https://...
SUPABASE_SECRET_KEY=...
SUPABASE_STORAGE_BUCKET=...

REDIS_URL=rediss://...  # Upstash in real prod
```

## Notes

- Don’t duplicate “API reference” docs: use `http://localhost:8000/docs`.
- Keep `.env` permissive; the profile decides what’s required.

