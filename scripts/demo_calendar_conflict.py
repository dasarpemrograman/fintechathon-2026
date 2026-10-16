"""Simulate an external edit to an existing synthetic owned Calendar event."""

import argparse, sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import sqlalchemy as sa
from services.api import store, commands
from services.api.settings import settings
from migrations.schema_v3 import calendar_events
from packages.domain.demo import DATASET

parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument("--connection", required=True)
parser.add_argument("--milestone", required=True)
args = parser.parse_args()
if not settings.demo:
    raise SystemExit("Synthetic conflict simulation requires explicit demo mode.")
with store.engine.begin() as conn:
    owned = (
        conn.execute(
            sa.select(store.registry).where(
                store.registry.c.id == args.connection,
                store.registry.c.kind == "calendar_connection",
            )
        )
        .mappings()
        .one_or_none()
    )
    if not owned:
        raise SystemExit("Select a known synthetic connection.")
    milestone = (
        conn.execute(
            sa.select(store.registry).where(
                store.registry.c.id == args.milestone,
                store.registry.c.tenant_id == owned["tenant_id"],
                store.registry.c.dataset_id == DATASET,
            )
        )
        .mappings()
        .one_or_none()
    )
    if not milestone:
        raise SystemExit(
            "Simulation is limited to a milestone in the seeded namespace."
        )
    connection = store.get(
        conn, owned["tenant_id"], "calendar_connection", args.connection
    )
    if (
        connection["data_mode"] != "synthetic_demo"
        or connection["status"] != "connected"
    ):
        raise SystemExit("Select an active synthetic Calendar connection.")
    where = (
        calendar_events.c.tenant_id == owned["tenant_id"],
        calendar_events.c.connection_id == args.connection,
        calendar_events.c.milestone_id == args.milestone,
    )
    row = (
        conn.execute(sa.select(calendar_events).where(*where)).mappings().one_or_none()
    )
    if not row or row["state"] != "delivered":
        raise SystemExit(
            "First project the milestone through the approved offline outbox."
        )
    conn.execute(
        calendar_events.update()
        .where(*where)
        .values(
            state="conflict",
            etag='"synthetic-external-edit"',
            provider_data={**row["provider_data"], "_synthetic_external_edit": True},
        )
    )
    commands.audit(
        conn,
        {
            "tenant": owned["tenant_id"],
            "actor": connection["created_by"],
            "scope": "demo",
            "dataset": DATASET,
            "request_id": store.uid("demo_conflict"),
        },
        "synthetic_calendar_external_edit",
        {"state": row["state"], "milestone_id": args.milestone},
        {"state": "conflict", "milestone_id": args.milestone},
        args.connection,
    )
print(
    "Synthetic external edit recorded. Review the visible conflict before another projection."
)
