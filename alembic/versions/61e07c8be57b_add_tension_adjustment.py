"""add_tension_adjustment

Revision ID: 61e07c8be57b
Revises: a2b3c4d5e6f7
Create Date: 2026-02-26 06:53:00.669280

"""

from typing import Sequence, Union

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "61e07c8be57b"
down_revision: Union[str, Sequence[str], None] = "a2b3c4d5e6f7"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.add_column("vote_proposals", sa.Column("tension_delta", sa.Integer(), nullable=True))
    op.add_column("vote_proposals", sa.Column("ai_rationale", sa.Text(), nullable=True))


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_column("vote_proposals", "ai_rationale")
    op.drop_column("vote_proposals", "tension_delta")
