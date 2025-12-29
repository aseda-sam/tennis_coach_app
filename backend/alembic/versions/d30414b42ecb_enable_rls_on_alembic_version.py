"""enable_rls_on_alembic_version

Revision ID: d30414b42ecb
Revises: 8591bc6ff486
Create Date: 2025-12-29 08:13:40.291903

"""

from typing import Sequence, Union

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "d30414b42ecb"
down_revision: Union[str, Sequence[str], None] = "8591bc6ff486"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Enable RLS on alembic_version table to satisfy Supabase security requirements.

    The alembic_version table is only used by Alembic to track migration versions
    and should not be accessed via the PostgREST API. Enabling RLS with no policies
    will deny all API access while still allowing Alembic (running as the table owner)
    to access it during migrations.
    """
    # Enable RLS on alembic_version table
    # With RLS enabled and no policies, all access via PostgREST is denied
    # but the table owner (used by Alembic) can still access it
    op.execute("ALTER TABLE alembic_version ENABLE ROW LEVEL SECURITY")


def downgrade() -> None:
    """Disable RLS on alembic_version table."""
    op.execute("ALTER TABLE alembic_version DISABLE ROW LEVEL SECURITY")
