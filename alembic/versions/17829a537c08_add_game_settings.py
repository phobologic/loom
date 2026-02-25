"""add_game_settings

Revision ID: 17829a537c08
Revises: 8d14509786db
Create Date: 2026-02-24 18:23:43.561556

"""

from __future__ import annotations

from typing import Sequence, Union

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "17829a537c08"
down_revision: Union[str, Sequence[str], None] = "8d14509786db"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Add game settings columns to the games table."""
    op.add_column(
        "games", sa.Column("silence_timer_hours", sa.Integer(), nullable=False, server_default="12")
    )
    op.add_column(
        "games",
        sa.Column(
            "tie_breaking_method",
            sa.Enum(
                "random", "proposer", "challenger", name="tiebreakingmethod", native_enum=False
            ),
            nullable=False,
            server_default="random",
        ),
    )
    op.add_column(
        "games",
        sa.Column(
            "beat_significance_threshold",
            sa.Enum(
                "flag_most",
                "flag_obvious",
                "minimal",
                name="beatsignificancethreshold",
                native_enum=False,
            ),
            nullable=False,
            server_default="flag_obvious",
        ),
    )
    op.add_column(
        "games",
        sa.Column("max_consecutive_beats", sa.Integer(), nullable=False, server_default="3"),
    )
    op.add_column(
        "games",
        sa.Column("auto_generate_narrative", sa.Boolean(), nullable=False, server_default="1"),
    )
    op.add_column(
        "games", sa.Column("fortune_roll_contest_window_hours", sa.Integer(), nullable=True)
    )
    op.add_column(
        "games", sa.Column("starting_tension", sa.Integer(), nullable=False, server_default="5")
    )


def downgrade() -> None:
    """Remove game settings columns from the games table."""
    op.drop_column("games", "starting_tension")
    op.drop_column("games", "fortune_roll_contest_window_hours")
    op.drop_column("games", "auto_generate_narrative")
    op.drop_column("games", "max_consecutive_beats")
    op.drop_column("games", "beat_significance_threshold")
    op.drop_column("games", "tie_breaking_method")
    op.drop_column("games", "silence_timer_hours")
