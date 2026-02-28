"""add_narrative_voice

Revision ID: d6e7f8a9b0c1
Revises: c2d3e4f5a6b7
Create Date: 2026-02-27 00:00:00.000000

"""

from __future__ import annotations

from typing import Sequence, Union

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "d6e7f8a9b0c1"
down_revision: Union[str, Sequence[str], None] = "c2d3e4f5a6b7"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Add narrative_voice to games and is_narrative_voice to session0_prompts."""
    op.add_column(
        "games",
        sa.Column("narrative_voice", sa.Text(), nullable=True),
    )
    op.add_column(
        "session0_prompts",
        sa.Column("is_narrative_voice", sa.Boolean(), nullable=False, server_default="0"),
    )


def downgrade() -> None:
    """Remove narrative_voice and is_narrative_voice columns."""
    op.drop_column("games", "narrative_voice")
    op.drop_column("session0_prompts", "is_narrative_voice")
