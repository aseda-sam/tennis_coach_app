"""remove_unused_ball_contact_fields

Revision ID: 8809c3660b6f
Revises: 692eb6a34dbe
Create Date: 2025-09-04 09:28:27.362167

"""
from typing import Sequence, Union

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = '8809c3660b6f'
down_revision: Union[str, Sequence[str], None] = '692eb6a34dbe'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Remove unused fields from ball_contacts table."""
    # Remove unused fields that were added for automated ball contact detection
    # but are never used since only manual ball contacts are implemented
    op.drop_column('ball_contacts', 'ball_area')
    op.drop_column('ball_contacts', 'ball_size_factor')
    op.drop_column('ball_contacts', 'racket_data')
    op.drop_column('ball_contacts', 'ball_bbox')
    op.drop_column('ball_contacts', 'ball_racket_distance')
    op.drop_column('ball_contacts', 'player')
    op.drop_column('ball_contacts', 'confidence')
    op.drop_column('ball_contacts', 'ball_position')
    op.drop_column('ball_contacts', 'player_position')
    op.drop_column('ball_contacts', 'description')


def downgrade() -> None:
    """Re-add unused fields to ball_contacts table."""
    # Re-add the unused fields for rollback capability
    op.add_column('ball_contacts', sa.Column('ball_area', sa.Float(), nullable=True))
    op.add_column('ball_contacts', sa.Column('ball_size_factor', sa.Float(), nullable=True))
    op.add_column('ball_contacts', sa.Column('racket_data', sa.String(), nullable=True))
    op.add_column('ball_contacts', sa.Column('ball_bbox', sa.String(), nullable=True))
    op.add_column('ball_contacts', sa.Column('ball_racket_distance', sa.Float(), nullable=True))
    op.add_column('ball_contacts', sa.Column('player', sa.Integer(), nullable=True))
    op.add_column('ball_contacts', sa.Column('confidence', sa.Float(), nullable=True))
    op.add_column('ball_contacts', sa.Column('ball_position', sa.String(), nullable=True))
    op.add_column('ball_contacts', sa.Column('player_position', sa.String(), nullable=True))
    op.add_column('ball_contacts', sa.Column('description', sa.String(), nullable=True))
