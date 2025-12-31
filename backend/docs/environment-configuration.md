# Environment Configuration Guide

## Overview

This guide explains how to configure the application for different environments and testing scenarios. It covers both backend and frontend configuration, environment variable management, and recommended .env file structure.

## Table of Contents

1. [Environment Profiles](#environment-profiles)
2. [Configuration Strategy](#configuration-strategy)
3. [Environment Variables Reference](#environment-variables-reference)
4. [.env File Management](#env-file-management)
5. [Testing Scenarios](#testing-scenarios)
6. [Implementation Details](#implementation-details)
7. [Troubleshooting](#troubleshooting)

---

## Environment Profiles

The application supports three main environment profiles:

### 1. **Local Development (Full Local)**

- **Database**: SQLite (local file) OR Local PostgreSQL (optional, for production parity)
- **Storage**: Local filesystem
- **Auth**: None (disabled) OR Local Auth (FastAPI JWT/OAuth2 - future implementation)
- **Use Case**: Full local development, no external dependencies, fastest iteration
- **Frontend**: No login screen (if auth disabled) OR Local auth UI (if local auth implemented)

### 2. **Local with Production Services (Bundled)**

- **Database**: Supabase (production)
- **Storage**: Supabase Storage (production) - auto-detected
- **Auth**: Supabase Auth (production)
- **Use Case**: Test against production services while running locally
- **Frontend**: Shows login/signup screen, requires authentication

### 2b. **Local with Supabase Branch (Recommended for Postgres Testing)**

- **Database**: Supabase Branch (isolated test database)
- **Storage**: Supabase Storage (production) - auto-detected
- **Auth**: Supabase Auth (production)
- **Use Case**: Test with full Postgres parity in isolated environment, no local Postgres needed
- **Frontend**: Shows login/signup screen, requires authentication
- **Benefits**: Full Postgres features, isolated from production, easy to reset

### 3. **Local with Production DB + Local Storage (Mixed - Advanced)**

- **Database**: Supabase (production)
- **Storage**: Local filesystem - explicit override
- **Auth**: Supabase Auth (production)
- **Use Case**: Test with production data but avoid storage upload/download costs
- **Frontend**: Shows login/signup screen, requires authentication

### 4. **Production**

- **Database**: Supabase (production)
- **Storage**: Supabase Storage (production) - auto-detected
- **Auth**: Supabase Auth (production)
- **Use Case**: Deployed application (Render, Railway, etc.)
- **Frontend**: Shows login/signup screen, requires authentication

---

## Configuration Strategy

### Principle: Service Bundling (Default/Recommended)

**By default, services should be bundled together for consistency:**

- ✅ **Recommended**: All Supabase services together (DB + Storage + Auth)
- ✅ **Recommended**: All local services together (SQLite/Postgres + Local filesystem + Local Auth or None)
- ⚠️ **Advanced**: Mixed configurations (Supabase DB + Local Storage) - allowed but requires explicit configuration

**Note on Local Auth:**

- Currently, local development uses no auth (`REQUIRE_AUTH=false`)
- You can implement local auth (FastAPI JWT, OAuth2PasswordBearer, etc.) as a separate system
- This still fits service bundling: **Local services bundle = Local auth system**, **Supabase services bundle = Supabase auth**
- The key is keeping auth systems bundled with their service stack, not mixing auth systems

**Why bundling?**

- Consistent behavior across environments
- Easier to reason about (all cloud or all local)
- Prevents path/URL mismatches
- Simpler deployment (same config for all services)

### Auto-Detection Logic (Default Behavior)

The application automatically detects which services to use based on environment variables:

1. **If `SUPABASE_DB_URL` is set AND `STORAGE_TYPE` is NOT explicitly set** → Use Supabase for DB, Storage, and Auth
2. **If `SUPABASE_DB_URL` is NOT set** → Use local SQLite, local storage, optional auth

**This prevents accidental mixing** - if you set Supabase DB, storage defaults to Supabase too.

### Explicit Override (Advanced)

**You can explicitly override storage type** by setting `STORAGE_TYPE` in your `.env`:

```bash
# Explicitly use local storage even with Supabase DB
SUPABASE_DB_URL=postgresql://...
STORAGE_TYPE=local  # Explicit override
```

**When is mixing useful?**

- **Development testing**: Use production DB with real data, but local storage for faster iteration
- **Cost optimization**: Cloud DB for persistence, local storage during development
- **Gradual migration**: Migrate DB first, storage later

**When is mixing problematic?**

- **Production deployments**: Should use consistent services
- **Path mismatches**: Supabase storage uses `raw/filename.mp4`, local uses full paths
- **Data sync issues**: Videos in local storage won't be accessible if you switch to Supabase storage
- **Auth system conflicts**: Mixing auth systems (local JWT + Supabase tokens) causes confusion

### Local Auth Implementation (Future)

**Current State**: Local development = No auth (mock user returned)

**Future Option**: Implement local auth system for local development:

- Use FastAPI's `OAuth2PasswordBearer` or JWT tokens
- Store users in local SQLite/Postgres database
- Separate from Supabase auth system
- Still follows service bundling: Local services = Local auth

**Why this makes sense:**

- Test auth flows locally without Supabase
- Faster iteration (no external auth service)
- Still bundled: Local stack uses local auth, Supabase stack uses Supabase auth
- Can test auth logic without hitting production Supabase

**Implementation approach:**

- Create `app/utils/local_auth.py` for JWT/OAuth2 handling
- Update `get_current_user` to detect auth system based on config
- If `REQUIRE_AUTH=true` and no Supabase keys → Use local auth
- If `REQUIRE_AUTH=true` and Supabase keys set → Use Supabase auth

### ENVIRONMENT Variable Purpose

The `ENVIRONMENT` variable serves two purposes:

1. **Auth Bypass**: When `ENVIRONMENT=development` and `REQUIRE_AUTH=false`, backend skips authentication
2. **Deployment Context**: Indicates deployment environment (development vs production)

**Important**: `ENVIRONMENT` does NOT control:

- Database selection (controlled by `SUPABASE_DB_URL`)
- Storage selection (controlled by `STORAGE_TYPE` or auto-detection)
- Service selection (controlled by Supabase keys)

**Future uses** (not currently implemented):

- Logging levels (DEBUG in dev, INFO in prod)
- Error handling (show stack traces in dev)
- CORS settings (more permissive in dev)
- Performance monitoring (disable in dev)

---

## Environment Variables Reference

### Backend Environment Variables

#### Core Configuration

| Variable       | Required | Default       | Description                                                              |
| -------------- | -------- | ------------- | ------------------------------------------------------------------------ |
| `ENVIRONMENT`  | No       | `development` | Deployment environment: `development` or `production`                    |
| `REQUIRE_AUTH` | No       | `true`        | Enable/disable authentication. Set to `false` for local dev without auth |
| `LOG_LEVEL`    | No       | `INFO`        | Logging level: `DEBUG`, `INFO`, `WARNING`, `ERROR`, `CRITICAL`           |

#### Database Configuration

| Variable          | Required | Default | Description                                                        |
| ----------------- | -------- | ------- | ------------------------------------------------------------------ |
| `SUPABASE_DB_URL` | No       | -       | PostgreSQL connection string for Supabase. If not set, uses SQLite |
| `DATABASE_URL`    | No       | -       | Alternative database URL (overrides SQLite if set)                 |

**Database Selection Logic:**

1. If `SUPABASE_DB_URL` is set → Use Supabase PostgreSQL
2. Else if `DATABASE_URL` is set → Use specified database (can be local Postgres)
3. Else → Use SQLite at `../data/database/tennis_coach.db`

**SQLite vs Local PostgreSQL:**

**SQLite (Default for Local):**

- ✅ **Pros**: No setup, zero configuration, fast for small datasets, perfect for hobby projects
- ❌ **Cons**: Different SQL dialect, missing Postgres features (RLS, JSONB, certain functions)
- **Use when**: Simple CRUD operations, no Postgres-specific features needed

**Local PostgreSQL (Optional):**

- ✅ **Pros**: Full parity with production, test Postgres-specific features (RLS, JSONB, etc.)
- ❌ **Cons**: Requires installation, more setup, more resource usage
- **Use when**: You need to test Postgres-specific features, want full production parity

**Recommendation for Hobby Projects:**

- **Start with SQLite** - It's fine for 90% of use cases
- **For Postgres testing**: Use **Supabase Branching** (recommended) - Isolated test database, full parity, no local installation
- **Alternative**: Switch to local Postgres only if you need Postgres-specific features and can't use Supabase branches
- **Not recommended**: Test against production Supabase DB (risky, could affect production data)

#### Storage Configuration

| Variable                  | Required | Default                    | Description                                                                              |
| ------------------------- | -------- | -------------------------- | ---------------------------------------------------------------------------------------- |
| `STORAGE_TYPE`            | No       | Auto-detected              | Storage backend: `local` or `supabase`. If not set, auto-detected from `SUPABASE_DB_URL` |
| `UPLOAD_DIR`              | No       | `../data/videos/raw`       | Local storage directory for raw videos                                                   |
| `PROCESSED_DIR`           | No       | `../data/videos/processed` | Local storage directory for processed videos                                             |
| `SUPABASE_STORAGE_BUCKET` | Yes\*    | -                          | Supabase storage bucket name (required if `STORAGE_TYPE=supabase`)                       |

**Storage Selection Logic:**

1. If `STORAGE_TYPE` is explicitly set → Use specified storage type
2. Else if `SUPABASE_DB_URL` is set → Auto-detect as `supabase`
3. Else → Auto-detect as `local`

#### Supabase Configuration

| Variable                  | Required | Default | Description                                                           |
| ------------------------- | -------- | ------- | --------------------------------------------------------------------- |
| `SUPABASE_URL`            | Yes\*    | -       | Supabase project URL (required for Supabase storage/auth)             |
| `SUPABASE_SECRET_KEY`     | Yes\*    | -       | Supabase service role secret key (required for Supabase storage/auth) |
| `SUPABASE_STORAGE_BUCKET` | Yes\*    | -       | Supabase storage bucket name (required if using Supabase storage)     |

\*Required only when using Supabase services (storage or auth)

#### API Configuration

| Variable   | Required | Default   | Description       |
| ---------- | -------- | --------- | ----------------- |
| `API_HOST` | No       | `0.0.0.0` | API server host   |
| `API_PORT` | No       | `8000`    | API server port   |
| `DEBUG`    | No       | `false`   | Enable debug mode |

### Frontend Environment Variables

#### Core Configuration

| Variable                 | Required | Default                    | Description                                                           |
| ------------------------ | -------- | -------------------------- | --------------------------------------------------------------------- |
| `REACT_APP_REQUIRE_AUTH` | No       | `true`                     | Enable/disable authentication UI. Set to `false` to skip login screen |
| `REACT_APP_API_URL`      | No       | `http://localhost:8000/v0` | Backend API URL                                                       |

#### Supabase Configuration

| Variable                             | Required | Default | Description                                         |
| ------------------------------------ | -------- | ------- | --------------------------------------------------- |
| `REACT_APP_SUPABASE_URL`             | Yes\*    | -       | Supabase project URL (required if auth enabled)     |
| `REACT_APP_SUPABASE_PUBLISHABLE_KEY` | Yes\*    | -       | Supabase anon/public key (required if auth enabled) |

\*Required only when `REACT_APP_REQUIRE_AUTH=true`

**Frontend Auth Behavior:**

- If `REACT_APP_REQUIRE_AUTH=false` → No login screen, direct access to app
- If `REACT_APP_REQUIRE_AUTH=true` → Shows login/signup screen, requires authentication
- If Supabase keys are missing and `REACT_APP_REQUIRE_AUTH=true` → Error (Supabase client fails to initialize)

---

## .env File Management

### Recommended .env File Structure

For a hobby project, we recommend using a single `.env` file that you update based on your testing scenario. However, you can also use multiple `.env` files if preferred.

#### Option 1: Single `.env` File (Recommended for Hobby Projects)

**Location**: `backend/.env` and `frontend/.env`

**Approach**: Update the `.env` file based on what you're testing:

- Comment/uncomment sections as needed
- Or use a simple script to switch between profiles

**Pros**: Simple, one file to manage
**Cons**: Need to manually switch between configurations

#### Option 2: Multiple .env Files (Advanced)

**Approach**: Create separate `.env` files for each scenario:

- `.env.development.local` - Full local
- `.env.development.prod-services` - Local app, prod services
- `.env.production` - Production

**Pros**: Easy to switch between scenarios
**Cons**: More files to manage, need to remember which one is active

**Note**: Most tools (like `dotenv`) only load `.env` by default. You'd need to manually specify which file to load.

### Recommended Files to Keep/Delete

#### Current .env Files Found:

Based on your current setup, you have:

- `backend/.env` - **Keep** (your active backend configuration)
- `backend/.env.production` - **Review** (only keep if you use it for deployment)
- `frontend/.env` - **Keep** (your active frontend configuration)

#### Keep These Files:

1. **`backend/.env`** - Your active backend configuration
2. **`frontend/.env`** - Your active frontend configuration

#### Review/Delete These:

1. **`backend/.env.production`** - Only keep if you're actively using it for deployment. If not, delete it or merge useful values into `.env`
2. **Any other `.env.*` files** - Review and delete if not actively used

#### Recommended Action:

1. **Review `backend/.env.production`**:
   - If it has production values you need → Keep it (but don't commit)
   - If it's outdated or unused → Delete it
2. **Consolidate into main `.env` files**:
   - Use `backend/.env` for your current testing scenario
   - Use `frontend/.env` for your current frontend configuration
   - Update these files based on which scenario you're testing (see Testing Scenarios section)

#### Git Ignore

Make sure `.env` files are in `.gitignore`:

```
# Environment variables
.env
.env.local
.env.development
.env.production
.env.*.local
```

---

## Testing Scenarios

### Scenario 1: Test Locally (Full Local)

**Goal**: Test without any external dependencies, fastest iteration

**Option 1a: SQLite (Default - Recommended for Hobby Projects)**

**Backend `.env`** (`backend/.env`):

```bash
# Environment
ENVIRONMENT=development
REQUIRE_AUTH=false

# Database - Local SQLite (auto-selected when SUPABASE_DB_URL is not set)
# No SUPABASE_DB_URL = uses SQLite

# Storage - Local filesystem (auto-detected)
# No STORAGE_TYPE = auto-detects as "local"

# Auth - Disabled
# No SUPABASE_URL = auth disabled
```

**Option 1b: Local PostgreSQL (For Production Parity)**

**Backend `.env`** (`backend/.env`):

```bash
# Environment
ENVIRONMENT=development
REQUIRE_AUTH=false

# Database - Local PostgreSQL (explicit override)
DATABASE_URL=postgresql://user:password@localhost:5432/tennis_coach_local

# Storage - Local filesystem (auto-detected)
# No STORAGE_TYPE = auto-detects as "local"

# Auth - Disabled
# No SUPABASE_URL = auth disabled
```

**Note**: To use local Postgres, you need to:

1. Install PostgreSQL locally (`brew install postgresql` on macOS)
2. Create database: `createdb tennis_coach_local`
3. Run migrations: `alembic upgrade head`

**Frontend `.env`** (`frontend/.env`):

```bash
# Auth - Disabled
REACT_APP_REQUIRE_AUTH=false

# API
REACT_APP_API_URL=http://localhost:8000/v0

# Supabase - Not needed (auth disabled)
# No REACT_APP_SUPABASE_URL = auth UI disabled
```

**Result**:

- SQLite DB, local storage, no auth
- Frontend: No login screen, direct access
- Backend: Accepts requests without auth tokens

---

### Scenario 2a: Test Locally with Prod Services (Bundled)

**Goal**: Test against production services while running locally

**Backend `.env`** (`backend/.env`):

```bash
# Environment
ENVIRONMENT=development
REQUIRE_AUTH=true

# Database - Supabase Production
SUPABASE_DB_URL=postgresql://user:password@host:5432/dbname

# Storage - Supabase Production (auto-detected from SUPABASE_DB_URL)
# Don't set STORAGE_TYPE - it will auto-detect as "supabase"

# Auth - Supabase Production
SUPABASE_URL=https://your-project.supabase.co
SUPABASE_SECRET_KEY=your-service-role-secret-key
SUPABASE_STORAGE_BUCKET=videos
```

**Frontend `.env`** (`frontend/.env`):

```bash
# Auth - Enabled
REACT_APP_REQUIRE_AUTH=true

# API
REACT_APP_API_URL=http://localhost:8000/v0

# Supabase - Required for auth
REACT_APP_SUPABASE_URL=https://your-project.supabase.co
REACT_APP_SUPABASE_PUBLISHABLE_KEY=your-anon-public-key
```

**Result**:

- Supabase DB, Supabase Storage, Supabase Auth
- Frontend: Shows login/signup screen
- Backend: Requires auth tokens

### Scenario 2b: Test Locally with Supabase Branch (Recommended for Postgres Testing)

**Goal**: Test with full Postgres parity in isolated environment

**Setup**:

1. Create Supabase branch: `supabase branch create dev-test` (via Supabase CLI or dashboard)
2. Get branch connection string from Supabase dashboard

**Backend `.env`** (`backend/.env`):

```bash
# Environment
ENVIRONMENT=development
REQUIRE_AUTH=true

# Database - Supabase Branch (isolated test database)
SUPABASE_DB_URL=postgresql://user:password@host:5432/branch-dbname

# Storage - Supabase Production (auto-detected)
# Don't set STORAGE_TYPE - it will auto-detect as "supabase"

# Auth - Supabase Production (shared across branches)
SUPABASE_URL=https://your-project.supabase.co
SUPABASE_SECRET_KEY=your-service-role-secret-key
SUPABASE_STORAGE_BUCKET=videos
```

**Frontend `.env`** (`frontend/.env`):

```bash
# Auth - Enabled
REACT_APP_REQUIRE_AUTH=true

# API
REACT_APP_API_URL=http://localhost:8000/v0

# Supabase - Required for auth
REACT_APP_SUPABASE_URL=https://your-project.supabase.co
REACT_APP_SUPABASE_PUBLISHABLE_KEY=your-anon-public-key
```

**Result**:

- Supabase Branch DB (isolated), Supabase Storage, Supabase Auth
- Frontend: Shows login/signup screen
- Backend: Requires auth tokens
- **Benefits**: Full Postgres features, safe testing, easy to reset

**Cleanup**: Delete branch when done: `supabase branch delete dev-test`

---

### Scenario 2b: Test Locally with Prod DB + Local Storage (Mixed - Advanced)

**Goal**: Test with production data but avoid storage upload/download costs

**Backend `.env`** (`backend/.env`):

```bash
# Environment
ENVIRONMENT=development
REQUIRE_AUTH=true

# Database - Supabase Production
SUPABASE_DB_URL=postgresql://user:password@host:5432/dbname

# Storage - Local (explicit override)
STORAGE_TYPE=local  # Explicitly override auto-detection

# Auth - Supabase Production
SUPABASE_URL=https://your-project.supabase.co
SUPABASE_SECRET_KEY=your-service-role-secret-key
```

**Frontend `.env`** (`frontend/.env`):

```bash
# Auth - Enabled
REACT_APP_REQUIRE_AUTH=true

# API
REACT_APP_API_URL=http://localhost:8000/v0

# Supabase - Required for auth
REACT_APP_SUPABASE_URL=https://your-project.supabase.co
REACT_APP_SUPABASE_PUBLISHABLE_KEY=your-anon-public-key
```

**Result**:

- Supabase DB, Local Storage, Supabase Auth
- Frontend: Shows login/signup screen
- Backend: Requires auth tokens
- **Warning**: Videos stored locally won't be accessible if you switch to Supabase storage

---

### Scenario 3: Production Deployment

**Goal**: Deploy to production (Render, Railway, etc.)

**Backend Environment Variables** (set in deployment platform):

```bash
# Environment
ENVIRONMENT=production
REQUIRE_AUTH=true

# Database - Supabase Production
SUPABASE_DB_URL=postgresql://user:password@host:5432/dbname

# Storage - Supabase Production (auto-detected)
# Don't set STORAGE_TYPE - it will auto-detect as "supabase"

# Auth - Supabase Production
SUPABASE_URL=https://your-project.supabase.co
SUPABASE_SECRET_KEY=your-service-role-secret-key
SUPABASE_STORAGE_BUCKET=videos
```

**Frontend Environment Variables** (set in deployment platform):

```bash
# Auth - Enabled
REACT_APP_REQUIRE_AUTH=true

# API - Your production API URL
REACT_APP_API_URL=https://your-api.render.com/v0

# Supabase - Required for auth
REACT_APP_SUPABASE_URL=https://your-project.supabase.co
REACT_APP_SUPABASE_PUBLISHABLE_KEY=your-anon-public-key
```

**Result**:

- Supabase DB, Supabase Storage, Supabase Auth
- Frontend: Shows login/signup screen
- Backend: Requires auth tokens

---

## Implementation Details

### Backend Auto-Detection Logic

The backend should implement the following logic in `config.py`:

```python
# Auto-detect storage type if not explicitly set
if settings.STORAGE_TYPE is None:
    if settings.SUPABASE_DB_URL:
        # Default to Supabase storage when using Supabase DB
        settings.STORAGE_TYPE = "supabase"
        logger.info("Auto-detected storage type: supabase (Supabase DB detected)")
    else:
        # Default to local storage when using SQLite
        settings.STORAGE_TYPE = "local"
        logger.info("Auto-detected storage type: local (SQLite DB detected)")
else:
    logger.info(f"Using explicitly set storage type: {settings.STORAGE_TYPE}")

# Validate Supabase configuration if using Supabase services
if settings.STORAGE_TYPE == "supabase":
    if not settings.SUPABASE_URL:
        raise ValueError("SUPABASE_URL required when STORAGE_TYPE=supabase")
    if not settings.SUPABASE_SECRET_KEY:
        raise ValueError("SUPABASE_SECRET_KEY required when STORAGE_TYPE=supabase")
    if not settings.SUPABASE_STORAGE_BUCKET:
        raise ValueError("SUPABASE_STORAGE_BUCKET required when STORAGE_TYPE=supabase")

# Warn if mixing services (Supabase DB + Local Storage)
if settings.SUPABASE_DB_URL and settings.STORAGE_TYPE == "local":
    logger.warning(
        "⚠️  Mixed configuration detected: Supabase DB with Local Storage. "
        "This is allowed but may cause path/data sync issues."
    )
```

### Frontend Auth Behavior

The frontend should implement the following logic:

```typescript
// In supabaseClient.ts - Make Supabase client optional
const requireAuth = process.env.REACT_APP_REQUIRE_AUTH !== "false";
const supabaseUrl = process.env.REACT_APP_SUPABASE_URL || "";
const supabaseKey = process.env.REACT_APP_SUPABASE_PUBLISHABLE_KEY || "";

let supabase: SupabaseClient | null = null;

if (requireAuth) {
  if (!supabaseUrl || !supabaseKey) {
    throw new Error("Supabase credentials required when auth is enabled");
  }
  supabase = createClient(supabaseUrl, supabaseKey);
} else {
  // Auth disabled - no Supabase client needed
  console.log("Auth disabled - Supabase client not initialized");
}

export { supabase };

// In App.tsx - Skip auth UI if disabled
const { user, loading } = useAuth();
const requireAuth = process.env.REACT_APP_REQUIRE_AUTH !== "false";

if (loading) {
  return <LoadingScreen />;
}

if (requireAuth && !user) {
  return <AuthForm />;
}

// User is authenticated or auth is disabled - show app
return <MainApp />;
```

**Key Points:**

- Auto-detection only applies if `STORAGE_TYPE` is not explicitly set
- Explicit `STORAGE_TYPE` setting overrides auto-detection
- This allows intentional mixing while preventing accidental mixing
- Frontend respects `REACT_APP_REQUIRE_AUTH` to show/hide auth UI

---

## Troubleshooting

### Issue: "Storage type mismatch"

**Symptom**: Videos saved locally but trying to access from Supabase storage (or vice versa)

**Cause**: Mixed configuration or switched storage types without migrating data

**Solution**:

- Use consistent storage type for your environment
- If switching, migrate existing videos to new storage
- Or use explicit `STORAGE_TYPE` override if intentional mixing

### Issue: "Frontend shows login screen even with REQUIRE_AUTH=false"

**Cause**: Frontend `REACT_APP_REQUIRE_AUTH` not set to `false`

**Solution**: Set `REACT_APP_REQUIRE_AUTH=false` in `frontend/.env`

### Issue: "Backend requires auth even with REQUIRE_AUTH=false"

**Cause**: `ENVIRONMENT` not set to `development` or `REQUIRE_AUTH` not set correctly

**Solution**: Check both `ENVIRONMENT=development` and `REQUIRE_AUTH=false` in `backend/.env`

### Issue: "Auto-detection not working"

**Cause**: `STORAGE_TYPE` is explicitly set, preventing auto-detection

**Solution**: Remove `STORAGE_TYPE` from `.env` to enable auto-detection, or set it explicitly if you want to override

### Issue: "Supabase storage fails but DB works"

**Cause**: Missing `SUPABASE_STORAGE_BUCKET` or incorrect bucket name

**Solution**: Set `SUPABASE_STORAGE_BUCKET` in `.env` and ensure bucket exists in Supabase dashboard

---

## Quick Reference

### Environment Profile Selection

| Profile                       | `SUPABASE_DB_URL` | `STORAGE_TYPE`             | `REQUIRE_AUTH` | `REACT_APP_REQUIRE_AUTH` |
| ----------------------------- | ----------------- | -------------------------- | -------------- | ------------------------ |
| Full Local                    | Not set           | Not set (auto: `local`)    | `false`        | `false`                  |
| Prod Services (Bundled)       | Set (production)  | Not set (auto: `supabase`) | `true`         | `true`                   |
| Supabase Branch (Recommended) | Set (branch)      | Not set (auto: `supabase`) | `true`         | `true`                   |
| Mixed (Advanced)              | Set               | `local` (explicit)         | `true`         | `true`                   |
| Production                    | Set (production)  | Not set (auto: `supabase`) | `true`         | `true`                   |

### Service Selection Matrix

| Database          | Storage  | Auth          | Configuration                                           |
| ----------------- | -------- | ------------- | ------------------------------------------------------- |
| SQLite            | Local    | Disabled      | No Supabase keys, `REQUIRE_AUTH=false`                  |
| SQLite            | Local    | Local Auth\*  | No `SUPABASE_DB_URL`, implement local JWT/OAuth2        |
| Local Postgres    | Local    | Disabled      | `DATABASE_URL=postgresql://...`, `REQUIRE_AUTH=false`   |
| Local Postgres    | Local    | Local Auth\*  | `DATABASE_URL=postgresql://...`, implement local auth   |
| Supabase (Prod)   | Supabase | Supabase Auth | Set `SUPABASE_DB_URL` (production), auto-detect storage |
| Supabase (Branch) | Supabase | Supabase Auth | Set `SUPABASE_DB_URL` (branch), auto-detect storage     |
| Supabase          | Local    | Supabase Auth | Set `SUPABASE_DB_URL`, `STORAGE_TYPE=local`             |

\*Local Auth not yet implemented - currently local = no auth

---

## Benefits

- ✅ **Consistency**: Services are bundled by default
- ✅ **Simplicity**: Less configuration needed (auto-detection)
- ✅ **Safety**: Can't accidentally mix services (auto-detection prevents it)
- ✅ **Flexibility**: Explicit overrides allow intentional mixing when needed
- ✅ **Clarity**: Clear environment profiles with sensible defaults
- ✅ **Developer Experience**: Fast local dev with no auth, easy switch to prod services

---

## Summary & Recommendations

### For Your Current Setup

Based on your current files (`backend/.env`, `backend/.env.production`, `frontend/.env`):

1. **Keep `backend/.env`** - Update it based on your testing scenario
2. **Review `backend/.env.production`** - Delete if unused, or keep for deployment reference
3. **Keep `frontend/.env`** - Update it to match your backend auth settings

### Database Parity Decision

**Question**: Should you use SQLite locally or install local PostgreSQL?

**Recommendation for Hobby Projects:**

1. **Start with SQLite** (current setup)

   - ✅ Zero setup, works immediately
   - ✅ Fine for 90% of use cases (CRUD, basic queries)
   - ✅ Fast iteration, no database server needed
   - ⚠️ Different from production Postgres, but usually fine

2. **For Postgres testing: Use Supabase Branching (Recommended)**

   - Create isolated Supabase branch for testing
   - Full Postgres parity without local installation
   - Safe testing (isolated from production)
   - Easy to reset (delete/recreate branch)
   - Use Scenario 2b configuration

3. **Alternative: Install local Postgres IF:**
   - You can't use Supabase branches
   - You need offline Postgres testing
   - You want to test without internet connection

**Bottom Line**: SQLite is fine for most hobby projects. Only add local Postgres if you specifically need Postgres features.

**Direct Answer to Your Question**:

**Q: Should I install local Postgres to fully test, or is SQLite fine?**

**A: Start with SQLite, add local Postgres only if needed**

**Reasons to stick with SQLite:**

- ✅ Zero setup - works immediately
- ✅ Fine for 90% of use cases (your current app likely fits here)
- ✅ Faster iteration (no database server to manage)
- ✅ Less resource usage
- ✅ For hobby projects, SQLite is perfectly acceptable

**Reasons to add local Postgres:**

- You're using Postgres-specific features (RLS, JSONB, advanced JSON queries, etc.)
- You want exact production parity for testing
- You're testing complex queries that behave differently in SQLite vs Postgres
- You plan to use Postgres features in the future

**Alternative (Recommended for Hobby Projects):**

- **Use Supabase Branching** (Scenario 2b) - Isolated test database with full Postgres features
- No local Postgres installation needed
- Safe testing (isolated from production)
- Easy to reset (delete/recreate branch)
- Full parity with production Postgres
- **Best option for testing Postgres-specific features** (JSONB, RLS, etc.)

### Local Auth Implementation

**Current State**: Local = No auth (mock user)

**Future Option**: Implement local auth system:

- FastAPI JWT or OAuth2PasswordBearer
- Store users in local database
- Separate from Supabase auth
- Still follows service bundling principle

**When to implement:**

- If you want to test auth flows without Supabase
- If you want faster auth iteration locally
- If you plan to support multiple auth providers

**For now**: No auth locally is fine for development. You can always add local auth later.

**Key Point**: Implementing local auth (FastAPI JWT/OAuth2) is **totally valid** and still follows service bundling:

- ✅ **Local services bundle** = SQLite/Postgres + Local storage + **Local auth system**
- ✅ **Supabase services bundle** = Supabase DB + Supabase storage + **Supabase auth system**
- ❌ **Don't mix**: Local DB + Supabase auth (confusing, different token systems)

The bundling principle is about keeping auth systems consistent with their service stack, not about using the same auth system everywhere.

### Quick Start Recommendations

**For Local Development (No Auth):**

```bash
# backend/.env
ENVIRONMENT=development
REQUIRE_AUTH=false
# No Supabase keys = SQLite + Local storage

# frontend/.env
REACT_APP_REQUIRE_AUTH=false
REACT_APP_API_URL=http://localhost:8000/v0
```

**For Testing with Production Services:**

```bash
# backend/.env
ENVIRONMENT=development
REQUIRE_AUTH=true
SUPABASE_DB_URL=postgresql://...
SUPABASE_URL=https://...
SUPABASE_SECRET_KEY=...
SUPABASE_STORAGE_BUCKET=videos
# Don't set STORAGE_TYPE - auto-detects as "supabase"

# frontend/.env
REACT_APP_REQUIRE_AUTH=true
REACT_APP_API_URL=http://localhost:8000/v0
REACT_APP_SUPABASE_URL=https://...
REACT_APP_SUPABASE_PUBLISHABLE_KEY=...
```

### Next Steps

1. ✅ **Review this documentation** - Confirm it matches your needs
2. ⏳ **Implement auto-detection** - Add logic to `config.py` (after your approval)
3. ⏳ **Update frontend auth** - Make Supabase client optional based on `REACT_APP_REQUIRE_AUTH`
4. ⏳ **Test scenarios** - Verify each configuration works as expected

---

**Last Updated**: 2024-12-29  
**Status**: Documentation Complete - Ready for Implementation Review
