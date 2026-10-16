"""Transactional application commands. HTTP and worker reuse these services."""

from copy import deepcopy
from datetime import datetime, timezone
from decimal import Decimal
import sqlalchemy as sa
from services.api import store
from services.api.store import (
    DomainError,
    now,
    meta,
    digest,
    issue,
    save,
    get,
    list_records,
    reference,
    assert_ref,
    uid,
    instant,
)
from packages.domain.economics import number, validate_allocations

WORKSPACE_PATCHES = {
    "/product",
    "/seller_domicile",
    "/dispatch_country",
    "/destination_country",
    "/planning_inputs",
}
DEAL_PATCHES = {
    "/seller_domicile",
    "/constraints",
    "/line_items",
    "/shipments",
    "/parties",
    "/payment_terms",
    "/procurement",
    "/invoices",
}


def all_records(conn, tenant, kind, parent=None):
    result = []
    cursor = None
    while True:
        page = list_records(conn, tenant, kind, parent, 100, cursor)
        result += page["items"]
        cursor = page["next_cursor"]
        if cursor is None:
            return result


def parent_workspace(deal):
    return deal["workspace_id"]


def children(conn, tenant, kind, parent):
    result = all_records(conn, tenant, kind, parent["id"])
    if "workspace_id" in parent:
        result += all_records(conn, tenant, kind, parent["workspace_id"])
    return sorted(result, key=lambda row: (row.get("created_at", ""), row["id"]))


def states():
    return {
        "analysis": "draft",
        "commercial_terms": "proposed",
        "funding_preparation": "not_needed",
        "execution_gate": "blocked",
        "goods": "not_started",
        "shipment": "not_booked",
        "buyer_payment": "not_due",
        "internal_closure": "open",
    }


def constraints():
    return {
        "cash_snapshot": None,
        "target_contribution_margin": None,
        "delivery_deadline": None,
        "credit_tenor_limit_days": None,
        "allowable_changes": [],
        "ranking_preference": None,
        "unknowns": [
            {
                "status": "missing",
                "field_path": "/constraints/cash_snapshot",
                "reason": "Owner cash snapshot has not been supplied.",
            }
        ],
    }


def fact_hash(deal):
    return digest(
        {
            k: v
            for k, v in deal.items()
            if k
            not in {
                "snapshot_hash",
                "revision",
                "states",
                "created_at",
                "created_by",
                "archived",
                "evidence_ids",
            }
        }
    )


def current_fact_hash(conn, tenant, deal):
    from packages.domain.dependencies import (
        material_ids,
        selected_fx,
        DEPENDENCY_POLICY,
    )
    from datetime import date
    from services.api.settings import settings
    from packages.domain.demo import MANIFEST

    today = (
        date.fromisoformat(MANIFEST["reference_date"])
        if deal["execution_scope"] == "demo"
        else now().date()
    )
    inputs = {
        kind: children(conn, tenant, kind, deal)
        for kind in [
            "cost_line",
            "fx_observation",
            "requirement",
            "evidence",
            "obligation",
            "milestone",
            "receipt",
            "funding_option",
            "market_observation",
        ]
    }
    products = children(conn, tenant, "finance_product", deal)
    if products:
        inputs["finance_product"] = products
    ids = material_ids(
        deal, inputs, bank_reviews=children(conn, tenant, "approval", deal), today=today
    )
    inputs["evidence"] = [row for row in inputs["evidence"] if row["id"] in ids]
    inputs["fx_observation"] = selected_fx(deal, inputs)
    return digest(
        {"policy": DEPENDENCY_POLICY, "facts": fact_hash(deal), "inputs": inputs}
    )


