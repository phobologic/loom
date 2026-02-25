"""add_oracle_discussion

Revision ID: c3f9a1b2d4e5
Revises: 148a7a9e6ffb
Create Date: 2026-02-25 12:00:00.000000

"""

from __future__ import annotations

from typing import Sequence, Union

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "c3f9a1b2d4e5"
down_revision: Union[str, Sequence[str], None] = "148a7a9e6ffb"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

_ts = sa.text("(CURRENT_TIMESTAMP)")


def upgrade() -> None:
    """Add oracle discussion columns to events and create oracle discussion tables."""
    conn = op.get_bind()

    # Add oracle_type and oracle_selected_interpretation to events
    existing_event_cols = {row[1] for row in conn.execute(sa.text("PRAGMA table_info(events)"))}
    if "oracle_type" not in existing_event_cols:
        op.add_column("events", sa.Column("oracle_type", sa.String(length=20), nullable=True))
    if "oracle_selected_interpretation" not in existing_event_cols:
        op.add_column(
            "events",
            sa.Column("oracle_selected_interpretation", sa.Text(), nullable=True),
        )

    # Create oracle_interpretation_votes table
    existing_tables = {
        row[0] for row in conn.execute(sa.text("SELECT name FROM sqlite_master WHERE type='table'"))
    }

    if "oracle_interpretation_votes" not in existing_tables:
        op.create_table(
            "oracle_interpretation_votes",
            sa.Column("id", sa.Integer(), nullable=False),
            sa.Column("event_id", sa.Integer(), nullable=False),
            sa.Column("voter_id", sa.Integer(), nullable=True),
            sa.Column("interpretation_index", sa.Integer(), nullable=False),
            sa.Column("alternative_text", sa.Text(), nullable=True),
            sa.Column("created_at", sa.DateTime(timezone=True), server_default=_ts, nullable=False),
            sa.Column("updated_at", sa.DateTime(timezone=True), server_default=_ts, nullable=False),
            sa.ForeignKeyConstraint(["event_id"], ["events.id"], ondelete="CASCADE"),
            sa.ForeignKeyConstraint(["voter_id"], ["users.id"], ondelete="SET NULL"),
            sa.PrimaryKeyConstraint("id"),
            sa.UniqueConstraint("event_id", "voter_id", name="uq_oracle_vote"),
        )

    if "oracle_comments" not in existing_tables:
        op.create_table(
            "oracle_comments",
            sa.Column("id", sa.Integer(), nullable=False),
            sa.Column("event_id", sa.Integer(), nullable=False),
            sa.Column("author_id", sa.Integer(), nullable=True),
            sa.Column("text", sa.Text(), nullable=False),
            sa.Column("created_at", sa.DateTime(timezone=True), server_default=_ts, nullable=False),
            sa.Column("updated_at", sa.DateTime(timezone=True), server_default=_ts, nullable=False),
            sa.ForeignKeyConstraint(["event_id"], ["events.id"], ondelete="CASCADE"),
            sa.ForeignKeyConstraint(["author_id"], ["users.id"], ondelete="SET NULL"),
            sa.PrimaryKeyConstraint("id"),
        )


def downgrade() -> None:
    """Remove oracle discussion tables and columns."""
    op.drop_table("oracle_comments")
    op.drop_table("oracle_interpretation_votes")
    op.drop_column("events", "oracle_selected_interpretation")
    op.drop_column("events", "oracle_type")
