"""Resumable synthetic checkpoints built through normal commands and calculations."""

from copy import deepcopy
from datetime import datetime, timezone
from decimal import Decimal
import sqlalchemy as sa
from packages.domain.demo import DATASET, MANIFEST, financial_case, call, transaction
from services.api import store, commands
from services.api.settings import settings
from services.api.store import DomainError, get, save, digest, uid
from services.worker.jobs import run_once

STAGES = ["negotiation", "blocked_goods", "reconciling", "closed"]


def drain():
    import time

    deadline = time.monotonic() + 120
    for _ in range(600):
        result = run_once(scope="demo", dataset=DATASET)
        if result is None:
            with store.engine.connect() as conn:
                pending = conn.execute(
                    sa.select(sa.func.count())
                    .select_from(
                        store.jobs.join(
                            store.registry,
                            sa.and_(
                                store.registry.c.tenant_id == store.jobs.c.tenant_id,
                                store.registry.c.id == store.jobs.c.id,
                            ),
                        )
                    )
                    .where(
                        store.registry.c.dataset_id == DATASET,
                        store.jobs.c.state.in_(["queued", "running"]),
                        store.jobs.c.cancelled.is_(False),
                    )
                ).scalar_one()
            if not pending:
                return
            if time.monotonic() > deadline:
                break
            time.sleep(0.2)
    raise DomainError(
        "SEED_JOB_BUDGET",
        "Seed jobs did not complete within the namespace drain budget; inspect their run records.",
    )


def extra_cost(component, amount, currency, seller, ops, terms, source):
    return {
        "component_key": component,
        "category": component,
        "location": "declared synthetic route",
        "payer_party_id": seller,
        "economic_bearer_party_id": seller,
        "basis": "fixed",
        "quantity": "1",
        "unit": "deal",
        "rate": None,
        "minimum_charge": None,
        "calculation_rule_ref": None,
        "estimate": {
            "low": None,
            "base": {"amount": amount, "currency": currency},
            "high": None,
        },
        "evidence_ids": [source],
        "covered_components": [component],
        "treatment": "expense",
        "allocations": [],
        "payment_term_ids": [
            t["id"]
            for t in terms
            if t["payee_id"] == ops and t["amount"]["amount"] == amount
        ],
        "status": "user_assumed",
        "conditional": False,
        "valid_until": None,
        "actual_amount": None,
        "unknowns": [],
        "cash_treatment": "scheduled",
    }


def phase(conn, tenant, parent):
    rows = commands.children(conn, tenant, "audit", parent)
    return max(
        (
            int(r["action"].rsplit("_", 1)[1])
            for r in rows
            if r["action"].startswith("seed_checkpoint_")
        ),
        default=0,
    )


def checkpoint(conn, context, parent, n):
    commands.audit(
        conn, context, "seed_checkpoint_" + str(n), parent, parent, parent["id"]
    )


def seed_sandbox_plans():
    if not settings.demo:
        raise DomainError("DEMO_MODE_REQUIRED", "Sandbox seed requires demo mode.")
    for case in MANIFEST["cases"]:
        tenant = "demo_org_" + case["organization"]
        identifier = "demo_" + case["key"] + "_sandbox"
        context = {
            "tenant": tenant,
            "actor": "demo_" + case["organization"] + "_owner",
            "roles": ["owner"],
            "scope": "demo",
            "dataset": DATASET,
            "request_id": uid("request"),
        }
        with (
            store.deterministic_ids(identifier + "-planning"),
            transaction(tenant) as conn,
        ):
            parent = get(conn, tenant, "workspace", identifier)
            if parent.get("planning_inputs"):
                continue
            # A source URL is only an explicit synthetic fixture label; no retrieval occurs.
            template = get(conn, tenant, "workspace", "demo_" + case["key"] + "_deal")
            deal = get(conn, tenant, "deal", template["deal_id"])
            source = deepcopy(commands.children(conn, tenant, "evidence", deal)[0])
            source = {
                k: v
                for k, v in source.items()
                if k not in {"id", "tenant_id", "created_at", "created_by"}
            }
            source.update(
                document_id=None,
                canonical_url="https://synthetic.example.test/" + case["key"],
                mode="synthetic_demo",
                review_status="unreviewed",
            )
            evidence = call(
                conn,
                context,
                "ingestWorkspacesEvidence",
                parent,
                {"expected_revision": parent["revision"], "evidence": source},
            )
            inputs, components, seller, ops = financial_case(
                case,
                datetime.fromisoformat(MANIFEST["reference_date"]).replace(
                    tzinfo=timezone.utc
                ),
                evidence["id"],
            )
            inputs.update(
                cost_lines=[
                    extra_cost(
                        k,
                        v,
                        case["currency"],
                        seller,
                        ops,
                        inputs["payment_terms"],
                        evidence["id"],
                    )
                    for k, v in components
                    if k
                    not in {"procurement", "materials", "labor", "process", "overhead"}
                ],
                fx_observations=[],
            )
            call(
                conn,
                context,
                "patchWorkspaceFacts",
                parent,
                {
                    "expected_revision": parent["revision"],
                    "patches": [
                        {
                            "op": "replace",
                            "path": "/planning_inputs",
                            "value": inputs,
                            "reason": "Versioned synthetic planning inputs",
                            "evidence_ids": [evidence["id"]],
                            "agreement_required_from": [],
                        }
                    ],
                },
            )
            call(
                conn,
                context,
                "analyzeSandbox",
                parent,
                {
                    "expected_revision": parent["revision"],
                    "scope": "full",
                    "execution": "deterministic",
                    "scenario_id": None,
                },
            )
    drain()


