"""Runtime outbox view with bounded retry scheduling; initial schema stays frozen."""

import sqlalchemy as sa
from migrations.schema_v1 import outbox as initial_outbox

metadata = sa.MetaData()
outbox = initial_outbox.to_metadata(metadata)
outbox.append_column(
    sa.Column("attempts", sa.Integer, nullable=False, server_default="0")
)
outbox.append_column(
    sa.Column(
        "available_at",
        sa.DateTime(timezone=True),
        nullable=False,
        server_default=sa.func.now(),
    )
)
outbox.append_column(sa.Column("last_error", sa.Text))
