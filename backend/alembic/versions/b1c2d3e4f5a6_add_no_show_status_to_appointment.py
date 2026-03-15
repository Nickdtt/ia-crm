"""add_no_show_status_to_appointment

Revision ID: b1c2d3e4f5a6
Revises: af20881a8b50
Create Date: 2026-03-05 19:50:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'b1c2d3e4f5a6'
down_revision: Union[str, Sequence[str], None] = 'af20881a8b50'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Adiciona valores 'no_show' e 'NO_SHOW' ao enum appointmentstatus."""
    op.execute("ALTER TYPE appointmentstatus ADD VALUE IF NOT EXISTS 'no_show'")
    op.execute("ALTER TYPE appointmentstatus ADD VALUE IF NOT EXISTS 'NO_SHOW'")


def downgrade() -> None:
    """Downgrade: PostgreSQL não permite remover valores de enum facilmente."""
    pass