def validate_deal(deal):
    if deal["business_profile"] != deal["procurement"]["business_profile"]:
        raise DomainError(
            "PROFILE_MISMATCH",
            "Procurement branch must match the selected business profile.",
        )
    line_ids = [line["id"] for line in deal["line_items"]]
    party_ids = {party["id"] for party in deal["parties"]}
    shipment_ids = [s["id"] for s in deal["shipments"]]
    if len(line_ids) != len(set(line_ids)) or len(shipment_ids) != len(
        set(shipment_ids)
    ):
        raise DomainError("DUPLICATE_CHILD", "Line and shipment IDs must be unique.")
    for line in deal["line_items"]:
        if number(line["quantity"]) <= 0 or not line["unit"].strip():
            raise DomainError(
                "INVALID_QUANTITY_UNIT",
                "Product quantities must be positive and declare a unit.",
            )
    plan = deal["procurement"]
    if plan["business_profile"] == "producer":
        if plan["usable_yield"] is not None and not Decimal(0) < number(
            plan["usable_yield"]
        ) <= Decimal(1):
            raise DomainError(
                "INVALID_YIELD",
                "Usable yield must be greater than zero and at most one.",
            )
        if (
            plan["capacity_quantity"] is not None
            and plan["batch_quantity"] is not None
            and number(plan["capacity_quantity"]) < number(plan["batch_quantity"])
        ):
            raise DomainError(
                "CAPACITY_EXCEEDED",
                "Declared batch exceeds available production capacity.",
            )
        if (
            plan["batch_quantity"] is not None
            and plan["usable_yield"] is not None
            and all(line["unit"] == plan["unit"] for line in deal["line_items"])
        ):
            usable = number(plan["batch_quantity"]) * number(plan["usable_yield"])
            required = sum(
                (number(line["quantity"]) for line in deal["line_items"]), Decimal(0)
            )
            if usable < required:
                raise DomainError(
                    "PRODUCTION_OUTPUT_SHORTFALL",
                    "Usable batch output cannot cover declared export quantities; revise batch size, yield or goods quantities.",
                )
    allocated = {}
    for shipment in deal["shipments"]:
        for line in shipment["lines"]:
            if line["line_item_id"] not in line_ids:
                raise DomainError(
                    "LINE_REFERENCE",
                    "Shipment line must reference a declared product line.",
                )
            declared = next(
                item
                for item in deal["line_items"]
                if item["id"] == line["line_item_id"]
            )
            if line["unit"] != declared["unit"]:
                raise DomainError(
                    "UNIT_MISMATCH",
                    "Shipment allocation must use its declared product line unit.",
                )
            allocated[line["line_item_id"]] = allocated.get(
                line["line_item_id"], Decimal(0)
            ) + number(line["quantity"])
            if allocated[line["line_item_id"]] > number(declared["quantity"]):
                raise DomainError(
                    "OVERALLOCATED_SHIPMENT",
                    "Shipment quantities exceed the declared product line quantity.",
                )
    for invoice in deal["invoices"]:
        if (
            invoice["payer_party_id"] not in party_ids
            or invoice["payee_party_id"] not in party_ids
        ):
            raise DomainError(
                "PARTY_REFERENCE", "Invoice parties must be declared in this deal."
            )
        number(invoice["amount"]["amount"])
        validate_allocation_targets(deal, invoice["allocations"])
        if invoice.get("reimbursable_amount"):
            reimbursed = invoice["reimbursable_amount"]
            if reimbursed["currency"] != invoice["amount"]["currency"] or number(
                reimbursed["amount"]
            ) > number(invoice["amount"]["amount"]):
                raise DomainError(
                    "INVOICE_REIMBURSEMENT",
                    "Included reimbursement must use the invoice currency and cannot exceed its amount.",
                )
    scheduled = {}
    for term in deal["payment_terms"]:
        if term["payer_id"] not in party_ids or term["payee_id"] not in party_ids:
            raise DomainError(
                "PARTY_REFERENCE", "Payment parties must belong to the deal."
            )
        if (
            term.get("invoice_fraction") is not None
            and number(term["invoice_fraction"]) > 1
        ):
            raise DomainError(
                "PAYMENT_FRACTION", "Invoice payment fraction cannot exceed one."
            )
        invoice = next(
            (i for i in deal["invoices"] if i["id"] == term["invoice_id"]), None
        )
        if not invoice:
            raise DomainError(
                "INVOICE_REFERENCE", "Payment term must reference its declared invoice."
            )
        if (term["payer_id"], term["payee_id"]) != (
            invoice["payer_party_id"],
            invoice["payee_party_id"],
        ):
            raise DomainError(
                "INVOICE_PARTY_MISMATCH",
                "Installment parties must match the referenced invoice.",
            )
        amount = term["amount"]
        if amount and amount["currency"] != invoice["amount"]["currency"]:
            raise DomainError(
                "INSTALLMENT_CURRENCY",
                "Installments must use the invoice currency; record execution FX separately.",
            )
        scheduled[invoice["id"]] = scheduled.get(invoice["id"], Decimal(0)) + (
            number(amount["amount"])
            if amount
            else number(invoice["amount"]["amount"]) * number(term["invoice_fraction"])
            if term["invoice_fraction"] is not None
            else Decimal(0)
        )
        if scheduled[invoice["id"]] > number(invoice["amount"]["amount"]):
            raise DomainError(
                "OVERALLOCATED_INVOICE", "Installments exceed their invoice amount."
            )


