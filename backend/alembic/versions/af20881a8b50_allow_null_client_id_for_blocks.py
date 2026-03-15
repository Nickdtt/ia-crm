"""allow_null_client_id_for_blocks

Revision ID: af20881a8b50
Revises: 3999eec9e252
Create Date: 2026-01-25 00:59:34.275841

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'af20881a8b50'
down_revision: Union[str, Sequence[str], None] = '3999eec9e252'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    # Permite client_id NULL (para bloqueios administrativos)
    op.alter_column('appointments', 'client_id',
                    existing_type=sa.UUID(),
                    nullable=True)


def downgrade() -> None:
    """Downgrade schema."""
    # Volta a exigir client_id
    op.alter_column('appointments', 'client_id',
                    existing_type=sa.UUID(),
                    nullable=False)
