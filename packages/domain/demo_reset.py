"""Reset only known seed ownership, after checking every retained reference."""

import sqlalchemy as sa
from services.api import store
from services.api.store import DomainError
from services.api.settings import settings
from packages.domain.demo import DATASET


def identifiers(value):
    if isinstance(value, str):
        yield value
    elif isinstance(value, dict):
        for child in value.values():
            yield from identifiers(child)
    elif isinstance(value, list):
        for child in value:
            yield from identifiers(child)


def reset_dataset(conn, dataset, apply=False):
    if not settings.demo or dataset != DATASET:
        raise DomainError(
            "DEMO_RESET_DISABLED",
            "Reset requires explicit demo mode and the declared dataset.",
        )
    # Serialize all potentially affected tenants, including those with retained user records.
    tenants = (
        conn.execute(
            sa.select(store.organizations.c.id)
            .order_by(store.organizations.c.id)
            .with_for_update()
        )
        .scalars()
        .all()
    )
    seed = set(
        conn.execute(
            sa.select(store.registry.c.id).where(store.registry.c.dataset_id == dataset)
        ).scalars()
    )
    if not seed:
        return 0
    for table in store.records.values():
        rows = conn.execute(
            sa.select(table.c.id, table.c.parent_id, table.c.data)
            .join(
                store.registry,
                sa.and_(
                    table.c.tenant_id == store.registry.c.tenant_id,
                    table.c.id == store.registry.c.id,
                ),
            )
            .where(
                sa.or_(
                    store.registry.c.dataset_id.is_(None),
                    store.registry.c.dataset_id != dataset,
                )
            )
        ).mappings()
        for row in rows:
            if row["parent_id"] in seed or set(identifiers(row["data"])) & seed:
                raise DomainError(
                    "DEMO_MIXED_OWNERSHIP",
                    "A retained user record references demonstration data; export and detach it before resetting.",
                    409,
                )
    for row in conn.execute(
        sa.select(store.snapshots.c.resource_id, store.snapshots.c.data)
    ).mappings():
        if row["resource_id"] not in seed and set(identifiers(row["data"])) & seed:
            raise DomainError(
                "DEMO_HISTORY_DEPENDENCY",
                "Retained immutable history refers to the seed namespace.",
                409,
            )
    for row in conn.execute(sa.select(store.references)).mappings():
        if row["source_id"] not in seed and row["target_id"] in seed:
            raise DomainError(
                "DEMO_REFERENCE_DEPENDENCY",
                "A retained source depends on a demonstration record.",
                409,
            )
    from migrations.schema_v3 import (
        calendar_events,
        connector_credentials,
        oauth_states,
    )

    calendar_owned = []
    for event in conn.execute(sa.select(calendar_events)).mappings():
        if event["milestone_id"] not in seed and event["connection_id"] not in seed:
            continue
        connection = store.get(
            conn,
            event["tenant_id"],
            "calendar_connection",
            event["connection_id"],
            False,
        )
        if (
            not connection
            or connection["data_mode"] != "synthetic_demo"
            or event["milestone_id"] not in seed
        ):
            raise DomainError(
                "DEMO_CALENDAR_DEPENDENCY",
                "A retained or live Calendar event depends on this namespace; export and detach it before reset.",
                409,
            )
        # An offline projection is a derived copy of the seeded milestone.
        # Retain the separately owned connection and credentials, clearing only
        # the synthetic projection whose source is explicitly being reset.
        calendar_owned.append(
            (event["tenant_id"], event["connection_id"], event["milestone_id"])
        )
    if not apply:
        return len(seed)
    conn.execute(
        store.references.delete().where(store.references.c.source_id.in_(seed))
    )
    conn.execute(
        store.snapshots.delete().where(store.snapshots.c.resource_id.in_(seed))
    )
    conn.execute(store.jobs.delete().where(store.jobs.c.id.in_(seed)))
    # Command receipts can embed seeded IDs; remove only receipts which depend on the reset namespace.
    for row in conn.execute(sa.select(store.commands)).mappings():
        if set(identifiers(row["response"])) & seed:
            conn.execute(
                store.commands.delete().where(
                    store.commands.c.tenant_id == row["tenant_id"],
                    store.commands.c.actor_id == row["actor_id"],
                    store.commands.c.operation == row["operation"],
                    store.commands.c.key == row["key"],
                )
            )
    for row in conn.execute(sa.select(store.outbox)).mappings():
        if set(identifiers(row["payload"])) & seed:
            conn.execute(
                store.outbox.delete().where(
                    store.outbox.c.tenant_id == row["tenant_id"],
                    store.outbox.c.id == row["id"],
                )
            )
    for tenant, connection, milestone in calendar_owned:
        conn.execute(
            calendar_events.delete().where(
                calendar_events.c.tenant_id == tenant,
                calendar_events.c.connection_id == connection,
                calendar_events.c.milestone_id == milestone,
            )
        )
    conn.execute(
        connector_credentials.delete().where(
            connector_credentials.c.connection_id.in_(seed)
        )
    )
    conn.execute(oauth_states.delete().where(oauth_states.c.connection_id.in_(seed)))
    for table in store.records.values():
        conn.execute(table.delete().where(table.c.id.in_(seed)))
    conn.execute(store.registry.delete().where(store.registry.c.id.in_(seed)))
    # Content-addressed originals, memberships, users and cash snapshots are retained conservatively.
    # They may be shared with user-owned records; content garbage collection is a separate review.
    return len(seed)
