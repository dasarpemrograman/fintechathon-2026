"""Versioned synthetic fixtures built through the same domain command services."""

from copy import deepcopy
from contextlib import contextmanager
from datetime import datetime, timedelta, timezone
from decimal import Decimal
from pathlib import Path
import json
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import insert
from services.api import store, commands
from services.api.settings import ROOT, settings
from services.api.store import DomainError, meta, digest, save, get, uid
from packages.contracts.runtime import validate_request, validate_response

MANIFEST = json.loads((ROOT / "fixtures/demo/manifest.json").read_text())
DATASET = MANIFEST["dataset_id"]


def call(conn, context, operation, parent, body):
    from services.api.handlers import write_operation

    validate_request(
        operation,
        body,
        "multipart/form-data" if operation == "uploadDocuments" else "application/json",
    )
    before = deepcopy(parent)
    response = write_operation(conn, context, operation, parent, body)
    parent["revision"] += 1
    parent["snapshot_hash"] = commands.current_fact_hash(
        conn, context["tenant"], parent
    )
    if "workspace_id" in parent:
        commands.derive_states(conn, context, parent)
    save(
        conn,
        context["tenant"],
        "deal" if "workspace_id" in parent else "workspace",
        parent,
        parent=parent.get("workspace_id"),
        dataset=DATASET,
        snapshot=True,
    )
    if "workspace_id" not in parent:
        commands.invalidate_workspace_dependents(conn, context, parent)
    if operation != "convertToDeal":
        response["revision"] = parent["revision"]
    status = (
        202
        if operation
        in {
            "uploadDocuments",
            "analyzeDeal",
            "startDiscovery",
            "discoverFinanceOptions",
            "generateDraft",
            "prepareFinancePack",
            "createScenario",
            "syncCalendar",
        }
        else 201
        if operation
        in {
            "convertToDeal",
            "recordApproval",
            "recordAgreement",
            "recordReceipt",
            "verifyReceipt",
            "recordMilestone",
        }
        else 200
    )
    # New explicit review operations use 200; original source-ingest definitions use 200.
    from packages.contracts.runtime import OPERATIONS

    status = next(
        int(code)
        for code in OPERATIONS[operation][2]["responses"]
        if code.startswith("2")
    )
    if operation == "closeDeal":
        response["result"]["deal"] = deepcopy(parent)
    validate_response(operation, status, response)
    commands.audit(conn, context, operation, before, parent, parent["id"])
    return response["result"]


