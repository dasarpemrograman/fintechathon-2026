"""Authentication command receipts, encrypted at rest."""

import sqlalchemy as sa

metadata = sa.MetaData()
auth_commands = sa.Table(
    "auth_commands",
    metadata,
    sa.Column("actor_id", sa.Text, primary_key=True),
    sa.Column("operation", sa.Text, primary_key=True),
    sa.Column("key", sa.Text, primary_key=True),
    sa.Column("request_hash", sa.Text, nullable=False),
    sa.Column("receipt", sa.Text, nullable=False),
)