def evidence_refs(conn, tenant, parent, identifiers, source=None):
    for identifier in identifiers:
        assert_ref(
            conn, tenant, identifier, kind="evidence", scope=parent["execution_scope"]
        )
        if source:
            reference(conn, tenant, source, identifier, parent["execution_scope"])


def new_workspace(conn, context, body, identifier=None, dataset=None):
    if body["mode"] == "deal":
        from packages.domain.entitlements import require_feature

        require_feature(conn, context["tenant"], "deal")
    from packages.domain.economics import currency
    from zoneinfo import ZoneInfo, ZoneInfoNotFoundError
    import pycountry

    currency(body["reporting_currency"])
    try:
        ZoneInfo(body["owner_timezone"])
    except ZoneInfoNotFoundError:
        raise DomainError("INVALID_TIMEZONE", "Choose an IANA timezone.")
    for field in ["seller_domicile", "dispatch_country", "destination_country"]:
        if body.get(field) and pycountry.countries.get(alpha_2=body[field]) is None:
            raise DomainError(
                "INVALID_COUNTRY", "Unknown ISO country code: " + body[field]
            )
    data = {
        **meta(context["tenant"], context["actor"], "workspace", identifier),
        **deepcopy(body),
        "schema_version": "2.2",
        "revision": 1,
        "planning_inputs": None,
        "deal_id": None,
        "execution_scope": context["scope"],
        "dataset_id": dataset,
        "archived": False,
    }
    for name in ["seller_domicile", "dispatch_country", "destination_country"]:
        data.setdefault(name, None)
    data.setdefault("unknowns", [])
    for name in ["seller_domicile", "dispatch_country", "destination_country"]:
        if data[name] is None:
            data["unknowns"].append(
                {
                    "field_path": "/" + name,
                    "status": "missing",
                    "reason": "Not supplied at workspace entry.",
                }
            )
    data["snapshot_hash"] = current_fact_hash(conn, context["tenant"], data)
    return save(
        conn, context["tenant"], "workspace", data, dataset=dataset, snapshot=True
    )


