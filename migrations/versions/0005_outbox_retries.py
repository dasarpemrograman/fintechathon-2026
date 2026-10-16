"""Bounded outbox retry scheduling and sanitized provider failure codes."""

import sqlalchemy as sa
from alembic import op

revision = "0005"
down_revision = "0004"
branch_labels = None
depends_on = None


def upgrade():
    op.add_column(
        "outbox", sa.Column("attempts", sa.Integer, nullable=False, server_default="0")
    )
    op.add_column(
        "outbox",
        sa.Column(
            "available_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
    )
    op.add_column("outbox", sa.Column("last_error", sa.Text))


def downgrade():
    raise RuntimeError("Outbox receipts require retention; use a forward migration.")