def financial_case(case, base, source_id):
    key = case["key"]
    code = case["currency"]
    prefix = "demo_" + key.replace("-", "_")
    seller = prefix + "_seller"
    buyer = prefix + "_buyer"
    supplier = prefix + "_supplier"
    ops = prefix + "_services"
    producer = case["financial"] == "cn_producer"
    if producer:
        revenue = "70000"
        opening = "20000"
        buffer = "3000"
        components = [
            ("materials", "22000"),
            ("labor", "18000"),
            ("process", "2000"),
            ("overhead", "3000"),
            ("logistics", "8000"),
        ]
        payments = [
            (0, "14000", buyer, seller, "buyer", 0),
            (0, "12000", seller, supplier, "production_input", 1),
            (7, "20000", seller, supplier, "production_input", 0),
            (14, "10000", seller, supplier, "production_input", 0),
            (14, "8000", seller, ops, "supplier", 1),
            (54, "56000", buyer, seller, "buyer", 0),
        ]
    else:
        scale = (
            Decimal(1)
            if case["financial"] == "id_reseller"
            else Decimal(".001")
            if code == "CNY"
            else Decimal(".0001")
        )
        value = lambda n: format(Decimal(str(n)) * scale, "f")
        revenue = value(160000000)
        opening = value(50000000)
        buffer = value(5000000)
        components = [
            ("procurement", value(100000000)),
            ("packaging", value(5000000)),
            ("administration", value(3000000)),
            ("origin_trucking", value(4000000)),
            ("main_freight", value(16000000)),
            ("destination_delivery", value(6000000)),
        ]
        payments = [
            (0, value(32000000), buyer, seller, "buyer", 0),
            (0, value(50000000), seller, supplier, "supplier", 1),
            (14, value(50000000), seller, supplier, "supplier", 0),
            (14, value(5000000), seller, ops, "supplier", 1),
            (14, value(3000000), seller, ops, "supplier", 2),
            (14, value(4000000), seller, ops, "supplier", 3),
            (14, value(16000000), seller, ops, "supplier", 4),
            (24, value(6000000), seller, ops, "supplier", 0),
            (54, value(128000000), buyer, seller, "buyer", 0),
        ]
    money = lambda amount: {"amount": amount, "currency": code}
    parties = [
        {
            "id": identifier,
            "legal_name": name,
            "display_name": name,
            "registration_identifier": None,
            "country": country,
            "roles": roles,
            "evidence_ids": [source_id],
            "unknowns": [],
        }
        for identifier, name, country, roles in [
            (seller, "Synthetic Seller " + key, case["origin"], ["seller"]),
            (buyer, "Synthetic Buyer " + key, case["destination"], ["buyer"]),
            (
                supplier,
                "Synthetic Inputs " + key,
                case["origin"],
                ["production_input"] if case["profile"] == "producer" else ["supplier"],
            ),
            (
                ops,
                "Synthetic Logistics " + key,
                case["origin"],
                ["supplier", "forwarder"],
            ),
        ]
    ]
    invoice_buyer = prefix + "_invoice_buyer"
    invoice_supplier = prefix + "_invoice_supplier"
    invoice_services = prefix + "_invoice_services"
    prod_total = "42000" if producer else components[0][1]
    service_total = (
        "8000" if producer else format(sum(Decimal(v) for k, v in components[1:]), "f")
    )
    invoices = [
        {
            "id": identifier,
            "side": side,
            "payer_party_id": payer,
            "payee_party_id": payee,
            "amount": money(amount),
            "allocations": [],
            "evidence_ids": [source_id],
        }
        for identifier, side, payer, payee, amount in [
            (invoice_buyer, "buyer", buyer, seller, revenue),
            (
                invoice_supplier,
                "production_input" if case["profile"] == "producer" else "supplier",
                seller,
                supplier,
                prod_total,
            ),
            (invoice_services, "supplier", seller, ops, service_total),
        ]
    ]
    terms = []
    for index, (day, amount, payer, payee, side, sequence) in enumerate(payments):
        at = base + timedelta(days=day, hours=11 if payer == buyer else 12)
        terms.append(
            {
                "id": prefix + "_payment_" + str(index),
                "side": side,
                "payer_id": payer,
                "payee_id": payee,
                "invoice_id": invoice_buyer
                if payer == buyer
                else invoice_supplier
                if payee == supplier
                else invoice_services,
                "amount": money(amount),
                "invoice_fraction": None,
                "schedule": {
                    "kind": "fixed",
                    "due": {"instant": at.isoformat(), "timezone": "UTC"},
                },
                "instrument": "advance" if day == 0 else "milestone",
                "instrument_details": None,
                "status": "proposed",
                "allocations": [],
                "evidence_ids": [source_id],
                "unknowns": [],
                "sequence": sequence,
            }
        )
    procurement_terms = [t["id"] for t in terms if t["payee_id"] == supplier]
    if case["profile"] == "reseller":
        procurement = {
            "business_profile": "reseller",
            "purchase_lines": [
                {
                    "line_item_id": prefix + "_line_1",
                    "supplier_party_id": supplier,
                    "quantity": "10",
                    "unit": "kg",
                    "unit_cost": money(format(Decimal(prod_total) / 10, "f")),
                    "payment_term_ids": procurement_terms,
                    "evidence_ids": [source_id],
                    "paid_before_snapshot": False,
                }
            ],
            "unknowns": [],
        }
    else:
        procurement = {
            "business_profile": "producer",
            "inputs": [
                {
                    "id": prefix + "_materials",
                    "description": "Declared synthetic materials",
                    "quantity": "1",
                    "unit": "batch",
                    "unit_cost": money("22000" if producer else prod_total),
                    "supplier_party_id": supplier,
                    "payment_term_ids": procurement_terms,
                    "evidence_ids": [source_id],
                    "paid_before_snapshot": False,
                }
            ],
            "costs": [],
            "usable_yield": "1",
            "batch_quantity": "10",
            "unit": "kg",
            "capacity_quantity": "10",
            "capacity_period": "one declared batch",
            "milestone_ids": [],
            "unknowns": [],
        }
        if producer:
            for category, amount in [
                ("labor", "18000"),
                ("process", "2000"),
                ("overhead", "3000"),
            ]:
                procurement["costs"].append(
                    {
                        "category": category,
                        "description": "Synthetic " + category + " allocation",
                        "amount": money(amount),
                        "milestone_id": None,
                        "evidence_ids": [source_id],
                        "payment_term_ids": []
                        if category == "overhead"
                        else procurement_terms,
                        "paid_before_snapshot": category == "overhead",
                    }
                )
    lines = [
        {
            "id": prefix + "_line_1",
            "product": {
                "description": case["product"],
                "form": "declared demonstration form",
                "intended_use": "synthetic fixture",
                "attributes": [],
                "unknowns": [],
            },
            "quantity": "10",
            "unit": "kg",
            "goods_origin_country": case["origin"],
            "evidence_ids": [source_id],
            "unknowns": [],
        }
    ]
    shipments = [
        {
            "id": prefix + "_shipment_1",
            "lines": [{"line_item_id": lines[0]["id"], "quantity": "10", "unit": "kg"}],
            "dispatch_country": case["origin"],
            "destination_country": case["destination"],
            "mode": "sea_lcl",
            "unknowns": [],
        }
    ]
    if case.get("multiple_shipments"):
        lines[0]["quantity"] = "5"
        lines.append({**deepcopy(lines[0]), "id": prefix + "_line_2"})
        shipments[0]["lines"][0]["quantity"] = "5"
        shipments.append(
            {
                **deepcopy(shipments[0]),
                "id": prefix + "_shipment_2",
                "lines": [
                    {"line_item_id": lines[1]["id"], "quantity": "5", "unit": "kg"}
                ],
            }
        )
    if case.get("multiple_shipments") and case["profile"] == "reseller":
        original = procurement["purchase_lines"][0]
        procurement["purchase_lines"] = [
            {
                **deepcopy(original),
                "line_item_id": line["id"],
                "quantity": line["quantity"],
            }
            for line in lines
        ]
    constraints = {
        "cash_snapshot": {
            "available": money(opening),
            "as_of": base.isoformat(),
            "committed_elsewhere": money("0"),
            "minimum_buffer": money(buffer),
        },
        "target_contribution_margin": "0.15",
        "delivery_deadline": None,
        "credit_tenor_limit_days": 90,
        "allowable_changes": [
            "buyer payment terms",
            "supplier payment terms",
            "funding",
        ],
        "ranking_preference": "cash",
        "unknowns": [],
    }
    return (
        {
            "parties": parties,
            "line_items": lines,
            "shipments": shipments,
            "payment_terms": terms,
            "procurement": procurement,
            "constraints": constraints,
            "invoices": invoices,
        },
        components,
        seller,
        ops,
    )


