"""add_safety_tools

Revision ID: b2458367ae3d
Revises: 4763999af882
Create Date: 2026-02-24 20:17:50.858186

"""

from __future__ import annotations

from typing import Sequence, Union

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "b2458367ae3d"
down_revision: Union[str, Sequence[str], None] = "4763999af882"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

_ts = sa.text("(CURRENT_TIMESTAMP)")


def upgrade() -> None:
    """Add game_safety_tools table and is_safety_tools column to session0_prompts."""
    op.create_table(
        "game_safety_tools",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("game_id", sa.Integer(), nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=True),
        sa.Column(
            "kind",
            sa.Enum("line", "veil", name="safetytoolkind", native_enum=False),
            nullable=False,
        ),
        sa.Column("description", sa.Text(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=_ts, nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=_ts, nullable=False),
        sa.ForeignKeyConstraint(["game_id"], ["games.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.add_column(
        "session0_prompts",
        sa.Column("is_safety_tools", sa.Boolean(), nullable=False, server_default="0"),
    )


def downgrade() -> None:
    """Remove game_safety_tools table and is_safety_tools column."""
    op.drop_column("session0_prompts", "is_safety_tools")
    op.drop_table("game_safety_tools")