def convert_deal(conn, context, workspace, body, identifier=None):
    from packages.domain.entitlements import require_feature

    require_feature(conn, context["tenant"], "deal", workspace["id"])
    if not workspace["seller_domicile"]:
        raise DomainError(
            "SELLER_DOMICILE_REQUIRED",
            "Confirm seller domicile before creating a deal.",
        )
    if workspace["deal_id"]:
        raise DomainError(
            "ALREADY_CONVERTED", "Workspace already has a concrete deal.", 409
        )
    data = {
        **meta(context["tenant"], context["actor"], "deal", identifier),
        "schema_version": "2.2",
        "workspace_id": workspace["id"],
        "revision": 1,
        "business_profile": workspace["business_profile"],
        "seller_domicile": workspace["seller_domicile"],
        "reporting_currency": workspace["reporting_currency"],
        "owner_timezone": workspace["owner_timezone"],
        "source_sandbox_revision": {
            "id": workspace["id"],
            "revision": workspace["revision"],
        }
        if workspace["mode"] == "sandbox"
        else None,
        "line_items": body["line_items"],
        "shipments": body["shipments"],
        "parties": body["parties"],
        "payment_terms": body["payment_terms"],
        "procurement": body["procurement"],
        "constraints": body["constraints"],
        "invoices": body["invoices"],
        "cost_line_ids": [],
        "evidence_ids": [
            r["id"] for r in children(conn, context["tenant"], "evidence", workspace)
        ],
        "requirement_ids": [],
        "states": states(),
        "unknowns": [],
        "execution_scope": workspace["execution_scope"],
        "dataset_id": workspace["dataset_id"],
        "archived": False,
    }
    validate_deal(data)
    validate_embedded_evidence(conn, context["tenant"], workspace, body)
    conn.execute(
        store.registry.insert().values(
            tenant_id=context["tenant"],
            id=data["id"],
            kind="deal",
            dataset_id=data["dataset_id"],
        )
    )
    for cost in procurement_costs(context, data):
        save(
            conn,
            context["tenant"],
            "cost_line",
            cost,
            parent=data["id"],
            dataset=data["dataset_id"],
        )
        data["cost_line_ids"].append(cost["id"])
    workspace["deal_id"] = data["id"]
    for term in data["payment_terms"]:
        amount = term["amount"]
        if amount is None and term["invoice_fraction"] is not None:
            invoice = next(
                (i for i in data["invoices"] if i["id"] == term["invoice_id"]), None
            )
            if invoice:
                amount = {
                    "currency": invoice["amount"]["currency"],
                    "amount": format(
                        number(invoice["amount"]["amount"])
                        * number(term["invoice_fraction"]),
                        "f",
                    ),
                }
        obligation = {
            **meta(context["tenant"], context["actor"], "obligation", term["id"]),
            "payer_party_id": term["payer_id"],
            "payee_party_id": term["payee_id"],
            "amount": amount,
            "schedule": term["schedule"],
            "allocations": term["allocations"],
            "status": "proposed" if term["status"] == "proposed" else "open",
            "evidence_ids": term["evidence_ids"],
            "unknowns": [],
        }
        if "sequence" in term:
            obligation["sequence"] = term["sequence"]
        save(
            conn,
            context["tenant"],
            "obligation",
            obligation,
            parent=data["id"],
            dataset=data["dataset_id"],
        )
    data["snapshot_hash"] = current_fact_hash(conn, context["tenant"], data)
    save(
        conn,
        context["tenant"],
        "deal",
        data,
        parent=workspace["id"],
        dataset=workspace["dataset_id"],
        snapshot=True,
    )
    return data


def patch_facts(conn, context, parent, patches, kind):
    for patch in patches:
        if patch["path"] not in (
            WORKSPACE_PATCHES if kind == "workspace" else DEAL_PATCHES
        ):
            raise DomainError(
                "PATCH_FORBIDDEN", "This path cannot be changed in this revision scope."
            )
        evidence_refs(conn, context["tenant"], parent, patch["evidence_ids"])
        validate_embedded_evidence(conn, context["tenant"], parent, patch["value"])
        parent[patch["path"][1:]] = deepcopy(patch["value"])
        if "evidence_ids" in parent:
            parent["evidence_ids"] = list(
                dict.fromkeys(parent["evidence_ids"] + patch["evidence_ids"])
            )
    if kind == "deal":
        validate_deal(parent)
        parent["snapshot_hash"] = fact_hash(parent)
        parent["states"]["analysis"] = "needs_input"
        parent["states"]["execution_gate"] = "blocked"
    return parent


