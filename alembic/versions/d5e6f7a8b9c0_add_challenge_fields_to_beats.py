"""add_challenge_fields_to_beats

Revision ID: d5e6f7a8b9c0
Revises: 61e07c8be57b
Create Date: 2026-02-26 08:00:00.000000

"""

from typing import Sequence, Union

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "d5e6f7a8b9c0"
down_revision: Union[str, Sequence[str], None] = "61e07c8be57b"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    conn = op.get_bind()
    existing = {row[1] for row in conn.execute(sa.text("PRAGMA table_info(beats)"))}
    if "challenge_reason" not in existing:
        op.add_column("beats", sa.Column("challenge_reason", sa.Text(), nullable=True))
    if "challenged_by_id" not in existing:
        op.add_column(
            "beats",
            sa.Column("challenged_by_id", sa.Integer(), nullable=True),
        )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_column("beats", "challenged_by_id")
    op.drop_column("beats", "challenge_reason")
