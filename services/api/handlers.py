"""HTTP operation adapters over persistent domain commands."""

from copy import deepcopy
from datetime import datetime, timezone
import json
import sqlalchemy as sa
from fastapi.responses import Response
from services.api import store, auth, commands, storage
from services.api.settings import settings
from services.api.store import DomainError, get, save, meta, uid, digest, issue
from packages.contracts.runtime import OPERATIONS

SEGMENTS = {
    "market-observations": "market_observation",
    "evidence": "evidence",
    "documents": "document",
    "fact-candidates": "fact_candidate",
    "analyses": "analysis",
    "scenarios": "scenario",
    "finance-options": "funding_option",
    "finance-products": "finance_product",
    "funding-options": "funding_option",
    "finance-packs": "finance_pack",
    "artifacts": "artifact",
    "cost-lines": "cost_line",
    "requirements": "requirement",
    "fx-observations": "fx_observation",
    "approvals": "approval",
    "agreements": "agreement",
    "milestones": "milestone",
    "receipts": "receipt",
    "obligations": "obligation",
    "reconciliations": "reconciliation",
    "goods-reviews": "goods_review",
    "shipment-events": "shipment_event",
    "reservations": "reservation",
    "audit": "audit",
    "usage": "usage",
    "business-calendars": "business_calendar",
}


def env(*args, **kwargs):
    from services.api.app import envelope

    return envelope(*args, **kwargs)


def verify_parent(conn, context, kind, identifier, parent):
    value = get(conn, context["tenant"], kind, identifier)
    if parent:
        table = store.records[kind]
        parent_id = conn.execute(
            sa.select(table.c.parent_id).where(
                table.c.id == identifier, table.c.tenant_id == context["tenant"]
            )
        ).scalar_one()
        if parent_id not in {parent["id"], parent.get("workspace_id")}:
            raise DomainError("NOT_FOUND", "Resource not found in this workspace.", 404)
    return value


