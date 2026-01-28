"""add_cascade_delete_trigger_for_auth_users

Revision ID: e2e9e9d5b092
Revises: 7a1eaf7c970e
Create Date: 2026-01-28 13:41:22.893349

"""

from typing import Sequence, Union

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "e2e9e9d5b092"
down_revision: Union[str, Sequence[str], None] = "7a1eaf7c970e"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Create trigger to cascade delete user data when auth user is deleted.

    This trigger fires when a user is deleted from Supabase's auth.users table
    and automatically deletes all related data:
    - Videos (which cascades to serve_attempts, pose_detections, video_jobs)
    - Players (which cascades to serve_attempts)

    Note: This only works in Supabase where auth.users exists. In local dev
    with PROFILE=local, auth is disabled and this trigger won't be created.
    """
    # Check if auth.users table exists (Supabase only)
    # If it doesn't exist, skip trigger creation (local dev scenario)
    # Create the trigger function with proper security settings
    # Note: In Supabase, SECURITY DEFINER functions run as the owner (postgres)
    # which can bypass RLS when properly configured
    op.execute("""
        DO $$
        BEGIN
            IF EXISTS (
                SELECT FROM information_schema.tables
                WHERE table_schema = 'auth'
                AND table_name = 'users'
            ) THEN
                -- Create trigger function
                -- SECURITY DEFINER: runs with owner privileges (postgres)
                -- SET search_path = '': prevents search_path injection (Supabase best practice)
                CREATE OR REPLACE FUNCTION public.handle_auth_user_deleted()
                RETURNS TRIGGER AS $func$
                BEGIN
                    -- Delete videos (cascades to serve_attempts, pose_detections, video_jobs)
                    DELETE FROM public.videos WHERE user_id = OLD.id::text;

                    -- Delete players (cascades to serve_attempts)
                    DELETE FROM public.players WHERE user_id = OLD.id::text;

                    RETURN OLD;
                END;
                $func$ LANGUAGE plpgsql SECURITY DEFINER SET search_path = '';

                -- Ensure function is owned by postgres (has BYPASSRLS)
                ALTER FUNCTION public.handle_auth_user_deleted() OWNER TO postgres;

                -- Revoke execute from public, grant to postgres only
                REVOKE ALL ON FUNCTION public.handle_auth_user_deleted() FROM PUBLIC;
                GRANT EXECUTE ON FUNCTION public.handle_auth_user_deleted() TO postgres;

                -- Create trigger on auth.users table
                DROP TRIGGER IF EXISTS on_auth_user_deleted ON auth.users;
                CREATE TRIGGER on_auth_user_deleted
                    AFTER DELETE ON auth.users
                    FOR EACH ROW
                    EXECUTE FUNCTION public.handle_auth_user_deleted();
            END IF;
        END $$;
    """)


def downgrade() -> None:
    """Remove cascade delete trigger and function."""
    # Check if auth.users table exists before trying to drop trigger
    op.execute("""
        DO $$
        BEGIN
            IF EXISTS (
                SELECT FROM information_schema.tables
                WHERE table_schema = 'auth'
                AND table_name = 'users'
            ) THEN
                DROP TRIGGER IF EXISTS on_auth_user_deleted ON auth.users;
                DROP FUNCTION IF EXISTS public.handle_auth_user_deleted();
            END IF;
        END $$;
    """)
