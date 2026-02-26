"""add_fortune_roll_contest

Revision ID: f3a2b1c0d9e8
Revises: c3f9a1b2d4e5
Create Date: 2026-02-25 14:00:00.000000

"""

from __future__ import annotations

from typing import Sequence, Union

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "f3a2b1c0d9e8"
down_revision: Union[str, Sequence[str], None] = "c3f9a1b2d4e5"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Add fortune roll contest tracking columns to events."""
    conn = op.get_bind()
    existing = {row[1] for row in conn.execute(sa.text("PRAGMA table_info(events)"))}
    if "fortune_roll_expires_at" not in existing:
        op.add_column(
            "events",
            sa.Column("fortune_roll_expires_at", sa.DateTime(timezone=True), nullable=True),
        )
    if "fortune_roll_contested" not in existing:
        op.add_column(
            "events",
            sa.Column(
                "fortune_roll_contested",
                sa.Boolean(),
                nullable=False,
                server_default="0",
            ),
        )


def downgrade() -> None:
    """Remove fortune roll contest columns from events."""
    op.drop_column("events", "fortune_roll_contested")
    op.drop_column("events", "fortune_roll_expires_at")
