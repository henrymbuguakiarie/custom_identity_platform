"""Add refresh token rotation + revocation fields to sessions

Revision ID: d7a90169b2b5
Revises: eebd1ca04a24
Create Date: 2025-11-15 20:22:58.814959

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'd7a90169b2b5'
down_revision: Union[str, Sequence[str], None] = 'eebd1ca04a24'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    pass


def downgrade() -> None:
    """Downgrade schema."""
    pass