def audit(conn, context, operation, before, after, parent_id=None):
    row = {
        **meta(context["tenant"], context["actor"], "audit"),
        "action": operation,
        "purpose": context.get("purpose", operation),
        "expected_revision": before.get("revision") if before else None,
        "current_revision": after.get("revision") if after else None,
        "before_hash": digest(before) if before else None,
        "after_hash": digest(after) if after else None,
        "data_mode": "synthetic_demo"
        if context["scope"] == "demo"
        else "user_provided",
        "request_id": context.get("request_id"),
        "job_id": context.get("job_id"),
    }
    save(
        conn,
        context["tenant"],
        "audit",
        row,
        parent=parent_id,
        dataset=context.get("dataset"),
    )


def enqueue(conn, context, parent, kind, payload):
    parent["snapshot_hash"] = current_fact_hash(conn, context["tenant"], parent)
    run = {
        **meta(context["tenant"], context["actor"], "run"),
        "workspace_id": parent.get("workspace_id", parent["id"]),
        "revision": parent["revision"] + 1,
        "kind": kind,
        "status": "queued",
        "output_refs": [],
        "blockers": [],
        "warnings": [],
        "data_modes": [],
        "retry_after_seconds": None,
        "usage": {
            "chargeable": payload.get("execution") == "enrich"
            or kind in {"discovery", "finance_options"}
            and not payload.get("_deterministic_matching", False)
            or kind == "document_ingestion"
            and payload.get("expected_pages", len(payload.get("document_ids", []))) > 0,
            "charged_runs": 0,
            "processed_pages": 0,
            "reason": "Queued; no successful charge yet.",
        },
    }
    save(
        conn,
        context["tenant"],
        "run",
        run,
        parent=parent["id"],
        dataset=parent["dataset_id"],
    )
    conn.execute(
        store.jobs.insert().values(
            tenant_id=context["tenant"],
            id=run["id"],
            state="queued",
            payload={
                "parent_id": parent["id"],
                "parent_kind": "deal" if "workspace_id" in parent else "workspace",
                "input_revision": run["revision"],
                "valuation_date": now().date().isoformat(),
                "request_id": context["request_id"],
                "actor": context["actor"],
                "kind": kind,
                "body": payload,
                "scope": parent["execution_scope"],
                "snapshot": deepcopy(parent),
                "input_resource_refs": {
                    kind: [
                        {
                            "id": r["id"],
                            "revision": conn.execute(
                                sa.select(store.records[kind].c.revision).where(
                                    store.records[kind].c.tenant_id
                                    == context["tenant"],
                                    store.records[kind].c.id == r["id"],
                                )
                            ).scalar_one(),
                        }
                        for r in children(conn, context["tenant"], kind, parent)
                    ]
                    for kind in [
                        "cost_line",
                        "obligation",
                        "milestone",
                        "fx_observation",
                        "evidence",
                        "receipt",
                        "funding_option",
                        "finance_product",
                        "market_observation",
                    ]
                },
                "input_resources": {
                    kind: children(conn, context["tenant"], kind, parent)
                    for kind in [
                        "cost_line",
                        "obligation",
                        "milestone",
                        "fx_observation",
                        "evidence",
                        "receipt",
                        "funding_option",
                        "finance_product",
                        "market_observation",
                    ]
                },
            },
        )
    )
    return {"run": run, "poll_url": "/v2/runs/" + run["id"]}


def allowance_state(conn, tenant):
    from packages.domain.entitlements import balance

    view = balance(conn, tenant)
    runs = view["units"]["enriched_run"]
    pages = view["units"]["document_page"]
    return (
        view["policy"],
        runs["included_remaining"] + runs["addon_remaining"],
        pages["included_remaining"] + pages["addon_remaining"],
        view["active"],
    )


