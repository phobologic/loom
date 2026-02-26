"""add_challenge_outcome_to_beats

Revision ID: 9993fe99a62b
Revises: 2be5780d189d
Create Date: 2026-02-26 13:23:13.247396

"""

from typing import Sequence, Union

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "9993fe99a62b"
down_revision: Union[str, Sequence[str], None] = "2be5780d189d"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("beats", sa.Column("challenge_outcome", sa.String(length=50), nullable=True))


def downgrade() -> None:
    op.drop_column("beats", "challenge_outcome")
