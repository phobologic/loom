"""add tension_carry_forward to scenes

Revision ID: 2be5780d189d
Revises: e7f8a9b0c1d2
Create Date: 2026-02-26 12:43:13.321104

"""

from typing import Sequence, Union

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "2be5780d189d"
down_revision: Union[str, Sequence[str], None] = "e7f8a9b0c1d2"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.add_column("scenes", sa.Column("tension_carry_forward", sa.Integer(), nullable=True))


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_column("scenes", "tension_carry_forward")
