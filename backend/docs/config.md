# Configuration (PROFILE-based)

The backend uses a **profile-based** config model: set one `PROFILE` and the app selects which services/vars matter.

## Profiles

- `PROFILE=local`
  - **Auth**: disabled (mock user)
  - **DB**: `DATABASE_URL` if set, otherwise auto-detected: `postgres` host inside Docker, `localhost` outside
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

REDIS_URL=rediss://...  # optional — defaults to redis://localhost:6379/0; use Upstash in real prod
ADMIN_USER_IDS=uuid1,uuid2  # optional — required for admin UI and demo video management
SUPABASE_DEMO_BUCKET=demo-videos  # optional — only needed if using public demo videos
```

## Notes

- `AUTO_CONTACT_DETECTOR_VERSION` controls auto-contact logic:
  - `v1` (default): toss-peak-gated wrist proximity.
  - `v2`: phase-gated proximity (search starts at dominant-arm acceleration onset).
- Don’t duplicate “API reference” docs: use `http://localhost:8000/docs`.
- Keep `.env` permissive; the profile decides what’s required.
