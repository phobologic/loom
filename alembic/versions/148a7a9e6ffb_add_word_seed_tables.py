"""add_word_seed_tables

Revision ID: 148a7a9e6ffb
Revises: 06150f5d6aff
Create Date: 2026-02-25 10:00:00.000000

"""

from __future__ import annotations

from typing import Sequence, Union

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "148a7a9e6ffb"
down_revision: Union[str, Sequence[str], None] = "06150f5d6aff"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Create word_seed_tables and word_seed_entries tables."""
    conn = op.get_bind()
    existing_tables = {
        row[0] for row in conn.execute(sa.text("SELECT name FROM sqlite_master WHERE type='table'"))
    }

    if "word_seed_tables" not in existing_tables:
        op.create_table(
            "word_seed_tables",
            sa.Column("id", sa.Integer(), nullable=False),
            sa.Column("game_id", sa.Integer(), nullable=False),
            sa.Column("category", sa.String(length=50), nullable=False),
            sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.text("1")),
            sa.Column("is_builtin", sa.Boolean(), nullable=False, server_default=sa.text("1")),
            sa.Column(
                "created_at",
                sa.DateTime(timezone=True),
                server_default=sa.text("(CURRENT_TIMESTAMP)"),
                nullable=False,
            ),
            sa.Column(
                "updated_at",
                sa.DateTime(timezone=True),
                server_default=sa.text("(CURRENT_TIMESTAMP)"),
                nullable=False,
            ),
            sa.ForeignKeyConstraint(["game_id"], ["games.id"], ondelete="CASCADE"),
            sa.PrimaryKeyConstraint("id"),
        )

    if "word_seed_entries" not in existing_tables:
        op.create_table(
            "word_seed_entries",
            sa.Column("id", sa.Integer(), nullable=False),
            sa.Column("table_id", sa.Integer(), nullable=False),
            sa.Column("word", sa.String(length=100), nullable=False),
            sa.Column("word_type", sa.String(length=20), nullable=False),
            sa.Column(
                "created_at",
                sa.DateTime(timezone=True),
                server_default=sa.text("(CURRENT_TIMESTAMP)"),
                nullable=False,
            ),
            sa.Column(
                "updated_at",
                sa.DateTime(timezone=True),
                server_default=sa.text("(CURRENT_TIMESTAMP)"),
                nullable=False,
            ),
            sa.ForeignKeyConstraint(["table_id"], ["word_seed_tables.id"], ondelete="CASCADE"),
            sa.PrimaryKeyConstraint("id"),
        )


def downgrade() -> None:
    """Drop word_seed_tables and word_seed_entries tables."""
    op.drop_table("word_seed_entries")
    op.drop_table("word_seed_tables")