def read_operation(conn, context, operation, parent, request):
    path = OPERATIONS[operation][0]
    params = request.path_params
    tenant = context["tenant"]
    if operation == "getDiagnostics":
        from collections import Counter
        from services.worker.liveness import ready

        job_rows = (
            conn.execute(sa.select(store.jobs).where(store.jobs.c.tenant_id == tenant))
            .mappings()
            .all()
        )
        queue = {
            state: sum(row["state"] == state for row in job_rows)
            for state in [
                "queued",
                "running",
                "succeeded",
                "partial",
                "failed",
                "cancelled",
            ]
        }
        queue["expired_leases"] = sum(
            row["state"] == "running"
            and row["lease_until"] is not None
            and row["lease_until"] < store.now()
            for row in job_rows
        )
        counts = Counter(
            item["code"]
            for run in commands.all_records(conn, tenant, "run")
            for item in run.get("blockers", []) + run.get("warnings", [])
        )
        stale = 0
        for deal in commands.all_records(conn, tenant, "deal"):
            stale += sum(
                not commands.analysis_view(conn, tenant, deal, row)["current_for_use"]
                for row in commands.children(conn, tenant, "analysis", deal)
            )
        return env(
            context,
            {
                "worker_ready": ready(),
                "queue": queue,
                "run_issues": [
                    {"code": code, "count": count}
                    for code, count in sorted(counts.items())
                ],
                "stale_analyses": stale,
            },
        )
    if operation == "getInputRevision":
        registry = (
            conn.execute(
                sa.select(store.registry).where(
                    store.registry.c.tenant_id == tenant,
                    store.registry.c.id == params["id"],
                )
            )
            .mappings()
            .first()
        )
        if not registry or registry["kind"] not in {
            "evidence",
            "cost_line",
            "fx_observation",
            "market_observation",
            "obligation",
            "receipt",
            "requirement",
            "milestone",
            "funding_option",
            "finance_product",
            "workspace",
            "deal",
        }:
            raise DomainError("NOT_FOUND", "Input not found.", 404)
        try:
            revision = int(params["revision"])
        except ValueError:
            raise DomainError("INVALID_REVISION", "Revision must be numeric.", 400)
        value = conn.execute(
            sa.select(store.snapshots.c.data).where(
                store.snapshots.c.tenant_id == tenant,
                store.snapshots.c.resource_id == params["id"],
                store.snapshots.c.revision == revision,
            )
        ).scalar_one_or_none()
        if value is None:
            raise DomainError("NOT_FOUND", "Input revision not found.", 404)
        return env(context, value)
    if operation == "getSession":
        return env(context, context["view"])
    if operation == "getWorkspace":
        return env(context, parent, parent)
    if operation == "getReviewContext":
        snapshot = parent["constraints"]["cash_snapshot"]
        return env(
            context,
            {
                "specification_hash": digest(parent["line_items"]),
                "cash_snapshot_hash": digest(snapshot) if snapshot else None,
            },
            parent,
        )
    if operation == "getGoodsSpecification":
        return env(
            context,
            {
                "line_items": parent["line_items"],
                "specification_hash": digest(parent["line_items"]),
            },
            parent,
        )
    if operation == "getDeal":
        return env(context, {"deal": parent, "invalidated_refs": []}, parent)
    if operation in {"getWorkspaceRevision", "getDealRevision"}:
        try:
            revision = int(params["revision"])
        except ValueError:
            raise DomainError("INVALID_REVISION", "Revision must be numeric.", 400)
        row = conn.execute(
            sa.select(store.snapshots.c.data).where(
                store.snapshots.c.tenant_id == tenant,
                store.snapshots.c.resource_id == parent["id"],
                store.snapshots.c.revision == revision,
            )
        ).scalar_one_or_none()
        if row is None:
            raise DomainError("NOT_FOUND", "Revision not found.", 404)
        return env(
            context,
            {"deal": row, "invalidated_refs": []}
            if operation == "getDealRevision"
            else row,
            row,
        )
    if operation.endswith("Revisions"):
        rows = list(
            conn.execute(
                sa.select(store.snapshots.c.data)
                .where(
                    store.snapshots.c.tenant_id == tenant,
                    store.snapshots.c.resource_id == parent["id"],
                )
                .order_by(store.snapshots.c.revision)
            ).scalars()
        )
        return env(context, {"items": rows, "next_cursor": None}, parent)
    if operation in {"exportWorkspace", "exportDeal"}:
        child_ids = list({parent["id"], parent.get("workspace_id", parent["id"])})
        for table in store.records.values():
            child_ids += list(
                conn.execute(
                    sa.select(table.c.id).where(
                        table.c.tenant_id == tenant,
                        table.c.parent_id.in_(
                            [parent["id"], parent.get("workspace_id", parent["id"])]
                        ),
                    )
                ).scalars()
            )
        history = list(
            conn.execute(
                sa.select(store.snapshots.c.data).where(
                    store.snapshots.c.tenant_id == tenant,
                    store.snapshots.c.resource_id.in_(child_ids),
                )
            ).scalars()
        )
        data = {
            "snapshot": parent,
            "evidence": commands.children(conn, tenant, "evidence", parent),
            "immutable_history": history,
        }
        return Response(
            json.dumps(data, ensure_ascii=False).encode(),
            media_type="application/octet-stream",
            headers={
                "Content-Disposition": 'attachment; filename="fincathon-export.json"'
            },
        )
    if "/content" in path:
        kind = "artifact" if "/artifacts/" in path else "document"
        value = verify_parent(conn, context, kind, params["resource_id"], parent)
        content = (
            value["content"].encode()
            if kind == "artifact"
            else storage.read_bytes(value["content_hash"])
        )
        return Response(
            content,
            media_type="application/octet-stream",
            headers={
                "Content-Disposition": 'attachment; filename="fincathon-'
                + kind
                + "."
                + ("md" if kind == "artifact" else "bin")
                + '"'
            },
        )
    if operation == "listMemberships":
        if params["id"] != tenant:
            raise DomainError("NOT_FOUND", "Organization not found.", 404)
        rows = conn.execute(
            sa.select(store.memberships, store.organizations.c.name)
            .join(
                store.organizations,
                store.organizations.c.id == store.memberships.c.organization_id,
            )
            .where(store.memberships.c.organization_id == tenant)
        ).mappings()
        return env(
            context,
            {
                "items": [
                    {
                        "id": r["id"],
                        "organization_id": tenant,
                        "user_id": r["user_id"],
                        "organization_name": r["name"],
                        "roles": r["roles"],
                    }
                    for r in rows
                ],
                "next_cursor": None,
            },
        )
    if operation == "getEntitlements":
        from packages.domain.entitlements import balance, active_workspaces

        state = balance(conn, tenant)
        result = {
            "plan": state["policy"].get("plan", "free_sandbox"),
            "status": "active" if state["active"] else "expired",
            "allowances": [
                {
                    "unit": unit,
                    "included_remaining": pool["included_remaining"],
                    "addon_remaining": pool["addon_remaining"],
                    "expires_at": pool["expires_at"],
                }
                for unit, pool in state["units"].items()
            ],
            "new_provider_work_allowed": commands.admission(conn, context)["admitted"],
            "existing_records_readable": True,
            "manual_obligations_and_receipts_allowed": True,
            "addons": [
                {
                    "id": a["id"],
                    "unit": unit,
                    "remaining": a["remaining"],
                    "expires_at": a["expires_at"],
                }
                for unit, pool in state["units"].items()
                for a in pool["addons"]
            ],
            "catalog_version": state["version"],
            "period_start": state["period_start"],
            "active_deal_limit": state["policy"].get(
                "active_deals", state["plan"]["active_deals"]
            ),
            "active_deals": len(active_workspaces(conn, tenant)),
            "user_limit": state["policy"].get("users", state["plan"]["users"]),
        }
        return env(context, result)
    if operation == "getCapabilities":
        return env(
            context,
            {
                "items": [
                    {
                        "name": name,
                        "state": "ready" if context["scope"] == "demo" else "blocked",
                        "mode": "synthetic_demo"
                        if context["scope"] == "demo"
                        else "live",
                        "reason": "Isolated offline fixture adapter."
                        if context["scope"] == "demo"
                        else "Live acceptance has not been recorded.",
                    }
                    for name in ["search", "fx", "model", "calendar"]
                ]
            },
        )
    if operation == "getReadiness":
        from packages.domain.workflow import readiness

        stage = request.query_params.get("stage")
        if stage not in {
            "analysis",
            "plan_review",
            "procurement_production",
            "booking",
            "shipment",
            "internal_close",
        }:
            raise DomainError("INVALID_STAGE", "Choose a declared readiness stage.")
        gate, blockers = readiness(conn, context, parent, stage)
        return env(
            context, gate, parent, "blocked" if blockers else "completed", blockers
        )
    if operation == "getRun":
        run = get(conn, tenant, "run", params["id"])
        parent_run = get(conn, tenant, "workspace", run["workspace_id"])
        response = env(
            context,
            run,
            parent_run,
            "partial" if run["status"] == "partial" else "completed",
        )
        response["revision"] = run["revision"]
        return response
    if operation == "listCalendarConnections":
        from migrations.schema_v3 import calendar_events

        page = store.list_records(conn, tenant, "calendar_connection", limit=100)
        for connection in page["items"]:
            events = (
                conn.execute(
                    sa.select(
                        calendar_events.c.milestone_id, calendar_events.c.state
                    ).where(
                        calendar_events.c.tenant_id == tenant,
                        calendar_events.c.connection_id == connection["id"],
                    )
                )
                .mappings()
                .all()
            )
            connection["owned_events"] = [dict(row) for row in events]
        return env(context, page)
    if operation.startswith("list"):
        segment = path.rsplit("/", 1)[-1]
        kind = (
            "workspace"
            if segment == "workspaces"
            else "deal"
            if segment == "deals"
            else SEGMENTS.get(segment)
        )
        if not kind:
            raise DomainError(
                "OPERATION_UNAVAILABLE",
                "Collection adapter has not been implemented.",
                503,
            )
        from services.api.app import collection_response

        return collection_response(conn, context, parent, kind, request)
    if "resource_id" in params:
        segment = path.split("/")[-2]
        kind = (
            "finance_options" if operation == "getFinanceOptions" else SEGMENTS[segment]
        )
        result = verify_parent(conn, context, kind, params["resource_id"], parent)
        if kind == "finance_options":
            result = {k: v for k, v in result.items() if k != "id"}
        if kind == "analysis":
            result = commands.analysis_view(conn, tenant, parent, result)
            return env(
                context,
                result,
                parent,
                "partial" if result["completeness"] == "partial" else "completed",
                result["blockers"],
                result["warnings"],
            )
        return env(context, result, parent)
    raise DomainError(
        "OPERATION_UNAVAILABLE", "This operation is not implemented yet.", 503
    )


