"""mark_current_schema

Revision ID: 595c8eda71ed
Revises: 63c79de0875a
Create Date: 2025-08-10 16:23:09.458078

"""

from typing import Sequence, Union

# revision identifiers, used by Alembic.
revision: str = "595c8eda71ed"
down_revision: Union[str, Sequence[str], None] = "63c79de0875a"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    pass


def downgrade() -> None:
    """Downgrade schema."""
    pass