def admission(conn, context, chargeable=True, pages=0):
    policy, remaining_runs, remaining_pages, active = allowance_state(
        conn, context["tenant"]
    )
    allowed = (
        not (chargeable or pages)
        or active
        and (not chargeable or remaining_runs > 0)
        and pages <= remaining_pages
    )
    return {
        "chargeable": bool(chargeable or pages),
        "admitted": bool(allowed),
        "expected_runs": 1 if chargeable else 0,
        "expected_pages": pages,
        "reason": "Within current-period allowance."
        if allowed
        else "New provider work is not admitted; existing records and manual obligations remain available.",
    }


def procurement_costs(context, deal):
    """Project declared procurement economics once; cash still follows obligations."""
    sellers = [p["id"] for p in deal["parties"] if "seller" in p["roles"]]
    if not sellers:
        return []
    seller = sellers[0]
    plan = deal["procurement"]
    rows = []

    def line(key, amount, quantity, rate, evidence_ids, terms, paid):
        return {
            **meta(context["tenant"], context["actor"], "cost_line"),
            "component_key": key,
            "category": "production"
            if plan["business_profile"] == "producer"
            else "procurement",
            "location": "origin",
            "payer_party_id": seller,
            "economic_bearer_party_id": seller,
            "basis": "per_unit" if rate else "fixed",
            "quantity": quantity,
            "unit": "declared input",
            "rate": rate,
            "minimum_charge": None,
            "calculation_rule_ref": None,
            "estimate": {"low": None, "base": amount, "high": None},
            "evidence_ids": evidence_ids,
            "covered_components": [key],
            "treatment": "expense",
            "allocations": [],
            "payment_term_ids": terms,
            "status": "user_assumed",
            "conditional": False,
            "valid_until": None,
            "actual_amount": None,
            "unknowns": [],
            "cash_treatment": "paid_before_snapshot"
            if paid
            else "scheduled"
            if terms
            else "unknown",
        }

    if plan["business_profile"] == "reseller":
        for index, purchase in enumerate(plan["purchase_lines"]):
            rows.append(
                line(
                    "procurement:" + purchase["line_item_id"],
                    None,
                    purchase["quantity"],
                    purchase["unit_cost"],
                    purchase["evidence_ids"],
                    purchase["payment_term_ids"],
                    purchase.get("paid_before_snapshot", False),
                )
            )
    else:
        for item in plan["inputs"]:
            rows.append(
                line(
                    "production-input:" + item["id"],
                    None,
                    item["quantity"],
                    item["unit_cost"],
                    item["evidence_ids"],
                    item.get("payment_term_ids", []),
                    item.get("paid_before_snapshot", False),
                )
            )
        for index, item in enumerate(plan["costs"]):
            rows.append(
                line(
                    "production-" + item["category"] + ":" + str(index),
                    item["amount"],
                    "1",
                    None,
                    item["evidence_ids"],
                    item.get("payment_term_ids", []),
                    item.get("paid_before_snapshot", False),
                )
            )
    return rows


