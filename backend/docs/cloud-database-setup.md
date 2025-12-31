# Cloud Database Setup (PostgreSQL)

## Overview

This guide walks you through setting up and testing a cloud PostgreSQL database locally. The app supports both local SQLite (development) and cloud PostgreSQL (production).

## Step-by-Step Guide

### Step 1: Get Database Connection String

1. Go to your cloud database provider's dashboard
2. Navigate to **Database Settings** or **Connection Info**
3. Find the **Connection string** or **URI**
4. Copy the PostgreSQL connection string

**Connection string format:**

```
postgresql://[USERNAME]:[PASSWORD]@[HOST]:[PORT]/[DATABASE]
```

**Example:**

```
postgresql://postgres:your-password@db.example.com:5432/postgres
```

**Important:**

- Replace `[PASSWORD]` with your actual database password
- If password contains special characters (`@`, `#`, `%`, etc.), URL-encode them:
  - `@` → `%40`
  - `#` → `%23`
  - `%` → `%25`

### Step 2: Update Your `.env` File

Open `backend/.env` and add:

```bash
# Cloud Database Connection (PostgreSQL)
SUPABASE_DB_URL=postgresql://postgres:your-password@db.example.com:5432/postgres

# Or use DATABASE_URL directly
# DATABASE_URL=postgresql://postgres:your-password@db.example.com:5432/postgres
```

**Note:** The config will use `SUPABASE_DB_URL` if set, otherwise falls back to `DATABASE_URL` or SQLite.

### Step 3: Run Database Migrations

The cloud database is empty, so you need to create the tables using Alembic migrations:

```bash
cd backend

# Check current migration status (will show nothing if database is empty)
alembic current

# Run all migrations to create all tables
alembic upgrade head
```

**What this does:**

- Creates all tables: `videos`, `players`, `video_players`, `ball_detections`, `pose_detections`, `ball_contacts`, `video_annotations`
- Sets up indexes and relationships
- Ready to use!

### Step 4: Verify Tables Were Created

**Option A: Check via Database Dashboard**

1. Go to your database provider's dashboard
2. Navigate to **Table Editor** or **Database Browser**
3. You should see all your tables listed

**Option B: Check via Python**

```bash
cd backend
python -c "
from app.core.database import engine
from sqlalchemy import inspect
inspector = inspect(engine)
tables = inspector.get_table_names()
print('Created tables:', sorted(tables))
"
```

### Step 5: Test Your Backend

```bash
cd backend
python -m uvicorn app.main:app --reload
```

**Test it:**

1. Upload a video via frontend
2. Check your database → `videos` table
3. You should see your video record!

### Step 6: Verify Everything Works

Try these operations:

- ✅ Upload video → Check `videos` table
- ✅ Create player → Check `players` table
- ✅ Run analysis → Check `ball_detections`, `pose_detections` tables
- ✅ Add ball contact → Check `ball_contacts` table

## What Gets Created

The migration creates these tables:

1. **videos** - Video metadata and file information
2. **players** - Player profiles
3. **video_players** - Many-to-many relationship between videos and players
4. **ball_detections** - Ball detection analysis results
5. **pose_detections** - Pose estimation analysis results
6. **ball_contacts** - Ball contact markers and events
7. **video_annotations** - Annotated video records

All with proper indexes, foreign keys, and relationships!

## Troubleshooting

### "password authentication failed"

- **Fix:** Verify password is correct and URL-encoded if it contains special characters
- **Check:** Connection string format matches provider's requirements

### "could not connect to server"

- **Fix:** Check connection string format
- **Verify:** Host, port, and database name are correct
- **Check:** IP restrictions or firewall settings

### "relation does not exist"

- **Fix:** Run migrations: `alembic upgrade head`
- **Check:** Verify database connection string is set correctly in `.env`

### "alembic: command not found"

- **Fix:** Install dependencies: `pip install -e .`
- **Or:** `pip install alembic`

### Migrations show "No current revision"

- **This is normal** for a fresh database
- Just run: `alembic upgrade head` to create everything

## Switching Back to SQLite

To use local SQLite again:

```bash
# In backend/.env
# Comment out or remove SUPABASE_DB_URL
# SUPABASE_DB_URL=...
```

Or set `DATABASE_URL` explicitly:

```bash
DATABASE_URL=sqlite:///../data/database/tennis_coach.db
```

## Production Deployment

For production, set these environment variables:

```bash
SUPABASE_DB_URL=postgresql://postgres:password@db.example.com:5432/postgres
PROFILE=production
```

The app will automatically use the cloud database when `SUPABASE_DB_URL` is set.

## Summary

1. ✅ Get connection string from your database provider
2. ✅ Add `SUPABASE_DB_URL` to `.env`
3. ✅ Run `alembic upgrade head` to create tables
4. ✅ Test your backend
5. ✅ Verify data in your database

**The database must be created and accessible before running migrations!**
