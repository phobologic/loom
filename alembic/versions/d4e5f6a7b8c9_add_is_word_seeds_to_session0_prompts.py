"""add_is_word_seeds_to_session0_prompts

Revision ID: d4e5f6a7b8c9
Revises: a1b2c3d4e5f6
Create Date: 2026-02-25 00:00:00.000000

"""

from __future__ import annotations

from typing import Sequence, Union

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "d4e5f6a7b8c9"
down_revision: Union[str, Sequence[str], None] = "a1b2c3d4e5f6"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Add is_word_seeds column to session0_prompts."""
    op.add_column(
        "session0_prompts",
        sa.Column("is_word_seeds", sa.Boolean(), nullable=False, server_default="0"),
    )


def downgrade() -> None:
    """Remove is_word_seeds column from session0_prompts."""
    op.drop_column("session0_prompts", "is_word_seeds")