def analysis_inputs(conn, context, parent, resources, patches):
    """Reproject hypothetical commercial inputs without mutating stored actuals."""
    paths = {p["path"] for p in patches}
    costs = deepcopy(resources["cost_line"])
    obligations = deepcopy(resources["obligation"])
    if "/procurement" in paths:
        old = {
            r["component_key"]: r
            for r in costs
            if r["category"] in {"procurement", "production"}
        }
        costs = [r for r in costs if r["category"] not in {"procurement", "production"}]
        for projected in procurement_costs(context, parent):
            previous = old.get(projected["component_key"])
            if previous:
                projected.update(
                    {
                        k: previous[k]
                        for k in ["id", "created_at", "created_by", "actual_amount"]
                    }
                )
            costs.append(projected)
    if paths & {"/payment_terms", "/invoices"}:
        by_id = {r["id"]: r for r in obligations}
        updated = []
        for term in parent["payment_terms"]:
            previous = by_id.pop(term["id"], None)
            amount = term["amount"]
            if amount is None and term["invoice_fraction"] is not None:
                invoice = next(
                    (i for i in parent["invoices"] if i["id"] == term["invoice_id"]),
                    None,
                )
                if invoice:
                    amount = {
                        "currency": invoice["amount"]["currency"],
                        "amount": format(
                            number(invoice["amount"]["amount"])
                            * number(term["invoice_fraction"]),
                            "f",
                        ),
                    }
            row = (
                deepcopy(previous)
                if previous
                else {
                    **meta(
                        context["tenant"], context["actor"], "obligation", term["id"]
                    ),
                    "status": "proposed",
                    "unknowns": [],
                }
            )
            row.update(
                payer_party_id=term["payer_id"],
                payee_party_id=term["payee_id"],
                amount=amount,
                schedule=term["schedule"],
                allocations=term["allocations"],
                evidence_ids=term["evidence_ids"],
            )
            if "sequence" in term:
                row["sequence"] = term["sequence"]
            updated.append(row)
        # Ancillary recorded liabilities remain even if not present in a proposed invoice schedule.
        obligations = updated + list(by_id.values())
    return costs, obligations


def derive_states(conn, context, parent):
    if "workspace_id" not in parent:
        return
    from packages.domain.workflow import readiness
    from services.api.review_handlers import refresh_settlement_states

    refresh_settlement_states(conn, context, parent)

    gate, _ = readiness(conn, context, parent, "shipment")
    parent["states"]["execution_gate"] = gate["status"]
    accepted = next(
        (
            c["status"] == "satisfied"
            for c in gate["conditions"]
            if c["code"] == "COUNTERPARTY_AGREEMENTS"
        ),
        False,
    )
    analyses = [
        row
        for row in children(conn, context["tenant"], "analysis", parent)
        if analysis_view(conn, context["tenant"], parent, row)["current_for_use"]
    ]
    latest = analyses[-1] if analyses else None
    parent["states"]["analysis"] = (
        (
            "analyzed_partial"
            if latest["completeness"] == "partial"
            else "analyzed_complete"
        )
        if latest
        else (
            "needs_input"
            if children(conn, context["tenant"], "analysis", parent)
            else "draft"
        )
    )
    packs = [
        pack
        for pack in children(conn, context["tenant"], "finance_pack", parent)
        if latest and pack["artifact"]["analysis_id"] == latest["id"]
    ]
    if packs:
        parent["states"]["funding_preparation"] = (
            "application_ready" if not packs[-1]["gaps"] else "preparing"
        )
    elif children(conn, context["tenant"], "funding_option", parent):
        parent["states"]["funding_preparation"] = "comparing"
    else:
        cash = latest["before_financing"]["cash_metrics"] if latest else None
        parent["states"]["funding_preparation"] = (
            "needed" if cash and number(cash["buffer_shortfall"]) > 0 else "not_needed"
        )
    if parent["states"]["internal_closure"] == "closed" and not parent.get("archived"):
        from services.api.reconciliation import reconciliation_input_hash

        closing, blockers = readiness(conn, context, parent, "internal_close")
        reconciliations = children(conn, context["tenant"], "reconciliation", parent)
        if (
            blockers
            or not reconciliations
            or reconciliations[-1]["reconciliation_hash"]
            != reconciliation_input_hash(conn, context["tenant"], parent)
        ):
            parent["states"]["internal_closure"] = "reconciling"
    if accepted:
        parent["states"]["commercial_terms"] = "agreed"
    elif children(conn, context["tenant"], "agreement", parent):
        parent["states"]["commercial_terms"] = "awaiting_counterparties"


