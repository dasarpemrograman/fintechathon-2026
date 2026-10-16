"""Encrypted idempotent authentication receipts."""

from alembic import op
from migrations.schema_v2 import metadata

revision = "0002"
down_revision = "0001"


def upgrade():
    metadata.create_all(op.get_bind())


def downgrade():
    raise RuntimeError(
        "Restore a verified backup instead of discarding session history."
    )
