"""add_voice_notes_to_characters

Revision ID: a0ad2b718fc4
Revises: 9993fe99a62b
Create Date: 2026-02-26 14:00:00.000000

"""

from typing import Sequence, Union

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "a0ad2b718fc4"
down_revision: Union[str, Sequence[str], None] = "9993fe99a62b"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("characters", sa.Column("voice_notes", sa.Text(), nullable=True))


def downgrade() -> None:
    op.drop_column("characters", "voice_notes")
