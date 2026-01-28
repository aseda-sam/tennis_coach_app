# Testing Cascade Delete Trigger

## Overview

The cascade delete trigger (`e2e9e9d5b092_add_cascade_delete_trigger_for_auth_.py`) automatically deletes user data when a user is deleted from Supabase's `auth.users` table.

## What Gets Deleted

When a user is deleted from `auth.users`, the trigger deletes:

1. **Videos** (which automatically cascade to):
   - `serve_attempts` (via foreign key `ondelete="CASCADE"`)
   - `pose_detections` (via foreign key `ondelete="CASCADE"`)
   - `video_jobs` (via foreign key `ondelete="CASCADE"`)

2. **Players** (which automatically cascade to):
   - `serve_attempts` (via foreign key `ondelete="CASCADE"`)

**Note**: Only `videos` and `players` need explicit deletion in the trigger. All other tables cascade automatically via foreign key constraints.

## Running the Migration

### Production (Supabase)

1. **Check current migration status**:

   ```bash
   # If running migrations via Fly.io or your deployment platform
   # Check the migration status in your deployment logs

   # Or connect to Supabase directly and check:
   # SELECT * FROM alembic_version;
   ```

2. **Run the migration**:

   ```bash
   # Via Fly.io (if configured)
   fly ssh console -a tennis-coach-api
   cd /app
   alembic upgrade head

   # Or via Supabase SQL Editor (run the migration SQL manually)
   # Copy the SQL from the migration file's upgrade() function
   ```

3. **Verify the trigger was created**:
   ```sql
   -- In Supabase SQL Editor
   SELECT
       trigger_name,
       event_manipulation,
       event_object_table,
       action_statement
   FROM information_schema.triggers
   WHERE trigger_name = 'on_auth_user_deleted';
   ```

### Local Development

**Note**: The trigger only works in Supabase where `auth.users` exists. In local dev with `PROFILE=local`, the trigger won't be created (by design - the migration checks for `auth.users` existence).

1. **Run migration** (for testing purposes):

   ```bash
   cd backend
   alembic upgrade head
   ```

2. **Verify trigger was NOT created** (expected in local dev):
   ```sql
   -- Should return 0 rows since auth.users doesn't exist locally
   SELECT * FROM information_schema.triggers
   WHERE trigger_name = 'on_auth_user_deleted';
   ```

## Testing the Trigger

### Prerequisites

- A Supabase project with the migration applied
- A test user account (create via Supabase Auth UI or API)
- Some test data for that user (videos, players, serve attempts, etc.)

### Test Steps

1. **Create test data**:
   - Sign up/login as test user
   - Upload a video
   - Create a player
   - Create some serve attempts
   - Verify data exists:
     ```sql
     -- Replace 'test-user-id' with actual user ID
     SELECT COUNT(*) FROM videos WHERE user_id = 'test-user-id';
     SELECT COUNT(*) FROM players WHERE user_id = 'test-user-id';
     SELECT COUNT(*) FROM serve_attempts WHERE user_id = 'test-user-id';
     ```

2. **Delete the user from Supabase Auth**:
   - Go to Supabase Dashboard → Authentication → Users
   - Find your test user
   - Click "Delete user" (or use SQL: `DELETE FROM auth.users WHERE id = 'test-user-id';`)

3. **Verify cascade deletion**:
   ```sql
   -- Should return 0 rows for all queries
   SELECT COUNT(*) FROM videos WHERE user_id = 'test-user-id';
   SELECT COUNT(*) FROM players WHERE user_id = 'test-user-id';
   SELECT COUNT(*) FROM serve_attempts WHERE user_id = 'test-user-id';
   SELECT COUNT(*) FROM video_jobs WHERE user_id = 'test-user-id';
   SELECT COUNT(*) FROM pose_detections
   WHERE video_id IN (SELECT id FROM videos WHERE user_id = 'test-user-id');
   ```

### Testing via API (Alternative)

If you have admin access, you can also test using the cleanup endpoint:

1. **Create orphaned data** (manually delete user from Supabase Auth, but data remains):

   ```sql
   -- Delete user but leave data (simulates orphaned state)
   DELETE FROM auth.users WHERE id = 'test-user-id';
   ```

2. **Check for orphaned data**:

   ```bash
   curl -X GET "https://your-api.com/v0/admin/cleanup/orphaned-data/check" \
     -H "Authorization: Bearer YOUR_ADMIN_TOKEN"
   ```

3. **Clean up orphaned data** (dry run first):
   ```bash
   curl -X POST "https://your-api.com/v0/admin/cleanup/orphaned-data?dry_run=true" \
     -H "Authorization: Bearer YOUR_ADMIN_TOKEN"
   ```

## Troubleshooting

### Trigger Not Created

**Symptom**: No trigger exists after running migration

**Possible causes**:

- Migration didn't run successfully
- `auth.users` table doesn't exist (local dev scenario - this is expected)
- Migration was run but failed silently

**Solution**:

```sql
-- Check if migration was applied
SELECT * FROM alembic_version;

-- Check if auth.users exists
SELECT EXISTS (
    SELECT FROM information_schema.tables
    WHERE table_schema = 'auth'
    AND table_name = 'users'
);

-- Manually create trigger if needed (copy SQL from migration file)
```

### Data Not Deleted

**Symptom**: User deleted but data remains

**Possible causes**:

- Trigger not created
- Trigger function has an error
- Foreign key constraints missing

**Solution**:

```sql
-- Check if trigger exists
SELECT * FROM information_schema.triggers
WHERE trigger_name = 'on_auth_user_deleted';

-- Test trigger function manually
SELECT handle_auth_user_deleted();

-- Check foreign key constraints
SELECT
    tc.table_name,
    kcu.column_name,
    ccu.table_name AS foreign_table_name,
    ccu.column_name AS foreign_column_name,
    rc.delete_rule
FROM information_schema.table_constraints AS tc
JOIN information_schema.key_column_usage AS kcu
    ON tc.constraint_name = kcu.constraint_name
JOIN information_schema.constraint_column_usage AS ccu
    ON ccu.constraint_name = tc.constraint_name
JOIN information_schema.referential_constraints AS rc
    ON rc.constraint_name = tc.constraint_name
WHERE tc.constraint_type = 'FOREIGN KEY'
    AND tc.table_name IN ('serve_attempts', 'video_jobs', 'pose_detections');
```

## Rollback

If you need to rollback the migration:

```bash
# Via Alembic
alembic downgrade -1

# Or manually via SQL
DROP TRIGGER IF EXISTS on_auth_user_deleted ON auth.users;
DROP FUNCTION IF EXISTS handle_auth_user_deleted();
```

## Related Documentation

- [Database Migrations](../README.md#database-operations)
- [Cleanup Service](../../app/services/cleanup_service.py)
- [Admin API Routes](../../app/api/routes/admin.py)
