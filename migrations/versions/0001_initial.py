"""Initial tenant-scoped storage with immutable snapshots and durable jobs."""

from alembic import op
from migrations.schema_v1 import metadata

revision = "0001"
down_revision = None


def upgrade():
    metadata.create_all(op.get_bind())


def downgrade():
    raise RuntimeError(
        "Refusing destructive history deletion; restore a verified backup instead."
    )
