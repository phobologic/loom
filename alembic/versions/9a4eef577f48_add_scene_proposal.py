"""add_scene_proposal

Revision ID: 9a4eef577f48
Revises: b2458367ae3d
Create Date: 2026-02-24 21:37:47.025318

"""

from typing import Sequence, Union

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "9a4eef577f48"
down_revision: Union[str, Sequence[str], None] = "b2458367ae3d"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Add act_id and scene_id to vote_proposals for proposal type expansion."""
    conn = op.get_bind()
    existing = {row[1] for row in conn.execute(sa.text("PRAGMA table_info(vote_proposals)"))}
    if "act_id" not in existing:
        op.add_column("vote_proposals", sa.Column("act_id", sa.Integer(), nullable=True))
    if "scene_id" not in existing:
        op.add_column("vote_proposals", sa.Column("scene_id", sa.Integer(), nullable=True))


def downgrade() -> None:
    """Remove scene_id from vote_proposals."""
    op.drop_column("vote_proposals", "scene_id")
