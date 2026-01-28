"""drop_existing_rls_policies

Revision ID: 7d36585465af
Revises: e9078981fbf0
Create Date: 2026-01-28 14:31:03.354157

"""
# ruff: noqa: S608  # Table names are from hardcoded APPLICATION_TABLES list, safe

from typing import Sequence, Union

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "7d36585465af"
down_revision: Union[str, Sequence[str], None] = "e9078981fbf0"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

# All application tables that should have RLS enabled but NO policies
APPLICATION_TABLES = [
    "videos",
    "players",
    "serve_attempts",
    "pose_detections",
    "video_jobs",
    # Legacy tables (may still exist in some environments)
    "ball_detections",
    # Note: video_players will be dropped in a later migration (fb60e79c5043)
]


def upgrade() -> None:
    """Drop all existing RLS policies on application tables.

    This ensures a clean state where:
    - RLS is enabled (defense in depth)
    - No policies exist (PostgREST blocked, backend works via service_role)

    Any policies created manually in Supabase dashboard will be removed.
    """
    for table in APPLICATION_TABLES:
        # Drop all policies on this table dynamically
        # Table names are from hardcoded list, safe to use in f-string
        op.execute(
            f"""
            DO $$
            DECLARE
                policy_record RECORD;
            BEGIN
                -- Check if table exists
                IF EXISTS (
                    SELECT FROM information_schema.tables
                    WHERE table_schema = 'public'
                    AND table_name = '{table}'
                ) THEN
                    -- Drop all policies on this table
                    FOR policy_record IN
                        SELECT policyname
                        FROM pg_policies
                        WHERE schemaname = 'public'
                        AND tablename = '{table}'
                    LOOP
                        EXECUTE format('DROP POLICY IF EXISTS %I ON public.%I', policy_record.policyname, '{table}');
                    END LOOP;
                END IF;
            END $$;
        """
        )


def downgrade() -> None:
    """No-op: Cannot restore policies that were manually created.

    If policies need to be restored, they must be recreated manually
    or via a new migration.
    """
    pass
