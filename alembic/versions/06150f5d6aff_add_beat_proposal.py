"""add_beat_proposal

Revision ID: 06150f5d6aff
Revises: 9a4eef577f48
Create Date: 2026-02-25 08:09:26.773853

"""

from __future__ import annotations

from typing import Sequence, Union

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "06150f5d6aff"
down_revision: Union[str, Sequence[str], None] = "9a4eef577f48"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Add beat_id and expires_at columns to vote_proposals."""
    conn = op.get_bind()
    existing = {row[1] for row in conn.execute(sa.text("PRAGMA table_info(vote_proposals)"))}
    if "beat_id" not in existing:
        op.add_column("vote_proposals", sa.Column("beat_id", sa.Integer(), nullable=True))
    if "expires_at" not in existing:
        op.add_column(
            "vote_proposals",
            sa.Column("expires_at", sa.DateTime(timezone=True), nullable=True),
        )


def downgrade() -> None:
    """Remove beat_id and expires_at columns from vote_proposals."""
    op.drop_column("vote_proposals", "expires_at")
    op.drop_column("vote_proposals", "beat_id")
