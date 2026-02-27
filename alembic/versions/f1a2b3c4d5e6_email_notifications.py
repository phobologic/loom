"""email_notifications

Revision ID: f1a2b3c4d5e6
Revises: 89c6a0f67eb9
Create Date: 2026-02-26 12:00:00.000000

"""

from typing import Sequence, Union

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "f1a2b3c4d5e6"
down_revision: Union[str, Sequence[str], None] = "89c6a0f67eb9"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    with op.batch_alter_table("users") as batch_op:
        batch_op.add_column(
            sa.Column(
                "email_pref",
                sa.String(length=20),
                nullable=False,
                server_default="digest",
            )
        )

    with op.batch_alter_table("game_members") as batch_op:
        batch_op.add_column(sa.Column("email_pref_override", sa.String(length=20), nullable=True))

    with op.batch_alter_table("notifications") as batch_op:
        batch_op.add_column(sa.Column("emailed_at", sa.DateTime(timezone=True), nullable=True))


def downgrade() -> None:
    """Downgrade schema."""
    with op.batch_alter_table("notifications") as batch_op:
        batch_op.drop_column("emailed_at")

    with op.batch_alter_table("game_members") as batch_op:
        batch_op.drop_column("email_pref_override")

    with op.batch_alter_table("users") as batch_op:
        batch_op.drop_column("email_pref")
