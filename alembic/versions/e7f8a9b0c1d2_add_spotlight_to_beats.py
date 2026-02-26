"""add_spotlight_to_beats

Revision ID: e7f8a9b0c1d2
Revises: d5e6f7a8b9c0
Create Date: 2026-02-26 10:00:00.000000

"""

from typing import Sequence, Union

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "e7f8a9b0c1d2"
down_revision: Union[str, Sequence[str], None] = "e6f7a8b9c0d1"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    conn = op.get_bind()
    existing = {row[1] for row in conn.execute(sa.text("PRAGMA table_info(beats)"))}
    if "waiting_for_character_id" not in existing:
        op.add_column("beats", sa.Column("waiting_for_character_id", sa.Integer(), nullable=True))
    if "spotlight_expires_at" not in existing:
        op.add_column("beats", sa.Column("spotlight_expires_at", sa.DateTime(), nullable=True))
    if "spotlight_resolved_at" not in existing:
        op.add_column("beats", sa.Column("spotlight_resolved_at", sa.DateTime(), nullable=True))


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_column("beats", "spotlight_resolved_at")
    op.drop_column("beats", "spotlight_expires_at")
    op.drop_column("beats", "waiting_for_character_id")
