# Profile Configuration Guide

## Overview

The application uses a **profile-based configuration system**. Set a single `PROFILE` variable to determine which services are used. Variables that don't match the profile are ignored.

## Profiles

| Profile      | Database        | Storage | Auth     | Use Case                                    |
| ------------ | --------------- | ------- | -------- | ------------------------------------------- |
| `local`      | SQLite/Postgres | Local   | Disabled | Day-to-day development                      |
| `production` | PostgreSQL      | Cloud   | JWT Auth | Testing with prod services OR deployed prod |

**How it works:**

- Set `PROFILE` in `.env` file
- Profile determines which variables are **used** and which are **ignored**
- Your `.env` can contain all variables - profile acts as a filter
- Switch profiles by changing one variable

**Example:**

```bash
PROFILE=local
SUPABASE_DB_URL=postgresql://...  # IGNORED when PROFILE=local
SUPABASE_URL=https://...          # IGNORED when PROFILE=local
```

**Important:** The `production` profile can be used in two ways:

- **Local testing with production services**: Set `PROFILE=production` + `REACT_APP_API_URL=http://localhost:8000/v0`
- **Deployed production**: Set `PROFILE=production` + `REACT_APP_API_URL=https://your-api-domain.com/v0`

The profile controls **which services** to use, while `API_URL` controls **where the backend runs**.

---

## Environment Variables

### Backend

#### Core

| Variable  | Default | Description             |
| --------- | ------- | ----------------------- |
| `PROFILE` | `local` | `local` or `production` |

#### Database

| Variable          | Required\* | Description                                  |
| ----------------- | ---------- | -------------------------------------------- |
| `SUPABASE_DB_URL` | Yes        | PostgreSQL connection string for Supabase    |
| `DATABASE_URL`    | No         | Local Postgres URL (overrides SQLite if set) |

\*Required only when `PROFILE=production`

**Selection logic:**

- `PROFILE=local`: Uses `DATABASE_URL` if set, else SQLite. Ignores `SUPABASE_DB_URL`.
- `PROFILE=production`: Requires `SUPABASE_DB_URL`.

#### Storage

| Variable                  | Required\* | Default                    | Description                  |
| ------------------------- | ---------- | -------------------------- | ---------------------------- |
| `STORAGE_TYPE`            | No         | Profile-based              | `local` or `supabase`        |
| `UPLOAD_DIR`              | No         | `../data/videos/raw`       | Local storage directory      |
| `PROCESSED_DIR`           | No         | `../data/videos/processed` | Processed videos directory   |
| `SUPABASE_STORAGE_BUCKET` | Yes        | -                          | Supabase storage bucket name |

\*Required only when `PROFILE=production`

**Selection logic:**

- `PROFILE=local`: Uses `local` storage (ignores `SUPABASE_STORAGE_BUCKET`).
- `PROFILE=production`: Uses `supabase` storage (requires `SUPABASE_STORAGE_BUCKET`).

#### Supabase

| Variable                  | Required\* | Description                      |
| ------------------------- | ---------- | -------------------------------- |
| `SUPABASE_URL`            | Yes        | Supabase project URL             |
| `SUPABASE_SECRET_KEY`     | Yes        | Supabase service role secret key |
| `SUPABASE_STORAGE_BUCKET` | Yes        | Supabase storage bucket name     |

\*Required only when `PROFILE=production`

#### API

| Variable   | Default   | Description                                     |
| ---------- | --------- | ----------------------------------------------- |
| `API_HOST` | `0.0.0.0` | API server host                                 |
| `API_PORT` | `8000`    | API server port                                 |
| `DEBUG`    | `false`   | Enable debug mode (auto-reload + DEBUG logging) |

### Frontend

#### Core

| Variable            | Default                    | Description     |
| ------------------- | -------------------------- | --------------- |
| `REACT_APP_PROFILE` | `local`                    | Match backend   |
| `REACT_APP_API_URL` | `http://localhost:8000/v0` | Backend API URL |

#### Supabase

| Variable                             | Required\* | Description              |
| ------------------------------------ | ---------- | ------------------------ |
| `REACT_APP_SUPABASE_URL`             | Yes        | Supabase project URL     |
| `REACT_APP_SUPABASE_PUBLISHABLE_KEY` | Yes        | Supabase anon/public key |

\*Required only when `REACT_APP_PROFILE=production`

**Auth behavior:**

- `REACT_APP_PROFILE=local`: No login screen (ignores Supabase URLs).
- `REACT_APP_PROFILE=production`: Shows login screen (requires Supabase URLs).

---

## Configuration Examples

### Local Development

**Backend `.env`:**

```bash
PROFILE=local
# All Supabase variables ignored
```

**Frontend `.env`:**

```bash
REACT_APP_PROFILE=local
REACT_APP_API_URL=http://localhost:8000/v0
# All Supabase variables ignored
```

### Local Testing with Production Services

Use this when you want to test with Supabase services but run everything locally.

**Backend `.env`:**

```bash
PROFILE=production
SUPABASE_DB_URL=postgresql://user:password@host:5432/dbname
SUPABASE_URL=https://your-project.supabase.co
SUPABASE_SECRET_KEY=your-service-role-secret-key
SUPABASE_STORAGE_BUCKET=videos
```

