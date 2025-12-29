# User ID Migration Guide

## Overview

This guide explains the general process for migrating existing data to assign `user_id` to all records, then enforce `user_id` as NOT NULL.

## Migration Steps

### 1. Run Alembic Migration to Add Columns

**First, add the `user_id` columns to your tables:**

```bash
cd backend
alembic upgrade head
```

This will:
- Add `user_id` column to `videos` table (nullable)
- Add `user_id` column to `players` table (nullable)
- Attempt to make `user_id` NOT NULL (will fail if NULLs exist - that's OK)

**Note:** If the NOT NULL migration fails, that's expected. Continue to step 2.

### 2. Run SQL Script to Populate Existing Data

**After the columns exist, populate existing records:**

1. Open Supabase Dashboard → SQL Editor
2. Create a SQL script to assign `user_id` to existing records
3. Replace placeholder with your actual Supabase user UUID
4. Run the SQL script
5. Verify no NULL values remain:
   ```sql
   SELECT COUNT(*) as videos_with_null FROM videos WHERE user_id IS NULL;
   SELECT COUNT(*) as players_with_null FROM players WHERE user_id IS NULL;
   ```
   Both should return 0.

### 3. Complete NOT NULL Migration

**After populating data, complete the NOT NULL constraint:**

```bash
cd backend
alembic upgrade head
```

This will:
- Make `videos.user_id` NOT NULL
- Make `players.user_id` NOT NULL

### 4. Verify Application

- All new videos require authentication (already implemented)
- All new players require authentication (already implemented)
- No legacy NULL handling needed anymore

## Local Development

**Current State:** Local dev database (SQLite) may need migration.

**Options:**

### Option A: Migrate Local Dev Now

1. Run the SQL script against your local SQLite database
2. Or manually update records in local DB
3. Run `alembic upgrade head` locally

### Option B: Keep Local Dev Flexible (Recommended for now)

- Local dev can still have NULL `user_id` temporarily
- The NOT NULL constraint will be enforced in production
- When ready, migrate local dev the same way

**Note:** The application code now requires `user_id` for new records, so local dev will need auth enabled or you'll need to manually set `user_id` for testing.

## Rollback (if needed)

If you need to rollback:

```bash
# Rollback the NOT NULL migration
alembic downgrade -1

# The user_id columns will be nullable again
# Existing data will remain (user_id values won't be removed)
```

## Files Changed

- `backend/app/models/video.py` - `user_id` now NOT NULL
- `backend/app/models/player.py` - `user_id` now NOT NULL
- `backend/app/services/player_service.py` - `user_id` required parameter
- `backend/app/api/routes/players.py` - Requires authentication
- Migration files in `backend/alembic/versions/`
