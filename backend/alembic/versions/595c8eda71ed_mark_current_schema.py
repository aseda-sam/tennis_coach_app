"""mark_current_schema

Revision ID: 595c8eda71ed
Revises: a1b2c3d4e5f6
Create Date: 2025-08-10 16:23:09.458078

"""

from typing import Sequence, Union

# revision identifiers, used by Alembic.
revision: str = "595c8eda71ed"
down_revision: Union[str, Sequence[str], None] = "a1b2c3d4e5f6"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    pass


def downgrade() -> None:
    """Downgrade schema."""
    pass
