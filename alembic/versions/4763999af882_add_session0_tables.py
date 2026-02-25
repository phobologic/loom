"""add_session0_tables

Revision ID: 4763999af882
Revises: 17829a537c08
Create Date: 2026-02-24 19:54:08.409107

"""

from __future__ import annotations

from typing import Sequence, Union

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "4763999af882"
down_revision: Union[str, Sequence[str], None] = "17829a537c08"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

_ts = sa.text("(CURRENT_TIMESTAMP)")


def upgrade() -> None:
    """Add session0_prompts and session0_responses tables."""
    op.create_table(
        "session0_prompts",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("game_id", sa.Integer(), nullable=False),
        sa.Column("order", sa.Integer(), nullable=False),
        sa.Column("question", sa.Text(), nullable=False),
        sa.Column("is_default", sa.Boolean(), nullable=False, server_default="1"),
        sa.Column(
            "status",
            sa.Enum(
                "pending",
                "active",
                "skipped",
                "complete",
                name="promptstatus",
                native_enum=False,
            ),
            nullable=False,
            server_default="pending",
        ),
        sa.Column("synthesis", sa.Text(), nullable=True),
        sa.Column("synthesis_accepted", sa.Boolean(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=_ts, nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=_ts, nullable=False),
        sa.ForeignKeyConstraint(["game_id"], ["games.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_table(
        "session0_responses",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("prompt_id", sa.Integer(), nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=True),
        sa.Column("content", sa.Text(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=_ts, nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=_ts, nullable=False),
        sa.ForeignKeyConstraint(["prompt_id"], ["session0_prompts.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("prompt_id", "user_id", name="uq_session0_response"),
    )


def downgrade() -> None:
    """Remove session0_prompts and session0_responses tables."""
    op.drop_table("session0_responses")
    op.drop_table("session0_prompts")
