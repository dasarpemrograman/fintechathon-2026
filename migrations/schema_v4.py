"""Market evidence records, with independent migration metadata."""

import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSONB
from migrations.schema_v1 import registry

metadata = sa.MetaData()
market_observations = sa.Table(
    "market_observation_records",
    metadata,
    sa.Column("tenant_id", sa.Text, primary_key=True),
    sa.Column("id", sa.Text, primary_key=True),
    sa.Column("parent_id", sa.Text),
    sa.Column("revision", sa.Integer, nullable=False),
    sa.Column("data", JSONB, nullable=False),
    sa.Column("amount", sa.Numeric),
    sa.Column("currency", sa.Text),
    sa.Column(
        "created_at",
        sa.DateTime(timezone=True),
        nullable=False,
        server_default=sa.func.now(),
    ),
    sa.ForeignKeyConstraint(["tenant_id", "id"], [registry.c.tenant_id, registry.c.id]),
    sa.ForeignKeyConstraint(
        ["tenant_id", "parent_id"], [registry.c.tenant_id, registry.c.id]
    ),
    sa.CheckConstraint("revision > 0"),
    sa.Index("market_observation_parent_idx", "tenant_id", "parent_id", "id"),
)
