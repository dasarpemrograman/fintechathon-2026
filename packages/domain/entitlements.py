"""Versioned pilot allowances. No checkout, automatic overage or ledger deletion."""

from datetime import datetime, timezone
from copy import deepcopy
import json
import sqlalchemy as sa
from services.api import store
from services.api.settings import ROOT
from services.api.store import DomainError

CATALOG = json.loads((ROOT / "config/plans-v1.json").read_text())


def records(conn, tenant, kind):
    rows = []
    cursor = None
    while True:
        page = store.list_records(conn, tenant, kind, limit=100, cursor=cursor)
        rows += page["items"]
        cursor = page["next_cursor"]
        if cursor is None:
            return rows


def timestamp(value):
    return datetime.fromisoformat(value.replace("Z", "+00:00"))


def policy_view(conn, tenant, at=None):
    policy = conn.execute(
        sa.select(store.organizations.c.policy).where(
            store.organizations.c.id == tenant
        )
    ).scalar_one()
    plan = CATALOG["plans"][policy.get("plan", "free_sandbox")]
    now = at or store.now()
    start = (
        timestamp(policy["period_start"])
        if policy.get("period_start")
        else now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
    )
    if not plan["monthly"]:
        start = timestamp(
            policy.get("activated_at", policy.get("period_start", start.isoformat()))
        )
    expires = timestamp(policy["expires_at"]) if policy.get("expires_at") else None
    active = policy.get("active", True) and (expires is None or expires > now)
    return policy, plan, start, expires, active


def balance(conn, tenant, include_pending=True, at=None):
    policy, plan, start, expires, active = policy_view(conn, tenant, at)
    all_usage = records(conn, tenant, "usage")
    result = {}
    now = at or store.now()
    for unit, key in [("enriched_run", "runs"), ("document_page", "pages")]:
        field = "enriched_runs" if unit == "enriched_run" else "document_pages"
        included_used = 0
        addon_used = {}
        for row in all_usage:
            allocations = row.get("allocations")
            if allocations is None:
                if timestamp(row["created_at"]) >= start:
                    included_used += row[field]
            else:
                for allocation in allocations:
                    if allocation["unit"] != unit:
                        continue
                    if (
                        allocation["pool"] == "included"
                        and timestamp(allocation["period_start"]) == start
                    ):
                        included_used += allocation["quantity"]
                    elif allocation["pool"] == "addon":
                        addon_used[allocation["addon_id"]] = (
                            addon_used.get(allocation["addon_id"], 0)
                            + allocation["quantity"]
                        )
        included = max(0, policy.get(key, plan[key]) - included_used)
        addons = []
        for addon in policy.get("addons", []):
            if (
                policy.get("plan", "free_sandbox") == "free_sandbox"
                or addon["unit"] != unit
                or timestamp(addon["expires_at"]) <= now
                or not active
            ):
                continue
            addons.append(
                {
                    **addon,
                    "remaining": max(
                        0, addon["quantity"] - addon_used.get(addon["id"], 0)
                    ),
                }
            )
        addons.sort(key=lambda a: (a["expires_at"], a["id"]))
        pending = 0
        if include_pending:
            jobs = conn.execute(
                sa.select(store.jobs).where(
                    store.jobs.c.tenant_id == tenant,
                    store.jobs.c.state.in_(["queued", "running"]),
                    store.jobs.c.cancelled.is_(False),
                )
            ).mappings()
            for job in jobs:
                kind = job["payload"]["kind"]
                body = job["payload"]["body"]
                if unit == "document_page" and kind == "document_ingestion":
                    pending += body.get(
                        "expected_pages", len(body.get("document_ids", []))
                    )
                if unit == "enriched_run" and (
                    body.get("execution") == "enrich"
                    or kind in {"discovery", "finance_options"}
                    and not body.get("_deterministic_matching", False)
                ):
                    pending += 1
        from_included = min(included, pending)
        included -= from_included
        pending -= from_included
        for addon in addons:
            reserved = min(addon["remaining"], pending)
            addon["remaining"] -= reserved
            pending -= reserved
        result[unit] = {
            "included_remaining": included,
            "addon_remaining": sum(a["remaining"] for a in addons),
            "addons": addons,
            "expires_at": expires.isoformat() if expires else None,
        }
    return {
        "policy": policy,
        "plan": plan,
        "period_start": start.isoformat(),
        "active": active,
        "units": result,
        "version": policy.get("catalog_version", CATALOG["version"]),
    }


def allocations(conn, tenant, runs, pages, at=None):
    state = balance(conn, tenant, include_pending=False, at=at)
    result = []
    if (runs or pages) and not state["active"]:
        raise DomainError(
            "ENTITLEMENT_EXPIRED",
            "New provider work cannot be charged after entitlement expiry.",
            429,
        )
    for unit, quantity in [("enriched_run", runs), ("document_page", pages)]:
        pool = state["units"][unit]
        included = min(quantity, pool["included_remaining"])
        if included:
            result.append(
                {
                    "unit": unit,
                    "pool": "included",
                    "addon_id": None,
                    "quantity": included,
                    "period_start": state["period_start"],
                }
            )
        remaining = quantity - included
        for addon in pool["addons"]:
            count = min(remaining, addon["remaining"])
            if count:
                result.append(
                    {
                        "unit": unit,
                        "pool": "addon",
                        "addon_id": addon["id"],
                        "quantity": count,
                        "period_start": state["period_start"],
                    }
                )
                remaining -= count
        if remaining:
            raise DomainError(
                "ALLOWANCE_EXHAUSTED",
                "Successful work exceeds remaining included and unexpired add-on allowance.",
                429,
            )
    return result, state["version"]


def require_feature(conn, tenant, feature, exclude_workspace=None):
    policy, plan, _, _, active = policy_view(conn, tenant)
    if not active:
        raise DomainError(
            "ENTITLEMENT_EXPIRED",
            "New AI/discovery/draft work requires an active entitlement; existing records and manual settlements remain available.",
            429,
        )
    if (
        feature in {"deal", "negotiation", "finance_pack", "draft"}
        and policy.get("plan", "free_sandbox") == "free_sandbox"
    ):
        raise DomainError(
            "PAID_FEATURE_REQUIRED",
            "This feature requires a paid pilot entitlement provisioned by the local operator.",
            403,
        )
    if feature == "deal":
        active_deals = len(active_workspaces(conn, tenant, exclude_workspace))
        if active_deals >= policy.get("active_deals", plan["active_deals"]):
            raise DomainError(
                "ACTIVE_DEAL_LIMIT",
                "Active-deal capacity is exhausted; archive or close an existing deal or change entitlement.",
                429,
            )


def active_workspaces(conn, tenant, exclude_workspace=None):
    result = []
    for workspace in records(conn, tenant, "workspace"):
        if (
            workspace["id"] == exclude_workspace
            or workspace["archived"]
            or workspace["mode"] != "deal"
            and not workspace["deal_id"]
        ):
            continue
        deal = (
            store.get(conn, tenant, "deal", workspace["deal_id"], False)
            if workspace["deal_id"]
            else None
        )
        if deal and (
            deal["archived"] or deal["states"]["internal_closure"] == "closed"
        ):
            continue
        result.append(workspace["id"])
    return result
