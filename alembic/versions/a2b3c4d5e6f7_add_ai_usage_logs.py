"""add_ai_usage_logs

Revision ID: a2b3c4d5e6f7
Revises: f3a2b1c0d9e8
Create Date: 2026-02-26 06:00:00.000000

"""

from __future__ import annotations

from typing import Sequence, Union

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "a2b3c4d5e6f7"
down_revision: Union[str, Sequence[str], None] = "e5f6a7b8c9d0"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Create ai_usage_logs table."""
    op.create_table(
        "ai_usage_logs",
        sa.Column("id", sa.Integer(), primary_key=True, nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.Column("feature", sa.String(100), nullable=False),
        sa.Column("model", sa.String(100), nullable=False),
        sa.Column("input_tokens", sa.Integer(), nullable=False),
        sa.Column("output_tokens", sa.Integer(), nullable=False),
        sa.Column("context_components", sa.Text(), nullable=True),
        sa.Column(
            "game_id", sa.Integer(), sa.ForeignKey("games.id", ondelete="SET NULL"), nullable=True
        ),
    )


def downgrade() -> None:
    """Drop ai_usage_logs table."""
    op.drop_table("ai_usage_logs")