**Frontend `.env`:**

```bash
REACT_APP_PROFILE=production
REACT_APP_API_URL=http://localhost:8000/v0  # Local backend
REACT_APP_SUPABASE_URL=https://your-project.supabase.co
REACT_APP_SUPABASE_PUBLISHABLE_KEY=your-anon-public-key
```

### Deployed Production

**Backend (deployment platform):**

```bash
PROFILE=production
SUPABASE_DB_URL=postgresql://user:password@host:5432/dbname
SUPABASE_URL=https://your-project.supabase.co
SUPABASE_SECRET_KEY=your-service-role-secret-key
SUPABASE_STORAGE_BUCKET=videos
```

**Frontend (deployment platform):**

```bash
REACT_APP_PROFILE=production
REACT_APP_API_URL=https://tennis-coach-api.fly.dev/v0  # Deployed backend (Fly.io)
REACT_APP_SUPABASE_URL=https://your-project.supabase.co
REACT_APP_SUPABASE_PUBLISHABLE_KEY=your-anon-public-key
```

---

## Implementation

### Backend Profile Logic

```python
from app.core.config import settings
import logging

logger = logging.getLogger(__name__)

PROFILE = settings.PROFILE  # local or production

# Determine storage type
if settings.STORAGE_TYPE is None:
    settings.STORAGE_TYPE = "local" if PROFILE == "local" else "supabase"
    logger.info(f"Profile '{PROFILE}': Using {settings.STORAGE_TYPE} storage")

# Determine database
if PROFILE == "local":
    if settings.DATABASE_URL:
        logger.info(f"Profile '{PROFILE}': Using DATABASE_URL for local Postgres")
    else:
        logger.info(f"Profile '{PROFILE}': Using SQLite (default)")
else:
    if not settings.SUPABASE_DB_URL:
        raise ValueError(f"SUPABASE_DB_URL required when PROFILE={PROFILE}")
    logger.info(f"Profile '{PROFILE}': Using Supabase database")

# Validate Supabase configuration
if settings.STORAGE_TYPE == "supabase":
    required_vars = {
        "SUPABASE_URL": settings.SUPABASE_URL,
        "SUPABASE_SECRET_KEY": settings.SUPABASE_SECRET_KEY,
        "SUPABASE_STORAGE_BUCKET": settings.SUPABASE_STORAGE_BUCKET,
    }
    for var_name, var_value in required_vars.items():
        if not var_value:
            raise ValueError(f"{var_name} required when STORAGE_TYPE=supabase")

# Determine auth requirement
auth_required = PROFILE != "local"
logger.info(f"Profile '{PROFILE}': Auth {'required' if auth_required else 'disabled'}")
```

### Frontend Profile Logic

```typescript
// supabaseClient.ts
const profile = process.env.REACT_APP_PROFILE || "local";
const supabaseUrl = process.env.REACT_APP_SUPABASE_URL || "";
const supabaseKey = process.env.REACT_APP_SUPABASE_PUBLISHABLE_KEY || "";

let supabase: SupabaseClient | null = null;

if (profile === "local") {
  console.log("Profile 'local': Auth disabled");
} else {
  if (!supabaseUrl || !supabaseKey) {
    throw new Error(
      `Supabase credentials required when REACT_APP_PROFILE=${profile}`
    );
  }
  supabase = createClient(supabaseUrl, supabaseKey);
}

export { supabase };

// App.tsx
const profile = process.env.REACT_APP_PROFILE || "local";
const { user, loading } = useAuth();

if (loading) {
  return <LoadingScreen />;
}

if (profile !== "local" && !user) {
  return <AuthForm />;
}

return <MainApp />;
```

---

## Troubleshooting

| Issue                       | Cause                                    | Solution                      |
| --------------------------- | ---------------------------------------- | ----------------------------- |
| Frontend shows login screen | `REACT_APP_PROFILE` not set to `local`   | Set `REACT_APP_PROFILE=local` |
| Backend requires auth       | `PROFILE` not set to `local`             | Set `PROFILE=local`           |
| Profile not working         | Incorrect profile value                  | Use `local` or `production`   |
| Supabase storage fails      | Missing `SUPABASE_STORAGE_BUCKET`        | Set bucket name in `.env`     |
| Storage type mismatch       | Switched profiles without migrating data | Migrate videos to new storage |

---

## Quick Reference

| Profile    | `PROFILE`    | Auth     | Frontend Profile               | Backend Location                  |
| ---------- | ------------ | -------- | ------------------------------ | --------------------------------- |
| Full Local | `local`      | Disabled | `REACT_APP_PROFILE=local`      | Local (`localhost:8000`)          |
| Production | `production` | Required | `REACT_APP_PROFILE=production` | Local or Deployed (via `API_URL`) |

---

## Notes

- **SQLite vs Postgres**: Start with SQLite for local dev. Use local Postgres only if you need Postgres-specific features (RLS, JSONB).
- **Local Auth**: Currently not implemented. `PROFILE=local` returns mock user. Future: implement local JWT/OAuth2.
- **Git Ignore**: Ensure `.env` files are in `.gitignore`.
- **Profile vs Deployment**: Remember that `PROFILE` controls **which services** to use, while `API_URL` controls **where the backend runs**. You can use `PROFILE=production` with a local backend for testing.
