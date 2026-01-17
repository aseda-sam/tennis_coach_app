-- Manual SQL script to apply demo-related migrations
-- Run this directly in Supabase SQL Editor (as database owner/service role)
-- This applies migrations 4212cb7567aa and d1f0ec4cf292

-- IMPORTANT: Run this as the database owner (not through PostgREST)
-- Go to Supabase Dashboard → SQL Editor → New Query → Paste this → Run

BEGIN;

-- Check current state
DO $$
DECLARE
    current_version TEXT;
BEGIN
    SELECT version_num INTO current_version FROM alembic_version;
    RAISE NOTICE 'Current alembic version: %', current_version;
    
    IF current_version != 'd30414b42ecb' THEN
        RAISE EXCEPTION 'Expected current version d30414b42ecb, but found: %', current_version;
    END IF;
END $$;

-- Migration 4212cb7567aa: Add is_demo and original_user_id columns
DO $$
BEGIN
    -- Add is_demo column if it doesn't exist
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns 
        WHERE table_name = 'videos' AND column_name = 'is_demo'
    ) THEN
        ALTER TABLE videos ADD COLUMN is_demo BOOLEAN NOT NULL DEFAULT false;
        CREATE INDEX IF NOT EXISTS ix_videos_is_demo ON videos (is_demo);
        -- Note: DEFAULT false automatically applies to all existing rows, no UPDATE needed
        RAISE NOTICE '✅ Added is_demo column';
    ELSE
        RAISE NOTICE 'ℹ️  is_demo column already exists';
    END IF;

    -- Add original_user_id column if it doesn't exist
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns 
        WHERE table_name = 'videos' AND column_name = 'original_user_id'
    ) THEN
        ALTER TABLE videos ADD COLUMN original_user_id VARCHAR(36);
        RAISE NOTICE '✅ Added original_user_id column';
    ELSE
        RAISE NOTICE 'ℹ️  original_user_id column already exists';
    END IF;
END $$;

-- Update version to 4212cb7567aa
UPDATE alembic_version SET version_num = '4212cb7567aa' WHERE version_num = 'd30414b42ecb';

-- Migration d1f0ec4cf292: Add is_active_demo column
DO $$
BEGIN
    -- Add is_active_demo column if it doesn't exist
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns 
        WHERE table_name = 'videos' AND column_name = 'is_active_demo'
    ) THEN
        ALTER TABLE videos ADD COLUMN is_active_demo BOOLEAN NOT NULL DEFAULT false;
        CREATE INDEX IF NOT EXISTS ix_videos_is_active_demo ON videos (is_active_demo);
        -- Note: DEFAULT false automatically applies to all existing rows, no UPDATE needed
        RAISE NOTICE '✅ Added is_active_demo column';
    ELSE
        RAISE NOTICE 'ℹ️  is_active_demo column already exists';
    END IF;
END $$;

-- Update version to d1f0ec4cf292
UPDATE alembic_version SET version_num = 'd1f0ec4cf292' WHERE version_num = '4212cb7567aa';

COMMIT;

-- Verification queries (run these separately to see results)
-- Verify columns exist
SELECT 
    column_name, 
    data_type, 
    column_default,
    is_nullable
FROM information_schema.columns 
WHERE table_name = 'videos' 
AND column_name IN ('is_demo', 'is_active_demo', 'original_user_id')
ORDER BY column_name;

-- Verify version updated
SELECT version_num FROM alembic_version;

-- Verify indexes exist
SELECT indexname 
FROM pg_indexes 
WHERE tablename = 'videos' 
AND indexname IN ('ix_videos_is_demo', 'ix_videos_is_active_demo');
