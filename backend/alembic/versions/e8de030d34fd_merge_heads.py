"""merge heads

Revision ID: e8de030d34fd
Revises: b8bccc14602f, c3e7c1d9a2b4
Create Date: 2026-02-08 17:20:34.541656

"""

from typing import Sequence, Union

# revision identifiers, used by Alembic.
revision: str = "e8de030d34fd"
down_revision: Union[str, Sequence[str], None] = ("b8bccc14602f", "c3e7c1d9a2b4")
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    pass


def downgrade() -> None:
    """Downgrade schema."""
    pass
