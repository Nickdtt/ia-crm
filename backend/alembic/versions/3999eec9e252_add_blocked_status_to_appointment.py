"""add_blocked_status_to_appointment

Revision ID: 3999eec9e252
Revises: e76a85ad1fc9
Create Date: 2026-01-25 00:56:34.263051

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '3999eec9e252'
down_revision: Union[str, Sequence[str], None] = 'e76a85ad1fc9'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    # Adiciona valor 'blocked' ao enum appointmentstatus
    op.execute("ALTER TYPE appointmentstatus ADD VALUE IF NOT EXISTS 'blocked'")


def downgrade() -> None:
    """Downgrade schema."""
    # Nota: PostgreSQL não permite remover valores de enum facilmente
    # Seria necessário recriar o enum inteiro
    pass