def seed(reference_date=None):
    if not settings.demo:
        raise DomainError(
            "DEMO_MODE_REQUIRED", "Set APP_MODE=demo explicitly before seeding."
        )
    base = datetime.fromisoformat(reference_date or MANIFEST["reference_date"]).replace(
        tzinfo=timezone.utc
    )
    created = []
    with store.engine.begin() as conn:
        for key, name in MANIFEST["organizations"].items():
            tenant = "demo_org_" + key
            conn.execute(
                insert(store.organizations)
                .values(
                    id=tenant,
                    name=name,
                    dataset_id=DATASET,
                    policy={"plan": "team", "runs": 100, "pages": 1000, "active": True},
                )
                .on_conflict_do_nothing()
            )
            for role, label in [
                ("owner", "Owner"),
                ("export_admin", "Export Admin"),
                ("finance_reviewer", "Finance Reviewer"),
                ("production_procurement", "Production Reviewer"),
            ]:
                user = "demo_" + key + "_" + role
                conn.execute(
                    insert(store.users)
                    .values(
                        id=user,
                        email=role + "-" + key + "@example.test",
                        display_name=label + " — " + name,
                        password_hash=None,
                        dataset_id=DATASET,
                        active=True,
                    )
                    .on_conflict_do_nothing()
                )
                conn.execute(
                    insert(store.memberships)
                    .values(
                        id="demo_membership_" + key + "_" + role,
                        organization_id=tenant,
                        user_id=user,
                        roles=[role],
                    )
                    .on_conflict_do_nothing()
                )
    for case in MANIFEST["cases"]:
        for mode in ["sandbox", "deal"]:
            identifier = "demo_" + case["key"] + "_" + mode
            tenant = "demo_org_" + case["organization"]
            actor = "demo_" + case["organization"] + "_owner"
            with store.deterministic_ids(identifier), transaction(tenant) as conn:
                existing = get(conn, tenant, "workspace", identifier, False)
                if existing:
                    if existing["dataset_id"] != DATASET:
                        raise DomainError(
                            "SEED_OWNERSHIP",
                            "Refusing to overwrite an existing user-owned workspace.",
                        )
                    created.append(identifier)
                    continue
                context = {
                    "tenant": tenant,
                    "actor": actor,
                    "roles": ["owner"],
                    "scope": "demo",
                    "dataset": DATASET,
                    "request_id": uid("request"),
                }
                body = {
                    "mode": mode,
                    "business_profile": case["profile"],
                    "seller_domicile": case["origin"],
                    "dispatch_country": case["origin"],
                    "destination_country": case["destination"],
                    "reporting_currency": case["currency"],
                    "owner_timezone": case["timezone"],
                    "product": {"description": case["product"]},
                }
                workspace = commands.new_workspace(
                    conn, context, body, identifier=identifier, dataset=DATASET
                )
                if mode == "sandbox":
                    created.append(identifier)
                    continue
                # Original source bytes traverse normal upload/worker extraction.
                declared, components, _, _ = financial_case(
                    case, base, "fixture_source"
                )
                source_lines = [
                    "SYNTHETIC DEMO financial fixture. Not a contract, current price or lender offer.",
                    "Product: " + case["product"],
                ]
                source_lines += [
                    "Invoice "
                    + invoice["side"]
                    + ": "
                    + invoice["amount"]["currency"]
                    + " "
                    + invoice["amount"]["amount"]
                    for invoice in declared["invoices"]
                ]
                source_lines += [
                    "Cost " + name + ": " + case["currency"] + " " + amount
                    for name, amount in components
                ]
                source_lines += [
                    "Payment "
                    + term["id"]
                    + ": "
                    + term["amount"]["currency"]
                    + " "
                    + term["amount"]["amount"]
                    + " at "
                    + term["schedule"]["due"]["instant"]
                    for term in declared["payment_terms"]
                ]
                source_text = "\n".join(source_lines)
                content = source_text.encode()
                context["uploads"] = [("financial-fixture.txt", "text/plain", content)]
                ingestion = call(
                    conn,
                    context,
                    "uploadDocuments",
                    workspace,
                    {
                        "expected_revision": workspace["revision"],
                        "files": ["financial-fixture.txt"],
                        "document_role": "quotation",
                    },
                )
                document = ingestion["documents"][0]
                values = {
                    "canonical_url": None,
                    "document_id": document["id"],
                    "publisher": "ALLExport synthetic fixture",
                    "title": "Synthetic financial assumptions — " + case["key"],
                    "language": "en",
                    "retrieved_at": store.instant(),
                    "published_at": None,
                    "effective_from": base.date().isoformat(),
                    "valid_until": None,
                    "access": "success",
                    "mode": "synthetic_demo",
                    "content_hash": document["content_hash"],
                    "locator": "Fixture manifest and declared schedules",
                    "claim": source_text,
                    "applicability": {
                        "jurisdictions": [case["origin"], case["destination"]],
                        "product_attributes": [],
                        "shipment_ids": [],
                        "line_item_ids": [],
                        "validity_reason": "Demonstration only. Not regulatory or credit advice.",
                        "unknowns": [],
                    },
                    "limitations": ["Synthetic data cannot authorize real execution."],
                    "review_status": "unreviewed",
                }
                source = call(
                    conn,
                    context,
                    "ingestWorkspacesEvidence",
                    workspace,
                    {"expected_revision": workspace["revision"], "evidence": values},
                )
                deal_body, components, seller, ops = financial_case(
                    case, base, source["id"]
                )
                deal = call(
                    conn,
                    context,
                    "convertToDeal",
                    workspace,
                    {"expected_revision": workspace["revision"], **deal_body},
                )["deal"]
                for component, amount in components:
                    if component in {
                        "procurement",
                        "materials",
                        "labor",
                        "process",
                        "overhead",
                    }:
                        continue
                    terms = [
                        t["id"]
                        for t in deal["payment_terms"]
                        if t["payee_id"] == ops and t["amount"]["amount"] == amount
                    ]
                    cost = {
                        "component_key": component,
                        "category": component,
                        "location": "declared route",
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
                            "base": {"amount": amount, "currency": case["currency"]},
                            "high": None,
                        },
                        "evidence_ids": [source["id"]],
                        "covered_components": [component],
                        "treatment": "expense",
                        "allocations": [],
                        "payment_term_ids": terms,
                        "status": "user_assumed",
                        "conditional": False,
                        "valid_until": None,
                        "actual_amount": None,
                        "unknowns": [],
                        "cash_treatment": "scheduled",
                    }
                    call(
                        conn,
                        context,
                        "recordCostLine",
                        deal,
                        {
                            "expected_revision": deal["revision"],
                            "cost_line_id": None,
                            "line": cost,
                        },
                    )
                requirement = {
                    "jurisdiction": case["destination"],
                    "subject": "shipment",
                    "category": "Synthetic conformity/document checklist",
                    "applicability": "unresolved",
                    "predicate_facts": [
                        "Reviewed transaction-specific requirement applicability"
                    ],
                    "evidence_ids": [source["id"]],
                    "fulfillment_status": "missing",
                    "owner_party_id": seller,
                    "fulfillment_evidence_ids": [],
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
                if case["key"] in {"cn-producer", "ke-producer"}:
                    file = (
                        "ambiguous-zh.txt"
                        if case["key"] == "cn-producer"
                        else "scan.png"
                    )
                    media = "text/plain" if file.endswith(".txt") else "image/png"
                    context["uploads"] = [
                        (
                            file,
                            media,
                            (ROOT / "fixtures/demo/documents" / file).read_bytes(),
                        )
                    ]
                    call(
                        conn,
                        context,
                        "uploadDocuments",
                        deal,
                        {
                            "expected_revision": deal["revision"],
                            "files": [file],
                            "document_role": "quality",
                        },
                    )
                created.append(identifier)
    return {
        "dataset": DATASET,
        "workspaces": created,
        "reference_date": base.date().isoformat(),
    }


def analyze_seeded():
    if not settings.demo:
        raise DomainError("DEMO_MODE_REQUIRED", "Set APP_MODE=demo explicitly.")
    with store.engine.begin() as conn:
        for case in MANIFEST["cases"]:
            tenant = "demo_org_" + case["organization"]
            conn.execute(
                sa.select(store.organizations.c.id)
                .where(store.organizations.c.id == tenant)
                .with_for_update()
            )
            workspace = get(conn, tenant, "workspace", "demo_" + case["key"] + "_deal")
            deal = get(conn, tenant, "deal", workspace["deal_id"])
            if commands.children(conn, tenant, "analysis", deal):
                continue
            context = {
                "tenant": tenant,
                "actor": "demo_" + case["organization"] + "_owner",
                "roles": ["owner"],
                "scope": "demo",
                "dataset": DATASET,
                "request_id": uid("request"),
            }
            with store.deterministic_ids("analysis-" + case["key"]):
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


@contextmanager
def transaction(tenant):
    with store.engine.begin() as conn:
        conn.execute(
            sa.select(store.organizations.c.id)
            .where(store.organizations.c.id == tenant)
            .with_for_update()
        )
        yield conn
