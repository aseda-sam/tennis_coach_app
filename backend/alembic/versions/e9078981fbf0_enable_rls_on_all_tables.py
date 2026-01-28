"""enable_rls_on_all_tables

Revision ID: e9078981fbf0
Revises: e2e9e9d5b092
Create Date: 2026-01-28 14:00:56.530938

"""

from typing import Sequence, Union

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "e9078981fbf0"
down_revision: Union[str, Sequence[str], None] = "e2e9e9d5b092"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

# All application tables that should have RLS enabled
# Note: alembic_version already has RLS enabled (separate migration)
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
    """Enable Row Level Security on all application tables.

    Why RLS with no policies?
    -------------------------
    In Supabase, tables in the public schema are automatically exposed via
    PostgREST (the auto-generated REST API). This creates a security risk:

    - RLS disabled: Anyone with anon key can read/write ALL data
    - RLS enabled, no policies: PostgREST access blocked (returns empty)
    - RLS enabled, with policies: Only allowed access per policy rules

    Since our backend:
    1. Uses service_role key (which bypasses RLS)
    2. Does all authorization in Python code
    3. Is the only interface for users

    We enable RLS with NO policies as "defense in depth":
    - PostgREST is effectively blocked
    - Backend works normally (service_role bypasses RLS)
    - No complex RLS policies to maintain

    This is the recommended pattern for backend-only architectures.
    """
    for table in APPLICATION_TABLES:
        # Use DO block to make it idempotent (won't fail if table doesn't exist
        # or RLS is already enabled)
        op.execute(f"""
            DO $$
            BEGIN
                IF EXISTS (
                    SELECT FROM information_schema.tables
                    WHERE table_schema = 'public'
                    AND table_name = '{table}'
                ) THEN
                    ALTER TABLE public.{table} ENABLE ROW LEVEL SECURITY;
                END IF;
            END $$;
        """)


def downgrade() -> None:
    """Disable Row Level Security on all application tables.

    WARNING: This will expose all data via PostgREST if Supabase is configured
    with the public schema exposed.
    """
    for table in APPLICATION_TABLES:
        op.execute(f"""
            DO $$
            BEGIN
                IF EXISTS (
                    SELECT FROM information_schema.tables
                    WHERE table_schema = 'public'
                    AND table_name = '{table}'
                ) THEN
                    ALTER TABLE public.{table} DISABLE ROW LEVEL SECURITY;
                END IF;
            END $$;
        """)
