"""add_oauth_unique_and_notify_prefs

Revision ID: e5f6a7b8c9d0
Revises: d4e5f6a7b8c9
Create Date: 2026-02-25 06:00:00.000000

"""

from typing import Sequence, Union

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "e5f6a7b8c9d0"
down_revision: Union[str, Sequence[str], None] = "d4e5f6a7b8c9"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    # SQLite requires batch mode for constraint changes (copy-and-move strategy).
    with op.batch_alter_table("users") as batch_op:
        batch_op.add_column(
            sa.Column("notify_enabled", sa.Boolean(), nullable=False, server_default=sa.true())
        )
        batch_op.create_unique_constraint("uq_users_oauth", ["oauth_provider", "oauth_subject"])


def downgrade() -> None:
    """Downgrade schema."""
    with op.batch_alter_table("users") as batch_op:
        batch_op.drop_constraint("uq_users_oauth", type_="unique")
        batch_op.drop_column("notify_enabled")
