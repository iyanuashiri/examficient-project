"""exam voice_enabled flag

Revision ID: c84d1e5b6a92
Revises: b71f2c9d4a08
Create Date: 2026-11-05

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'c84d1e5b6a92'
down_revision: Union[str, Sequence[str], None] = 'b71f2c9d4a08'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.add_column('exam', sa.Column('voice_enabled', sa.Boolean(), nullable=False, server_default=sa.false()))


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_column('exam', 'voice_enabled')
