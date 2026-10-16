"""Encrypted connector credentials and stable Calendar event ownership."""

import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSONB
from migrations.schema_v1 import metadata

connector_credentials = sa.Table(
    "connector_credentials",
    metadata,
    sa.Column("tenant_id", sa.Text, primary_key=True),
    sa.Column("connection_id", sa.Text, primary_key=True),
    sa.Column("ciphertext", sa.Text, nullable=False),
)
oauth_states = sa.Table(
    "oauth_states",
    metadata,
    sa.Column("state", sa.Text, primary_key=True),
    sa.Column("tenant_id", sa.Text, nullable=False),
    sa.Column("actor_id", sa.Text, nullable=False),
    sa.Column("connection_id", sa.Text, nullable=False),
    sa.Column("redirect_uri", sa.Text, nullable=False),
    sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
    sa.Column("consumed", sa.Boolean, nullable=False, server_default=sa.false()),
)
calendar_events = sa.Table(
    "calendar_events",
    metadata,
    sa.Column("tenant_id", sa.Text, primary_key=True),
    sa.Column("connection_id", sa.Text, primary_key=True),
    sa.Column("milestone_id", sa.Text, primary_key=True),
    sa.Column("provider_id", sa.Text, nullable=False),
    sa.Column("etag", sa.Text),
    sa.Column("projection_hash", sa.Text),
    sa.Column("state", sa.Text, nullable=False),
    sa.Column("provider_data", JSONB, nullable=False),
)