def invalidate_workspace_dependents(conn, context, workspace):
    if not workspace.get("deal_id"):
        return
    deal = get(conn, context["tenant"], "deal", workspace["deal_id"])
    current = current_fact_hash(conn, context["tenant"], deal)
    if current == deal["snapshot_hash"]:
        return
    deal["snapshot_hash"] = current
    deal["revision"] += 1
    deal["states"]["analysis"] = "needs_input"
    deal["states"]["execution_gate"] = "blocked"
    if deal["states"]["internal_closure"] == "closed":
        deal["states"]["internal_closure"] = "reconciling"
    save(
        conn,
        context["tenant"],
        "deal",
        deal,
        parent=workspace["id"],
        dataset=deal["dataset_id"],
        snapshot=True,
    )


def analysis_view(conn, tenant, parent, row):
    from datetime import date

    from packages.domain.dependencies import CALCULATOR_VERSION

    view = deepcopy(row)
    reasons = []
    if row.get("calculator_version") != CALCULATOR_VERSION:
        reasons.append(
            issue(
                "CALCULATOR_SUPERSEDED",
                "This historical result predates the current calculator/dependency policy; recalculate before new review or action.",
            )
        )
    if row.get("base_deal_hash") != current_fact_hash(conn, tenant, parent):
        reasons.append(
            issue(
                "STALE_INPUT",
                "This historical analysis binds earlier inputs; recalculate current facts.",
            )
        )
    if parent["execution_scope"] == "demo":
        from packages.domain.demo import MANIFEST

        today = date.fromisoformat(MANIFEST["reference_date"])
    else:
        today = store.now().date()
    if row.get("dependency_policy") == "scoped-evidence-2":
        current_sources = [
            get(conn, tenant, "evidence", identifier)
            for identifier in row["input_evidence_ids"]
        ]
        if digest(current_sources) != row["evidence_digest"]:
            reasons.append(
                issue(
                    "STALE_EVIDENCE_REVISION",
                    "A selected source changed after this calculation.",
                )
            )
    for observation in children(conn, tenant, "market_observation", parent):
        if (
            observation["id"] in row.get("price_range", {}).get("comparator_ids", [])
            and observation.get("valid_until")
            and date.fromisoformat(observation["valid_until"]) < today
        ):
            reasons.append(
                issue("EXPIRED_MARKET_COMPARATOR", "A selected comparator has expired.")
            )
    for identifier in row["input_evidence_ids"]:
        source = get(conn, tenant, "evidence", identifier)
        if (
            source.get("effective_from")
            and date.fromisoformat(source["effective_from"]) > today
        ):
            reasons.append(
                issue(
                    "FUTURE_EVIDENCE",
                    "An input source is not effective yet; review applicability before using the result.",
                )
            )
        if (
            source["valid_until"]
            and date.fromisoformat(source["valid_until"]) < today
            or source["review_status"] == "expired"
        ):
            reasons.append(
                issue(
                    "EXPIRED_EVIDENCE",
                    "An input source has expired; review and recalculate.",
                )
            )
    view.update(current_for_use=not reasons, invalidation_reasons=reasons)
    return view


def validate_embedded_evidence(conn, tenant, parent, value):
    if isinstance(value, dict):
        for key, child in value.items():
            if key in {
                "evidence_ids",
                "source_ids",
                "fulfillment_evidence_ids",
                "external_facility_evidence_ids",
            } and isinstance(child, list):
                evidence_refs(conn, tenant, parent, child)
            else:
                validate_embedded_evidence(conn, tenant, parent, child)
    elif isinstance(value, list):
        for child in value:
            validate_embedded_evidence(conn, tenant, parent, child)


def validate_allocation_targets(parent, allocations):
    validate_allocations(allocations)
    lines = {line["id"] for line in parent["line_items"]}
    shipments = {s["id"] for s in parent["shipments"]}
    for allocation in allocations:
        if (
            allocation["line_item_id"]
            and allocation["line_item_id"] not in lines
            or allocation["shipment_id"]
            and allocation["shipment_id"] not in shipments
        ):
            raise DomainError(
                "ALLOCATION_REFERENCE",
                "Allocation must reference declared deal lines/shipments.",
            )
