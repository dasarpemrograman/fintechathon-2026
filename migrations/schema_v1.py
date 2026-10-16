"""Immutable initial database schema; later revisions must not edit this module."""

import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSONB

metadata = sa.MetaData()
organizations = sa.Table(
    "organizations",
    metadata,
    sa.Column("id", sa.Text, primary_key=True),
    sa.Column("name", sa.Text, nullable=False),
    sa.Column("dataset_id", sa.Text),
    sa.Column("policy", JSONB, nullable=False),
)
users = sa.Table(
    "users",
    metadata,
    sa.Column("id", sa.Text, primary_key=True),
    sa.Column("email", sa.Text, nullable=False, unique=True),
    sa.Column("display_name", sa.Text, nullable=False),
    sa.Column("password_hash", sa.Text),
    sa.Column("dataset_id", sa.Text),
    sa.Column("active", sa.Boolean, nullable=False, server_default="true"),
)
memberships = sa.Table(
    "memberships",
    metadata,
    sa.Column("id", sa.Text, primary_key=True),
    sa.Column(
        "organization_id", sa.Text, sa.ForeignKey("organizations.id"), nullable=False
    ),
    sa.Column("user_id", sa.Text, sa.ForeignKey("users.id"), nullable=False),
    sa.Column("roles", JSONB, nullable=False),
    sa.UniqueConstraint("organization_id", "user_id"),
)
sessions = sa.Table(
    "sessions",
    metadata,
    sa.Column("token_hash", sa.Text, primary_key=True),
    sa.Column("user_id", sa.Text, sa.ForeignKey("users.id"), nullable=False),
    sa.Column("organization_id", sa.Text, sa.ForeignKey("organizations.id")),
    sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
)
registry = sa.Table(
    "resource_registry",
    metadata,
    sa.Column(
        "tenant_id", sa.Text, sa.ForeignKey("organizations.id"), primary_key=True
    ),
    sa.Column("id", sa.Text, primary_key=True),
    sa.Column("kind", sa.Text, nullable=False),
    sa.Column("dataset_id", sa.Text),
    sa.UniqueConstraint("id"),
)
KINDS = (
    "workspace",
    "deal",
    "evidence",
    "document",
    "fact_candidate",
    "cost_line",
    "requirement",
    "fx_observation",
    "scenario",
    "analysis",
    "finance_product",
    "funding_option",
    "finance_options",
    "finance_pack",
    "artifact",
    "approval",
    "agreement",
    "milestone",
    "receipt",
    "obligation",
    "reconciliation",
    "run",
    "goods_review",
    "shipment_event",
    "reservation",
    "audit",
    "usage",
    "calendar_connection",
    "calendar_preview",
    "business_calendar",
)
records = {}
for kind in KINDS:
    records[kind] = sa.Table(
        kind + "_records",
        metadata,
        sa.Column("tenant_id", sa.Text, primary_key=True),
        sa.Column("id", sa.Text, primary_key=True),
        sa.Column("parent_id", sa.Text),
        sa.Column("revision", sa.Integer, nullable=False, server_default="1"),
        sa.Column("data", JSONB, nullable=False),
        sa.Column("amount", sa.Numeric),
        sa.Column("currency", sa.Text),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.ForeignKeyConstraint(
            ["tenant_id", "id"], ["resource_registry.tenant_id", "resource_registry.id"]
        ),
        sa.ForeignKeyConstraint(
            ["tenant_id", "parent_id"],
            ["resource_registry.tenant_id", "resource_registry.id"],
        ),
        sa.CheckConstraint("revision > 0"),
        sa.Index(kind + "_parent_idx", "tenant_id", "parent_id", "id"),
    )
references = sa.Table(
    "resource_references",
    metadata,
    sa.Column("tenant_id", sa.Text, primary_key=True),
    sa.Column("source_id", sa.Text, primary_key=True),
    sa.Column("target_id", sa.Text, primary_key=True),
    sa.ForeignKeyConstraint(
        ["tenant_id", "source_id"],
        ["resource_registry.tenant_id", "resource_registry.id"],
    ),
    sa.ForeignKeyConstraint(
        ["tenant_id", "target_id"],
        ["resource_registry.tenant_id", "resource_registry.id"],
    ),
)
snapshots = sa.Table(
    "snapshots",
    metadata,
    sa.Column("tenant_id", sa.Text, primary_key=True),
    sa.Column("resource_id", sa.Text, primary_key=True),
    sa.Column("revision", sa.Integer, primary_key=True),
    sa.Column("hash", sa.Text, nullable=False),
    sa.Column("data", JSONB, nullable=False),
    sa.Column(
        "created_at",
        sa.DateTime(timezone=True),
        nullable=False,
        server_default=sa.func.now(),
    ),
    sa.ForeignKeyConstraint(
        ["tenant_id", "resource_id"],
        ["resource_registry.tenant_id", "resource_registry.id"],
    ),
)
commands = sa.Table(
    "commands",
    metadata,
    sa.Column(
        "tenant_id", sa.Text, sa.ForeignKey("organizations.id"), primary_key=True
    ),
    sa.Column("actor_id", sa.Text, sa.ForeignKey("users.id"), primary_key=True),
    sa.Column("operation", sa.Text, primary_key=True),
    sa.Column("key", sa.Text, primary_key=True),
    sa.Column("request_hash", sa.Text, nullable=False),
    sa.Column("status", sa.Integer, nullable=False),
    sa.Column("response", JSONB, nullable=False),
    sa.Column(
        "created_at",
        sa.DateTime(timezone=True),
        nullable=False,
        server_default=sa.func.now(),
    ),
)
jobs = sa.Table(
    "jobs",
    metadata,
    sa.Column("tenant_id", sa.Text, primary_key=True),
    sa.Column("id", sa.Text, primary_key=True),
    sa.Column("payload", JSONB, nullable=False),
    sa.Column("state", sa.Text, nullable=False),
    sa.Column("attempts", sa.Integer, nullable=False, server_default="0"),
    sa.Column("lease_until", sa.DateTime(timezone=True)),
    sa.Column(
        "available_at",
        sa.DateTime(timezone=True),
        nullable=False,
        server_default=sa.func.now(),
    ),
    sa.Column("cancelled", sa.Boolean, nullable=False, server_default="false"),
    sa.ForeignKeyConstraint(
        ["tenant_id", "id"], ["resource_registry.tenant_id", "resource_registry.id"]
    ),
)
outbox = sa.Table(
    "outbox",
    metadata,
    sa.Column("tenant_id", sa.Text, primary_key=True),
    sa.Column("id", sa.Text, primary_key=True),
    sa.Column("effect_key", sa.Text, nullable=False),
    sa.Column("payload", JSONB, nullable=False),
    sa.Column("state", sa.Text, nullable=False),
    sa.Column("receipt", JSONB),
    sa.UniqueConstraint("tenant_id", "effect_key"),
    sa.ForeignKeyConstraint(["tenant_id"], ["organizations.id"]),
)
cash = sa.Table(
    "cash_ledgers",
    metadata,
    sa.Column(
        "tenant_id", sa.Text, sa.ForeignKey("organizations.id"), primary_key=True
    ),
    sa.Column("currency", sa.Text, primary_key=True),
    sa.Column("available", sa.Numeric, nullable=False),
    sa.Column("snapshot_hash", sa.Text, nullable=False),
    sa.CheckConstraint("available >= 0"),
)
