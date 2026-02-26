"""prose_expansion

Revision ID: ee0234fa5d74
Revises: a0ad2b718fc4
Create Date: 2026-02-26 14:58:57.466965

"""

from typing import Sequence, Union

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "ee0234fa5d74"
down_revision: Union[str, Sequence[str], None] = "a0ad2b718fc4"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.add_column("events", sa.Column("prose_expanded", sa.Text(), nullable=True))
    op.add_column(
        "events", sa.Column("prose_applied", sa.Boolean(), server_default="0", nullable=False)
    )
    op.add_column(
        "events", sa.Column("prose_dismissed", sa.Boolean(), server_default="0", nullable=False)
    )
    op.add_column(
        "game_members", sa.Column("prose_mode_override", sa.String(length=20), nullable=True)
    )
    op.add_column(
        "users",
        sa.Column("prose_mode", sa.String(length=20), server_default="always", nullable=False),
    )
    op.add_column(
        "users",
        sa.Column("prose_threshold_words", sa.Integer(), server_default="50", nullable=False),
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_column("users", "prose_threshold_words")
    op.drop_column("users", "prose_mode")
    op.drop_column("game_members", "prose_mode_override")
    op.drop_column("events", "prose_dismissed")
    op.drop_column("events", "prose_applied")
    op.drop_column("events", "prose_expanded")
