"""Tenant-scoped PostgreSQL persistence. Wire payloads are canonical-schema validated."""

from copy import deepcopy
from datetime import datetime, timezone
from decimal import Decimal
import hashlib, json, secrets, unicodedata
from contextvars import ContextVar
from contextlib import contextmanager
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import insert
from services.api.settings import settings
from migrations.schema_v1 import (
    organizations,
    users,
    memberships,
    sessions,
    registry,
    records,
    references,
    snapshots,
    commands,
    jobs,
    outbox,
    cash,
)
from migrations.schema_v4 import market_observations
from migrations.schema_v5 import outbox

records = {**records, "market_observation": market_observations}
engine = sa.create_engine(settings.database_url, pool_pre_ping=True)


def now():
    return datetime.now(timezone.utc)


def instant():
    return now().isoformat().replace("+00:00", "Z")


_seed_ids = ContextVar("allexport_seed_ids", default=None)


@contextmanager
def deterministic_ids(namespace):
    token = _seed_ids.set([namespace, 0])
    try:
        yield
    finally:
        _seed_ids.reset(token)


def uid(prefix):
    stream = _seed_ids.get()
    if stream is None:
        return prefix + "_" + secrets.token_hex(12)
    stream[1] += 1
    return (
        prefix
        + "_"
        + hashlib.sha256(
            (stream[0] + ":" + prefix + ":" + str(stream[1])).encode()
        ).hexdigest()[:24]
    )


def normalized(value):
    if isinstance(value, str):
        return unicodedata.normalize("NFC", value)
    if isinstance(value, list):
        return [normalized(v) for v in value]
    if isinstance(value, dict):
        return {
            unicodedata.normalize("NFC", k): normalized(v) for k, v in value.items()
        }
    return value


def digest(value):
    return hashlib.sha256(
        json.dumps(
            normalized(value),
            sort_keys=True,
            separators=(",", ":"),
            ensure_ascii=False,
            allow_nan=False,
        ).encode()
    ).hexdigest()


class DomainError(Exception):
    def __init__(
        self,
        code,
        reason,
        status=422,
        field=None,
        action="Review the supplied inputs.",
        current_revision=None,
    ):
        super().__init__(reason)
        self.code = code
        self.reason = reason
        self.status = status
        self.field = field
        self.action = action
        self.current_revision = current_revision


def issue(
    code, reason, field=None, action="Review the missing evidence.", evidence=None
):
    return {
        "code": code,
        "field_path": field,
        "reason": reason,
        "required_action": action,
        "evidence_refs": evidence or [],
    }


def meta(tenant, actor, kind, identifier=None):
    return {
        "id": identifier or uid(kind),
        "tenant_id": tenant,
        "created_at": instant(),
        "created_by": actor,
    }


def get(conn, tenant, kind, identifier, required=True):
    row = conn.execute(
        sa.select(records[kind].c.data).where(
            records[kind].c.tenant_id == tenant, records[kind].c.id == identifier
        )
    ).scalar_one_or_none()
    if row is None and required:
        raise DomainError("NOT_FOUND", "Resource not found.", 404)
    return deepcopy(row) if row is not None else None


def list_records(conn, tenant, kind, parent=None, limit=25, cursor=None):
    table = records[kind]
    query = sa.select(table.c.data).where(table.c.tenant_id == tenant)
    if parent is not None:
        query = query.where(table.c.parent_id == parent)
    if cursor:
        query = query.where(table.c.id > cursor)
    rows = list(conn.execute(query.order_by(table.c.id).limit(limit + 1)).scalars())
    return {
        "items": deepcopy(rows[:limit]),
        "next_cursor": rows[limit - 1]["id"] if len(rows) > limit else None,
    }


def save(conn, tenant, kind, data, parent=None, dataset=None, snapshot=False):
    if "tenant_id" in data and data["tenant_id"] != tenant:
        raise DomainError("TENANT_MISMATCH", "Resource tenant mismatch.", 404)
    identifier = data["id"]
    existing = (
        conn.execute(sa.select(registry).where(registry.c.id == identifier))
        .mappings()
        .first()
    )
    if existing and (existing["tenant_id"] != tenant or existing["kind"] != kind):
        raise DomainError("REFERENCE_MISMATCH", "Resource reference mismatch.", 404)
    conn.execute(
        insert(registry)
        .values(tenant_id=tenant, id=identifier, kind=kind, dataset_id=dataset)
        .on_conflict_do_nothing()
    )
    current = (
        conn.execute(
            sa.select(records[kind].c.revision, records[kind].c.data).where(
                records[kind].c.tenant_id == tenant, records[kind].c.id == identifier
            )
        )
        .mappings()
        .first()
    )
    if current and digest(current["data"]) == digest(data):
        return deepcopy(data)
    version = (
        data["revision"]
        if kind in {"workspace", "deal"}
        else current["revision"] + 1
        if current
        else 1
    )
    amount = (
        data.get("received_amount") or data.get("amount") or data.get("actual_amount")
    )
    values = {
        "tenant_id": tenant,
        "id": identifier,
        "parent_id": parent,
        "revision": version,
        "data": data,
        "amount": Decimal(amount["amount"])
        if isinstance(amount, dict) and "amount" in amount
        else None,
        "currency": amount.get("currency") if isinstance(amount, dict) else None,
    }
    conn.execute(
        insert(records[kind])
        .values(**values)
        .on_conflict_do_update(
            index_elements=["tenant_id", "id"],
            set_={k: v for k, v in values.items() if k not in ("tenant_id", "id")},
        )
    )
    # Every mutable resource retains the exact old wire payload for replay/lineage.
    conn.execute(
        insert(snapshots)
        .values(
            tenant_id=tenant,
            resource_id=identifier,
            revision=version,
            hash=digest(data),
            data=data,
        )
        .on_conflict_do_nothing()
    )
    return deepcopy(data)


def assert_ref(conn, tenant, identifier, kind=None, scope=None):
    row = (
        conn.execute(
            sa.select(registry).where(
                registry.c.id == identifier, registry.c.tenant_id == tenant
            )
        )
        .mappings()
        .first()
    )
    if not row or (kind and row["kind"] != kind):
        raise DomainError(
            "INVALID_REFERENCE",
            "A referenced resource is unavailable in this organization.",
            404,
        )
    if scope == "real":
        current = row
        visited = set()
        while current:
            if current["id"] in visited:
                raise DomainError("REFERENCE_CYCLE", "Invalid resource ancestry.")
            visited.add(current["id"])
            data = get(conn, tenant, current["kind"], current["id"])
            if (
                current["dataset_id"]
                or data.get("execution_scope") == "demo"
                or data.get("mode") == "synthetic_demo"
            ):
                raise DomainError(
                    "SYNTHETIC_REFERENCE",
                    "Synthetic evidence cannot authorize a real workspace.",
                    422,
                )
            table = records[current["kind"]]
            parent_id = conn.execute(
                sa.select(table.c.parent_id).where(
                    table.c.id == current["id"], table.c.tenant_id == tenant
                )
            ).scalar_one()
            current = (
                conn.execute(
                    sa.select(registry).where(
                        registry.c.id == parent_id, registry.c.tenant_id == tenant
                    )
                )
                .mappings()
                .first()
                if parent_id
                else None
            )
    return row


def reference(conn, tenant, source, target, scope=None):
    assert_ref(conn, tenant, target, scope=scope)
    conn.execute(
        insert(references)
        .values(tenant_id=tenant, source_id=source, target_id=target)
        .on_conflict_do_nothing()
    )