def seed_stages():
    if not settings.demo:
        raise DomainError("DEMO_MODE_REQUIRED", "Staged histories require demo mode.")
    tenant = "demo_org_id"
    actor = "demo_id_owner"
    created = []
    for stage in STAGES:
        identifier = "demo_stage_" + stage
        context = {
            "tenant": tenant,
            "actor": actor,
            "roles": ["owner"],
            "scope": "demo",
            "dataset": DATASET,
            "request_id": uid("request"),
        }
        # Phase 1 preserves the original loss-of-liquidity baseline before negotiation.
        with (
            store.deterministic_ids(identifier + "-phase1"),
            transaction(tenant) as conn,
        ):
            workspace = get(conn, tenant, "workspace", identifier, False)
            if not workspace:
                workspace = commands.new_workspace(
                    conn,
                    context,
                    {
                        "mode": "deal",
                        "business_profile": "reseller",
                        "seller_domicile": "ID",
                        "dispatch_country": "ID",
                        "destination_country": "SG",
                        "reporting_currency": "IDR",
                        "owner_timezone": "Asia/Jakarta",
                        "product": {
                            "description": "Synthetic coffee · "
                            + stage.replace("_", " ")
                        },
                    },
                    identifier=identifier,
                    dataset=DATASET,
                )
                source = deepcopy(
                    commands.children(
                        conn,
                        tenant,
                        "evidence",
                        get(
                            conn,
                            tenant,
                            "deal",
                            get(conn, tenant, "workspace", "demo_id-reseller_deal")[
                                "deal_id"
                            ],
                        ),
                    )[0]
                )
                source = {
                    k: v
                    for k, v in source.items()
                    if k not in {"id", "tenant_id", "created_at", "created_by"}
                }
                source.update(
                    document_id=None,
                    canonical_url="https://synthetic.example.test/checkpoints/" + stage,
                    review_status="unreviewed",
                    claim="SYNTHETIC CHECKPOINT: invented bank confirmation, counterparty acceptance, measurements and payment proof. Not usable outside demo scope.",
                )
                source = call(
                    conn,
                    context,
                    "ingestWorkspacesEvidence",
                    workspace,
                    {"expected_revision": workspace["revision"], "evidence": source},
                )
                case = deepcopy(
                    next(c for c in MANIFEST["cases"] if c["key"] == "id-reseller")
                )
                case.update(
                    key="stage-" + stage, product=workspace["product"]["description"]
                )
                body, components, seller, ops = financial_case(
                    case, datetime(2026, 8, 1, tzinfo=timezone.utc), source["id"]
                )
                deal = call(
                    conn,
                    context,
                    "convertToDeal",
                    workspace,
                    {"expected_revision": workspace["revision"], **body},
                )["deal"]
                for k, v in components:
                    if k == "procurement":
                        continue
                    call(
                        conn,
                        context,
                        "recordCostLine",
                        deal,
                        {
                            "expected_revision": deal["revision"],
                            "cost_line_id": None,
                            "line": extra_cost(
                                k,
                                v,
                                "IDR",
                                seller,
                                ops,
                                body["payment_terms"],
                                source["id"],
                            ),
                        },
                    )
                call(
                    conn,
                    context,
                    "analyzeDeal",
                    deal,
                    {
                        "expected_revision": deal["revision"],
                        "scenario_id": None,
                        "scope": "full",
                        "execution": "deterministic",
                    },
                )
                checkpoint(conn, context, deal, 1)
            elif workspace["dataset_id"] != DATASET:
                raise DomainError(
                    "SEED_OWNERSHIP", "A checkpoint ID belongs to retained user data."
                )
        drain()
        # Phase 2 negotiates a larger deposit and recalculates the shared plan.
        with (
            store.deterministic_ids(identifier + "-phase2"),
            transaction(tenant) as conn,
        ):
            workspace = get(conn, tenant, "workspace", identifier)
            deal = get(conn, tenant, "deal", workspace["deal_id"])
            if phase(conn, tenant, deal) < 2:
                evidence = commands.children(conn, tenant, "evidence", deal)[0]
                terms = deepcopy(deal["payment_terms"])
                buyers = [t for t in terms if t["side"] == "buyer"]
                buyers[0]["amount"]["amount"] = "96000000"
                buyers[-1]["amount"]["amount"] = "64000000"
                patch = {
                    "op": "replace",
                    "path": "/payment_terms",
                    "value": terms,
                    "reason": "Synthetic joint deposit/balance negotiation",
                    "evidence_ids": [evidence["id"]],
                    "agreement_required_from": [t["payer_id"] for t in buyers],
                }
                call(
                    conn,
                    context,
                    "patchDealFacts",
                    deal,
                    {"expected_revision": deal["revision"], "patches": [patch]},
                )
                call(
                    conn,
                    context,
                    "analyzeDeal",
                    deal,
                    {
                        "expected_revision": deal["revision"],
                        "scenario_id": None,
                        "scope": "full",
                        "execution": "deterministic",
                    },
                )
                checkpoint(conn, context, deal, 2)
        drain()
        # Phase 3 adds reviewed evidence and append-only settlement facts.
        with (
            store.deterministic_ids(identifier + "-phase3"),
            transaction(tenant) as conn,
        ):
            deal = get(
                conn,
                tenant,
                "deal",
                get(conn, tenant, "workspace", identifier)["deal_id"],
            )
            if phase(conn, tenant, deal) < 3:
                source = commands.children(conn, tenant, "evidence", deal)[0]
                call(
                    conn,
                    context,
                    "reviewEvidence",
                    deal,
                    {
                        "expected_revision": deal["revision"],
                        "evidence_id": source["id"],
                        "disposition": "confirmed",
                        "reason": "Explicit synthetic fixture review",
                    },
                )
                seller = next(
                    p["id"] for p in deal["parties"] if "seller" in p["roles"]
                )
                buyer = next(p["id"] for p in deal["parties"] if "buyer" in p["roles"])
                requirement = {
                    "jurisdiction": "SG",
                    "subject": "shipment",
                    "category": "Synthetic inspection and export checklist",
                    "applicability": "applies",
                    "predicate_facts": ["Demo fixture only; no live regulatory claim"],
                    "evidence_ids": [source["id"]],
                    "fulfillment_status": "verified",
                    "owner_party_id": seller,
                    "fulfillment_evidence_ids": [source["id"]],
                    "reviewer_id": None,
                    "review_due": None,
                }
                call(
                    conn,
                    context,
                    "recordRequirement",
                    deal,
                    {"expected_revision": deal["revision"], "requirement": requirement},
                )
                if stage != "negotiation":
                    call(
                        conn,
                        context,
                        "verifyCashResources",
                        deal,
                        {
                            "expected_revision": deal["revision"],
                            "cash_snapshot_hash": digest(
                                deal["constraints"]["cash_snapshot"]
                            ),
                            "evidence_ids": [source["id"]],
                            "reason": "Synthetic opening bank balance confirmation",
                        },
                    )
                    for obligation in commands.children(
                        conn, tenant, "obligation", deal
                    ):
                        is_buyer = obligation["payer_party_id"] == buyer
                        if stage == "blocked_goods" and (
                            not is_buyer or obligation["amount"]["amount"] != "96000000"
                        ):
                            continue
                        if stage == "reconciling" and not is_buyer:
                            continue
                        receipt = call(
                            conn,
                            context,
                            "recordReceipt",
                            deal,
                            {
                                "expected_revision": deal["revision"],
                                "received_amount": obligation["amount"],
                                "value_date": obligation["schedule"]["due"]["instant"][
                                    :10
                                ],
                                "allocations": [
                                    {
                                        "obligation_id": obligation["id"],
                                        "amount": obligation["amount"],
                                    }
                                ],
                                "evidence_ids": [source["id"]],
                            },
                        )
                        call(
                            conn,
                            context,
                            "verifyReceipt",
                            deal,
                            {
                                "expected_revision": deal["revision"],
                                "receipt_id": receipt["id"],
                                "disposition": "verified",
                                "evidence_ids": [source["id"]],
                                "reason": "Synthetic externally performed payment confirmation",
                                "settled_at": obligation["schedule"]["due"]["instant"],
                            },
                        )
                    if stage == "closed":
                        from packages.domain.economics import cost_amount, output

                        for cost in commands.children(conn, tenant, "cost_line", deal):
                            call(
                                conn,
                                context,
                                "recordActualCharge",
                                deal,
                                {
                                    "expected_revision": deal["revision"],
                                    "cost_line_id": cost["id"],
                                    "amount": {
                                        "amount": output(cost_amount(cost, "IDR", [])),
                                        "currency": "IDR",
                                    },
                                    "evidence_ids": [source["id"]],
                                    "reason": "Synthetic final actual cost confirmation",
                                },
                            )
                    call(
                        conn,
                        context,
                        "reviewGoods",
                        deal,
                        {
                            "expected_revision": deal["revision"],
                            "shipment_id": None,
                            "status": "nonconforming"
                            if stage == "blocked_goods"
                            else "ready",
                            "evidence_ids": [source["id"]],
                            "reason": "Synthetic moisture nonconformity"
                            if stage == "blocked_goods"
                            else "Synthetic measurement and quantity inspection",
                            "reviewed_specification_hash": digest(deal["line_items"]),
                            "inspection_basis": "physical_measurements",
                            "measurements": [
                                {
                                    "line_item_id": deal["line_items"][0]["id"],
                                    "attribute": "quantity",
                                    "value": deal["line_items"][0]["quantity"],
                                    "unit": deal["line_items"][0]["unit"],
                                    "evidence_ids": [source["id"]],
                                }
                            ],
                        },
                    )
                call(
                    conn,
                    context,
                    "analyzeDeal",
                    deal,
                    {
                        "expected_revision": deal["revision"],
                        "scenario_id": None,
                        "scope": "full",
                        "execution": "deterministic",
                    },
                )
                checkpoint(conn, context, deal, 3)
        drain()
        # Phase 4 records owner review and distinct counterparty acceptances; drafts remain drafts.
        with (
            store.deterministic_ids(identifier + "-phase4"),
            transaction(tenant) as conn,
        ):
            deal = get(
                conn,
                tenant,
                "deal",
                get(conn, tenant, "workspace", identifier)["deal_id"],
            )
            if phase(conn, tenant, deal) < 4:
                analysis = commands.children(conn, tenant, "analysis", deal)[-1]
                source = commands.children(conn, tenant, "evidence", deal)[0]
                call(
                    conn,
                    context,
                    "recordApproval",
                    deal,
                    {
                        "expected_revision": deal["revision"],
                        "purpose": "plan",
                        "analysis_hash": analysis["snapshot_hash"],
                        "evidence_digest": analysis["evidence_digest"],
                        "artifact_hash": None,
                        "decision": "approved",
                    },
                )
                for party in deal["parties"]:
                    if set(party["roles"]) & {"buyer", "supplier", "production_input"}:
                        call(
                            conn,
                            context,
                            "recordAgreement",
                            deal,
                            {
                                "expected_revision": deal["revision"],
                                "party_id": party["id"],
                                "accepted_revision": deal["revision"],
                                "evidence_ids": [source["id"]],
                            },
                        )
                call(
                    conn,
                    context,
                    "generateDraft",
                    deal,
                    {
                        "expected_revision": deal["revision"],
                        "scenario_id": analysis["scenario_id"],
                        "analysis_id": analysis["id"],
                        "kind": "agreement",
                        "recipient_party_id": None,
                        "language": "id",
                    },
                )
                checkpoint(conn, context, deal, 4)
        drain()
        if stage in {"reconciling", "closed"}:
            with (
                store.deterministic_ids(identifier + "-phase5"),
                transaction(tenant) as conn,
            ):
                deal = get(
                    conn,
                    tenant,
                    "deal",
                    get(conn, tenant, "workspace", identifier)["deal_id"],
                )
                if phase(conn, tenant, deal) < 5:
                    source = commands.children(conn, tenant, "evidence", deal)[0]
                    if stage == "closed":
                        for shipment in deal["shipments"]:
                            call(
                                conn,
                                context,
                                "recordShipmentEvent",
                                deal,
                                {
                                    "expected_revision": deal["revision"],
                                    "shipment_id": shipment["id"],
                                    "kind": "delivered",
                                    "occurred_at": "2026-09-24T12:00:00Z",
                                    "evidence_ids": [source["id"]],
                                    "exception_reason": None,
                                },
                            )
                    result = call(
                        conn,
                        context,
                        "reconcileDeal",
                        deal,
                        {
                            "expected_revision": deal["revision"],
                            "actual_evidence_ids": [source["id"]],
                            "adjustments": [],
                        },
                    )
                    if stage == "closed":
                        result = call(
                            conn,
                            context,
                            "closeDeal",
                            deal,
                            {
                                "expected_revision": deal["revision"],
                                "reconciliation_hash": result["reconciliation_hash"],
                            },
                        )
                        if result["gate"]["status"] != "ready_for_next_action":
                            raise DomainError(
                                "SEED_CLOSURE_BLOCKED",
                                "Closed checkpoint did not satisfy domain gates: "
                                + str(result["gate"]["conditions"]),
                            )
                    checkpoint(conn, context, deal, 5)
        if stage == "closed":
            with (
                store.deterministic_ids(identifier + "-delivery-checkpoint"),
                transaction(tenant) as conn,
            ):
                deal = get(
                    conn,
                    tenant,
                    "deal",
                    get(conn, tenant, "workspace", identifier)["deal_id"],
                )
                if deal["states"]["shipment"] != "delivered":
                    source = commands.children(conn, tenant, "evidence", deal)[0]
                    for shipment in deal["shipments"]:
                        call(
                            conn,
                            context,
                            "recordShipmentEvent",
                            deal,
                            {
                                "expected_revision": deal["revision"],
                                "shipment_id": shipment["id"],
                                "kind": "delivered",
                                "occurred_at": "2026-09-24T12:00:00Z",
                                "evidence_ids": [source["id"]],
                                "exception_reason": None,
                            },
                        )
                    result = call(
                        conn,
                        context,
                        "reconcileDeal",
                        deal,
                        {
                            "expected_revision": deal["revision"],
                            "actual_evidence_ids": [source["id"]],
                            "adjustments": [],
                        },
                    )
                    result = call(
                        conn,
                        context,
                        "closeDeal",
                        deal,
                        {
                            "expected_revision": deal["revision"],
                            "reconciliation_hash": result["reconciliation_hash"],
                        },
                    )
                    if result["gate"]["status"] != "ready_for_next_action":
                        raise DomainError(
                            "SEED_CLOSURE_BLOCKED",
                            "Delivery checkpoint failed operational closure.",
                        )
                    checkpoint(conn, context, deal, 6)
        if stage != "negotiation":
            with (
                store.deterministic_ids(identifier + "-cash-source-review"),
                transaction(tenant) as conn,
            ):
                deal = get(
                    conn,
                    tenant,
                    "deal",
                    get(conn, tenant, "workspace", identifier)["deal_id"],
                )
                if not any(
                    a["purpose"] == "cash_resources" and a.get("evidence_ids")
                    for a in commands.children(conn, tenant, "approval", deal)
                ):
                    source = commands.children(conn, tenant, "evidence", deal)[0]
                    call(
                        conn,
                        context,
                        "verifyCashResources",
                        deal,
                        {
                            "expected_revision": deal["revision"],
                            "cash_snapshot_hash": digest(
                                deal["constraints"]["cash_snapshot"]
                            ),
                            "evidence_ids": [source["id"]],
                            "reason": "Re-review synthetic opening bank source with explicit lineage",
                        },
                    )
                    checkpoint(conn, context, deal, 7)
        created.append(identifier)
    return created