def write_operation(conn, context, operation, parent, body, request=None):
    tenant = context["tenant"]
    actor = context["actor"]
    if operation == "logout":
        conn.execute(
            store.sessions.delete().where(
                store.sessions.c.token_hash == context["session"]["token_hash"]
            )
        )
        return env(context, {"message": "Session revoked."})
    if operation == "selectOrganization":
        selected = body["organization_id"]
        if not any(
            m["organization_id"] == selected for m in context["view"]["memberships"]
        ):
            raise DomainError("FORBIDDEN", "Organization membership required.", 403)
        conn.execute(
            store.sessions.update()
            .where(store.sessions.c.token_hash == context["session"]["token_hash"])
            .values(organization_id=selected)
        )
        view = deepcopy(context["view"])
        view["organization_id"] = selected
        return env(context, view)
    if operation == "createOrganization":
        identifier = uid("org")
        conn.execute(
            store.organizations.insert().values(
                id=identifier,
                name=body["name"],
                policy={"plan": "free_sandbox", "runs": 2, "pages": 10, "active": True},
            )
        )
        conn.execute(
            store.memberships.insert().values(
                id=uid("membership"),
                organization_id=identifier,
                user_id=actor,
                roles=["owner"],
            )
        )
        return env(context, {"id": identifier, "name": body["name"]})
    if operation == "setMembership":
        if request.path_params["id"] != tenant:
            raise DomainError("NOT_FOUND", "Organization not found.", 404)
        if not conn.execute(
            sa.select(store.users.c.id).where(store.users.c.id == body["user_id"])
        ).scalar_one_or_none():
            raise DomainError(
                "NOT_FOUND", "Provision the local user account first.", 404
            )
        existing = (
            conn.execute(
                sa.select(store.memberships).where(
                    store.memberships.c.organization_id == tenant,
                    store.memberships.c.user_id == body["user_id"],
                )
            )
            .mappings()
            .first()
        )
        if existing and "owner" in existing["roles"] and "owner" not in body["roles"]:
            owners = conn.execute(
                sa.select(sa.func.count())
                .select_from(store.memberships)
                .where(
                    store.memberships.c.organization_id == tenant,
                    store.memberships.c.roles.contains(["owner"]),
                )
            ).scalar_one()
            if owners <= 1:
                raise DomainError(
                    "LAST_OWNER_REQUIRED",
                    "Assign another owner before removing the final owner.",
                    409,
                )
        identifier = existing["id"] if existing else uid("membership")
        if not existing and body["roles"]:
            from packages.domain.entitlements import policy_view

            policy, plan, _, _, _ = policy_view(conn, tenant)
            count = conn.execute(
                sa.select(sa.func.count())
                .select_from(store.memberships)
                .where(store.memberships.c.organization_id == tenant)
            ).scalar_one()
            if count >= policy.get("users", plan["users"]):
                raise DomainError(
                    "MEMBER_ALLOWANCE_EXHAUSTED",
                    "This organization has reached its provisioned user allowance.",
                    429,
                )
        if not body["roles"]:
            if existing:
                conn.execute(
                    store.memberships.delete().where(
                        store.memberships.c.id == identifier,
                        store.memberships.c.organization_id == tenant,
                    )
                )
            conn.execute(
                store.sessions.update()
                .where(
                    store.sessions.c.user_id == body["user_id"],
                    store.sessions.c.organization_id == tenant,
                )
                .values(organization_id=None)
            )
        elif existing:
            conn.execute(
                store.memberships.update()
                .where(store.memberships.c.id == identifier)
                .values(roles=body["roles"])
            )
        else:
            conn.execute(
                store.memberships.insert().values(
                    id=identifier,
                    organization_id=tenant,
                    user_id=body["user_id"],
                    roles=body["roles"],
                )
            )
        name = conn.execute(
            sa.select(store.organizations.c.name).where(
                store.organizations.c.id == tenant
            )
        ).scalar_one()
        return env(
            context,
            {
                "id": identifier,
                "user_id": body["user_id"],
                "organization_id": tenant,
                "organization_name": name,
                "roles": body["roles"],
            },
        )
    if operation == "createWorkspace":
        value = commands.new_workspace(conn, context, body)
        return env(context, value, value)
    if operation == "convertToDeal":
        deal = commands.convert_deal(conn, context, parent, body)
        return env(context, {"deal": deal, "invalidated_refs": []}, deal)
    if operation in {"patchWorkspaceFacts", "patchDealFacts"}:
        inputs = (
            {
                kind: commands.children(conn, tenant, kind, parent)
                for kind in ["cost_line", "obligation"]
            }
            if operation == "patchDealFacts"
            else None
        )
        commands.patch_facts(
            conn,
            context,
            parent,
            body["patches"],
            "workspace" if operation == "patchWorkspaceFacts" else "deal",
        )
        if inputs is not None:
            costs, obligations = commands.analysis_inputs(
                conn, context, parent, inputs, body["patches"]
            )
            for kind, rows in [("cost_line", costs), ("obligation", obligations)]:
                for row in rows:
                    commands.evidence_refs(conn, tenant, parent, row["evidence_ids"])
                    save(
                        conn,
                        tenant,
                        kind,
                        row,
                        parent=parent["id"],
                        dataset=parent["dataset_id"],
                    )
            parent["cost_line_ids"] = [r["id"] for r in costs]
        return env(
            context,
            parent
            if operation == "patchWorkspaceFacts"
            else {"deal": parent, "invalidated_refs": []},
            parent,
        )
    if operation in {"archiveWorkspace", "archiveDeal"}:
        workspace_id = parent.get("workspace_id", parent["id"])
        workspace = get(conn, tenant, "workspace", workspace_id)
        if not body["archived"] and (
            workspace["mode"] == "deal" or workspace.get("deal_id")
        ):
            from packages.domain.entitlements import require_feature

            require_feature(conn, tenant, "deal", workspace_id)
        parent["archived"] = body["archived"]
        linked_kind = "workspace" if operation == "archiveDeal" else "deal"
        linked_id = (
            workspace_id if linked_kind == "workspace" else workspace.get("deal_id")
        )
        if linked_id:
            linked = get(conn, tenant, linked_kind, linked_id)
            linked.update(archived=body["archived"], revision=linked["revision"] + 1)
            save(
                conn,
                tenant,
                linked_kind,
                linked,
                parent=workspace_id if linked_kind == "deal" else None,
                dataset=linked["dataset_id"],
                snapshot=True,
            )
        return env(
            context,
            parent
            if operation == "archiveWorkspace"
            else {"deal": parent, "invalidated_refs": []},
            parent,
        )
    if operation == "estimateSandbox":
        from packages.domain.planning import estimate

        parent["planning_inputs"] = estimate(parent, body)
        return env(context, parent, parent)
    if operation == "previewUsage":
        return env(
            context,
            commands.admission(
                conn, context, body["execution"] == "enrich", body["document_pages"]
            ),
        )
    if operation == "cancelRun":
        run = get(conn, tenant, "run", request.path_params["id"])
        conn.execute(
            store.jobs.update()
            .where(store.jobs.c.tenant_id == tenant, store.jobs.c.id == run["id"])
            .values(cancelled=True)
        )
        if run["status"] in {"queued", "running"}:
            run["status"] = "cancelled"
            conn.execute(
                store.jobs.update()
                .where(store.jobs.c.tenant_id == tenant, store.jobs.c.id == run["id"])
                .values(state="cancelled", lease_until=None)
            )
            save(conn, tenant, "run", run, parent=run["workspace_id"])
        response = env(context, run)
        response.update(workspace_id=run["workspace_id"], revision=run["revision"])
        return response
    if operation == "createBusinessCalendar":
        row = {**meta(tenant, actor, "business_calendar"), **body}
        save(conn, tenant, "business_calendar", row)
        return env(context, row)
    if operation.startswith("ingest") and operation.endswith("Evidence"):
        values = deepcopy(body["evidence"])
        values["mode"] = (
            "synthetic_demo" if parent["execution_scope"] == "demo" else "user_provided"
        )
        values["review_status"] = "unreviewed"
        if values.get("canonical_url"):
            from urllib.parse import urlsplit

            try:
                source_url = urlsplit(values["canonical_url"])
                valid_url = (
                    source_url.scheme == "https"
                    and bool(source_url.hostname)
                    and not source_url.username
                    and not source_url.password
                    and source_url.port in {None, 443}
                )
            except ValueError:
                valid_url = False
            if not valid_url:
                raise DomainError(
                    "INVALID_SOURCE_URL",
                    "Use an HTTPS source URL without credentials and with the standard HTTPS port.",
                )
        if values["document_id"]:
            document = verify_parent(
                conn, context, "document", values["document_id"], parent
            )
            if values["content_hash"] != document["content_hash"]:
                raise DomainError(
                    "SOURCE_HASH_MISMATCH",
                    "Evidence does not match the uploaded original content hash.",
                )
            values["hash_scope"] = "original_document"
        elif values.get("hash_scope") == "manual_excerpt":
            import hashlib

            if (
                values["content_hash"]
                != hashlib.sha256(values["claim"].encode()).hexdigest()
            ):
                raise DomainError(
                    "SOURCE_HASH_MISMATCH",
                    "Excerpt hash does not match the supplied text.",
                )
        if not values["document_id"] and not values["canonical_url"]:
            raise DomainError(
                "SOURCE_REQUIRED", "Evidence must identify a source document or URL."
            )
        row = {**meta(tenant, actor, "evidence"), **values}
        save(
            conn,
            tenant,
            "evidence",
            row,
            parent=parent["id"],
            dataset=parent["dataset_id"],
        )
        if "evidence_ids" in parent:
            parent["evidence_ids"].append(row["id"])
        return env(context, row, parent)
    if operation in {
        "recordCostLine",
        "recordActualCharge",
        "recordFx",
        "recordObligation",
        "recordRequirement",
        "reviewRequirement",
        "reviewGoods",
        "recordShipmentEvent",
        "reserveCash",
        "reviewWorkspacesFact",
        "reviewDealsFact",
        "recordApproval",
        "recordAgreement",
        "recordMilestone",
        "recordReceipt",
        "verifyReceipt",
        "reconcileDeal",
        "closeDeal",
        "calculateBuyerRisk",
        "reviewEvidence",
        "reviewWorkspaceEvidence",
        "recordFinanceProduct",
        "recordFundingOption",
        "verifyCashResources",
        "recordMarketObservation",
    }:
        from services.api.review_handlers import execute_review

        return execute_review(conn, context, operation, parent, body)
    if operation in {
        "startDiscovery",
        "analyzeDeal",
        "createScenario",
        "discoverFinanceOptions",
        "prepareFinancePack",
        "generateDraft",
        "syncCalendar",
        "uploadDocuments",
        "retryDocument",
        "analyzeSandbox",
        "createSandboxScenario",
    }:
        from services.api.job_handlers import accept_job

        return accept_job(conn, context, operation, parent, body, request)
    if operation in {
        "connectCalendar",
        "calendarCallback",
        "selectCalendar",
        "revokeCalendar",
        "previewCalendar",
        "resolveCalendarConflict",
    }:
        from packages.adapters.calendar import calendar_command

        return calendar_command(conn, context, operation, parent, body, request)
    raise DomainError(
        "OPERATION_UNAVAILABLE", "This operation is not implemented yet.", 503
    )
