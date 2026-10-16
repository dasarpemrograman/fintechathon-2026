"""Canonical command acceptance over actual HTTP, database and worker services."""

from copy import deepcopy
import hashlib
import sqlalchemy as sa
from packages.contracts.runtime import OPERATIONS, DOCUMENT
from services.api import store, commands, auth
from services.worker.jobs import process
from migrations.schema_v3 import calendar_events


def exercise(case, conn, client, headers, deal, sandbox, source):
    tenant = "demo_org_id"
    actor = "demo_id_owner"

    def invoke(name, body=None, parent=None, params=None):
        path, method, definition = OPERATIONS[name]
        values = {"id": parent or deal["id"], **(params or {})}
        for key, value in values.items():
            path = path.replace("{" + key + "}", str(value))
        data = deepcopy(body or {})
        if definition["x-revision-scope"] in {"deal", "workspace"}:
            kind = "deal" if "/deals/" in path else "workspace"
            data["expected_revision"] = store.get(conn, tenant, kind, values["id"])[
                "revision"
            ]
        if "requestBody" in definition:
            invalid = client.request(
                method.upper(),
                path,
                json={**data, "unrecognized_protected_field": True},
                headers={**headers, "Idempotency-Key": store.uid("invalid_matrix")},
            )
            case.assertEqual(invalid.status_code, 422, (name, invalid.text[:400]))
        response = client.request(
            method.upper(),
            path,
            json=data,
            headers={**headers, "Idempotency-Key": store.uid("matrix_command")},
        )
        case.assertIn(
            response.status_code, {200, 201, 202}, (name, response.text[:600])
        )
        return response.json()["result"]

    def job(accepted):
        accepted = accepted.get("job", accepted)
        identifier = accepted["run"]["id"]
        row = dict(
            conn.execute(sa.select(store.jobs).where(store.jobs.c.id == identifier))
            .mappings()
            .one()
        )
        conn.execute(
            store.jobs.update()
            .where(store.jobs.c.id == identifier)
            .values(state="running", attempts=1)
        )
        run = process(row)
        case.assertIn(run["status"], {"succeeded", "partial"}, run.get("blockers"))
        return run

    def current():
        return store.get(conn, tenant, "deal", deal["id"])

    def fields(row, schema):
        return {
            key: deepcopy(value)
            for key, value in row.items()
            if key in DOCUMENT["components"]["schemas"][schema]["properties"]
        }

    proof = store.get(conn, tenant, "evidence", source)
    manual = fields(proof, "EvidenceInput")
    manual.update(
        document_id=None,
        canonical_url="https://synthetic.example.test/matrix",
        claim="Synthetic matrix quotation for review",
        content_hash=hashlib.sha256(
            b"Synthetic matrix quotation for review"
        ).hexdigest(),
        hash_scope="manual_excerpt",
        review_status="unreviewed",
    )
    new_source = invoke("ingestWorkspacesEvidence", {"evidence": manual}, sandbox["id"])
    invoke(
        "reviewWorkspaceEvidence",
        {
            "evidence_id": new_source["id"],
            "disposition": "confirmed",
            "reason": "Explicit synthetic source review",
        },
        sandbox["id"],
    )
    invoke(
        "reviewEvidence",
        {
            "evidence_id": source,
            "disposition": "confirmed",
            "reason": "Retain the current synthetic reference",
        },
    )
    job(
        invoke(
            "startDiscovery",
            {
                "categories": ["requirements", "fx"],
                "approved_public_terms": [],
                "budget": {
                    "max_queries": 2,
                    "max_pages": 2,
                    "max_actions": 4,
                    "max_provider_retries": 0,
                },
            },
            sandbox["id"],
        )
    )
    observation = fields(
        commands.children(conn, tenant, "fx_observation", current())[0], "FxInput"
    )
    cost = fields(
        commands.children(conn, tenant, "cost_line", current())[0], "CostLineInput"
    )
    cost.update(
        component_key="matrix_reviewed_fee",
        covered_components=["matrix_reviewed_fee"],
        category="bank_fee",
        basis="fixed",
        quantity=None,
        rate=None,
        estimate={
            "low": None,
            "base": {"amount": "1", "currency": "IDR"},
            "high": None,
        },
        actual_amount=None,
        percentage_rate=None,
        freight_input=None,
    )
    recorded = invoke("recordCostLine", {"cost_line_id": None, "line": cost})
    invoke(
        "recordActualCharge",
        {
            "cost_line_id": recorded["id"],
            "amount": {"amount": "1", "currency": "IDR"},
            "evidence_ids": [source],
            "reason": "Reviewed synthetic actual replaces the fee estimate",
        },
    )
    obligation = fields(
        commands.children(conn, tenant, "obligation", current())[0], "ObligationInput"
    )
    obligation["amount"] = {"amount": "1", "currency": "IDR"}
    invoke("recordObligation", {"obligation_id": None, "obligation": obligation})
    seller = next(p["id"] for p in current()["parties"] if "seller" in p["roles"])
    requirement = invoke(
        "recordRequirement",
        {
            "requirement": {
                "jurisdiction": "ID",
                "subject": "exporter",
                "category": "Synthetic matrix requirement",
                "applicability": "unresolved",
                "predicate_facts": ["Matrix fixture scope only"],
                "evidence_ids": [source],
                "fulfillment_status": "missing",
                "owner_party_id": seller,
                "fulfillment_evidence_ids": [],
                "reviewer_id": None,
                "review_due": None,
            }
        },
    )
    invoke(
        "reviewRequirement",
        {
            "requirement_id": requirement["id"],
            "applicability": "not_applicable",
            "fulfillment_status": "missing",
            "evidence_ids": [source],
            "reason": "Reviewed synthetic inapplicability for this fixture",
        },
    )
    invoke(
        "reviewGoods",
        {
            "shipment_id": None,
            "status": "evidence_review",
            "evidence_ids": [source],
            "reason": "Photographs do not establish unmeasured quality",
            "reviewed_specification_hash": store.digest(current()["line_items"]),
            "inspection_basis": "photos_only",
            "measurements": [],
        },
    )
    shipment = current()["shipments"][0]
    invoke(
        "recordShipmentEvent",
        {
            "shipment_id": shipment["id"],
            "kind": "in_transit",
            "occurred_at": "2026-10-15T12:00:00Z",
            "evidence_ids": [source],
            "exception_reason": "Synthetic external action recorded despite the unresolved conditions",
        },
    )
    snapshot_hash = store.digest(current()["constraints"]["cash_snapshot"])
    invoke(
        "verifyCashResources",
        {
            "cash_snapshot_hash": snapshot_hash,
            "evidence_ids": [source],
            "reason": "Reviewed synthetic opening resources",
        },
    )
    reservation = invoke(
        "reserveCash",
        {
            "reservation_id": None,
            "amount": {"amount": "1", "currency": "IDR"},
            "action": "reserve",
            "cash_snapshot_hash": snapshot_hash,
        },
    )
    invoke(
        "reserveCash",
        {
            "reservation_id": reservation["id"],
            "amount": reservation["amount"],
            "action": "release",
            "cash_snapshot_hash": snapshot_hash,
        },
    )
    invoke(
        "previewUsage",
        {"kind": "analysis", "execution": "deterministic", "document_pages": 0},
    )
    invoke(
        "createBusinessCalendar",
        {
            "name": "Synthetic weekdays",
            "timezone": "Asia/Jakarta",
            "weekend_days": [5, 6],
            "holidays": [],
        },
    )
    buyer = next(
        row
        for row in commands.children(conn, tenant, "obligation", current())
        if row["payee_party_id"] == seller
    )
    receipt = invoke(
        "recordReceipt",
        {
            "received_amount": {"amount": "1", "currency": "IDR"},
            "value_date": "2026-10-15",
            "allocations": [
                {
                    "obligation_id": buyer["id"],
                    "amount": {"amount": "1", "currency": "IDR"},
                }
            ],
            "evidence_ids": [source],
        },
    )
    invoke(
        "verifyReceipt",
        {
            "receipt_id": receipt["id"],
            "disposition": "verified",
            "evidence_ids": [source],
            "reason": "Review the actual synthetic bank proof",
            "settled_at": "2026-10-15T12:00:00Z",
        },
    )
    from test_pricing_treatment import PricingTreatmentTests

    market = fields(
        PricingTreatmentTests().observation(current()), "MarketObservationInput"
    )
    market["evidence_ids"] = [source]
    invoke("recordMarketObservation", {"observation": market})
    workspace = store.get(conn, tenant, "workspace", sandbox["id"])
    upload = client.post(
        "/v2/workspaces/" + sandbox["id"] + "/documents",
        data={
            "expected_revision": str(workspace["revision"]),
            "document_role": "quotation",
        },
        files={
            "files": (
                "synthetic-retry.txt",
                b"Quantity 12 kg\nUSD 350.00\n",
                "text/plain",
            )
        },
        headers={**headers, "Idempotency-Key": store.uid("matrix_upload")},
    )
    case.assertEqual(upload.status_code, 202, upload.text)
    job(upload.json()["result"]["job"])
    documents = commands.children(conn, tenant, "document", sandbox)
    document = documents[0]
    document.update(
        state="needs_review", parser_version="older-fixture-version", processed_pages=0
    )
    store.save(
        conn, tenant, "document", document, parent=sandbox["id"], dataset="demo-v1"
    )
    job(invoke("retryDocument", {}, sandbox["id"], {"resource_id": document["id"]}))
    # Resolve a deterministic candidate without replacing a protected field.
    for name, parent in [
        ("reviewDealsFact", current()),
        ("reviewWorkspacesFact", sandbox),
    ]:
        rows = commands.children(conn, tenant, "fact_candidate", parent)
        if rows:
            invoke(
                name,
                {
                    "candidate_id": rows[-1]["id"],
                    "disposition": "rejected",
                    "reason": "The synthetic alternative was explicitly rejected",
                    "patch": None,
                },
                parent["id"],
            )
    job(
        invoke(
            "analyzeDeal",
            {"scenario_id": None, "scope": "full", "execution": "deterministic"},
        )
    )
    analysis = commands.children(conn, tenant, "analysis", current())[-1]
    artifact_job = invoke(
        "generateDraft",
        {
            "scenario_id": analysis["scenario_id"],
            "analysis_id": analysis["id"],
            "kind": "recommendation",
            "recipient_party_id": None,
            "language": "id",
        },
    )
    job(artifact_job)
    invoke(
        "recordApproval",
        {
            "purpose": "plan",
            "analysis_hash": analysis["snapshot_hash"],
            "artifact_hash": None,
            "evidence_digest": analysis["evidence_digest"],
            "decision": "approved",
        },
    )
    party = next(p["id"] for p in current()["parties"] if "buyer" in p["roles"])
    invoke(
        "recordAgreement",
        {
            "party_id": party,
            "accepted_revision": current()["revision"],
            "evidence_ids": [source],
        },
    )
    invoke(
        "calculateBuyerRisk",
        {
            "scenario_id": analysis["scenario_id"],
            "kind": "partial",
            "delay_days": 20,
            "receipt_fraction": "0.5",
        },
    )
    queued = invoke(
        "analyzeDeal",
        {"scenario_id": None, "scope": "full", "execution": "deterministic"},
    )
    invoke("cancelRun", {}, params={"id": queued["run"]["id"]})
    planning = {
        "quantity": "10",
        "unit": "kg",
        "unit_cost": {"amount": "35", "currency": "IDR"},
        "invoice_amount": {"amount": "500", "currency": "IDR"},
        "deposit_amount": {"amount": "0", "currency": "IDR"},
        "deposit_at": {"instant": "2026-10-16T12:00:00Z", "timezone": "Asia/Jakarta"},
        "balance_at": {"instant": "2026-12-10T12:00:00Z", "timezone": "Asia/Jakarta"},
        "supplier_payment_at": {
            "instant": "2026-10-17T12:00:00Z",
            "timezone": "Asia/Jakarta",
        },
        "cash_snapshot": {
            "available": {"amount": "100", "currency": "IDR"},
            "committed_elsewhere": {"amount": "0", "currency": "IDR"},
            "minimum_buffer": {"amount": "0", "currency": "IDR"},
            "as_of": "2026-10-16T00:00:00Z",
        },
        "target_margin": None,
        "evidence_ids": [new_source["id"]],
    }
    invoke("estimateSandbox", planning, sandbox["id"])
    job(
        invoke(
            "analyzeSandbox",
            {"scenario_id": None, "scope": "full", "execution": "deterministic"},
            sandbox["id"],
        )
    )
    root = store.get(conn, tenant, "workspace", sandbox["id"])
    job(
        invoke(
            "createSandboxScenario",
            {
                "base_revision": {"id": root["id"], "revision": root["revision"]},
                "patches": [],
                "funding_option_ids": [],
            },
            sandbox["id"],
        )
    )
    connection_request = invoke(
        "connectCalendar",
        {"redirect_uri": "http://localhost:3000/oauth/calendar/callback"},
    )
    connection = invoke(
        "calendarCallback",
        {"state": connection_request["state"], "code": "offline-demo"},
    )
    invoke(
        "selectCalendar",
        {"calendar_id": "synthetic-local"},
        params={"id": connection["id"]},
    )
    milestone = commands.children(conn, tenant, "milestone", current())[-1]
    preview_body = {
        "connection_id": connection["id"],
        "milestone_ids": [milestone["id"]],
        "action": "insert",
    }
    preview = invoke("previewCalendar", preview_body)
    invoke(
        "recordApproval",
        {
            "purpose": "calendar_write",
            "analysis_hash": preview["projection_hash"],
            "artifact_hash": None,
            "evidence_digest": preview["projection_hash"],
            "decision": "approved",
        },
    )
    job(
        invoke(
            "syncCalendar",
            {**preview_body, "approved_projection_hash": preview["projection_hash"]},
        )
    )
    from packages.adapters.calendar import deliver_once

    deliver_once()
    conn.execute(
        calendar_events.update()
        .where(
            calendar_events.c.tenant_id == tenant,
            calendar_events.c.connection_id == connection["id"],
            calendar_events.c.milestone_id == milestone["id"],
        )
        .values(state="conflict")
    )
    invoke(
        "resolveCalendarConflict",
        {
            "connection_id": connection["id"],
            "milestone_id": milestone["id"],
            "decision": "keep_external",
        },
    )
    invoke("revokeCalendar", {}, params={"id": connection["id"]})
    invoke("archiveDeal", {"archived": True})
    invoke("archiveDeal", {"archived": False})
    invoke("createOrganization", {"name": "Synthetic additional organization"})
    user = (
        conn.execute(sa.select(store.users).where(store.users.c.id == actor))
        .mappings()
        .one()
    )
    other_token = auth.create_session(conn, user)["access_token"]
    response = client.post(
        "/v2/auth/logout",
        json={},
        headers={
            "Authorization": "Bearer " + other_token,
            "Idempotency-Key": store.uid("logout"),
        },
    )
    case.assertEqual(response.status_code, 200, response.text)
