"""Explicit high-level estimates map to the canonical shared planning model."""

from decimal import Decimal
from copy import deepcopy
from services.api.store import DomainError
from packages.domain.economics import number


def local_instant(value, timezone):
    from datetime import datetime, timezone as utc_timezone
    from zoneinfo import ZoneInfo

    try:
        local = datetime.fromisoformat(value)
        if local.tzinfo is not None:
            raise ValueError()
        zone = ZoneInfo(timezone)
        candidates = [local.replace(tzinfo=zone, fold=fold) for fold in [0, 1]]
        valid = [
            candidate
            for candidate in candidates
            if candidate.astimezone(utc_timezone.utc)
            .astimezone(zone)
            .replace(tzinfo=None)
            == local
        ]
        if not valid or len({candidate.utcoffset() for candidate in valid}) != 1:
            raise ValueError()
        return valid[0].astimezone(utc_timezone.utc).isoformat().replace("+00:00", "Z")
    except ValueError:
        raise DomainError(
            "LOCAL_TIME_UNRESOLVED",
            "Choose a valid, unambiguous local date and time; an explicit offset may be needed around clock changes.",
        )


def estimate(workspace, body):
    body = deepcopy(body)
    for local_key, target in [
        ("deposit", "deposit_at"),
        ("balance", "balance_at"),
        ("supplier", "supplier_payment_at"),
    ]:
        value = body.get("local_payment_times", {}).get(local_key)
        if value:
            if body[target] is not None:
                raise DomainError(
                    "DUPLICATE_SCENARIO_TIME",
                    "Provide either a local scenario time or an explicit temporal value.",
                )
            body[target] = {
                "instant": local_instant(value, workspace["owner_timezone"]),
                "timezone": workspace["owner_timezone"],
            }
    if body.get("local_cash_snapshot"):
        if body["cash_snapshot"] is not None:
            raise DomainError(
                "DUPLICATE_CASH_SNAPSHOT", "Provide one cash snapshot representation."
            )
        cash = body["local_cash_snapshot"]
        body["cash_snapshot"] = {
            key: cash[key]
            for key in ["available", "committed_elsewhere", "minimum_buffer"]
        }
        body["cash_snapshot"]["as_of"] = local_instant(
            cash["local_datetime"], workspace["owner_timezone"]
        )
    if body.get("target_margin_percent") is not None:
        if body["target_margin"] is not None:
            raise DomainError(
                "DUPLICATE_MARGIN", "Supply only one margin representation."
            )
        body["target_margin"] = format(
            number(body["target_margin_percent"]) / Decimal(100), "f"
        )
    quantity = number(body["quantity"])
    unit_cost = body["unit_cost"]
    invoice = body["invoice_amount"]
    deposit = body["deposit_amount"]
    if quantity <= 0:
        raise DomainError("QUANTITY_REQUIRED", "Quantity must be greater than zero.")
    if body["target_margin"] is not None and number(body["target_margin"]) >= 1:
        raise DomainError("INVALID_MARGIN", "Target margin must be less than one.")
    ids = {
        role: workspace["id"] + "_" + role
        for role in [
            "seller",
            "buyer",
            "supplier",
            "line",
            "invoice_buyer",
            "invoice_supplier",
        ]
    }
    parties = [
        {
            "id": ids[role],
            "legal_name": None,
            "display_name": label,
            "registration_identifier": None,
            "country": workspace["seller_domicile"]
            if role != "buyer"
            else workspace["destination_country"],
            "roles": [role],
            "evidence_ids": body["evidence_ids"],
            "unknowns": [
                {
                    "field_path": "/legal_name",
                    "status": "missing",
                    "reason": "Hypothetical planning party; identity not confirmed.",
                }
            ],
        }
        for role, label in [
            ("seller", "Exporter (planning)"),
            ("buyer", "Buyer (unconfirmed)"),
            ("supplier", "Input supplier (unconfirmed)"),
        ]
    ]
    line = {
        "id": ids["line"],
        "product": deepcopy(workspace["product"]),
        "quantity": body["quantity"],
        "unit": body["unit"],
        "goods_origin_country": workspace["dispatch_country"],
        "evidence_ids": body["evidence_ids"],
        "unknowns": [],
    }
    invoices = []
    terms = []
    cost = (
        {
            "amount": format(quantity * number(unit_cost["amount"]), "f"),
            "currency": unit_cost["currency"],
        }
        if unit_cost
        else None
    )
    for name, amount, payer, payee, side in [
        ("invoice_buyer", invoice, "buyer", "seller", "buyer"),
        ("invoice_supplier", cost, "seller", "supplier", "supplier"),
    ]:
        if amount:
            invoices.append(
                {
                    "id": ids[name],
                    "side": side,
                    "payer_party_id": ids[payer],
                    "payee_party_id": ids[payee],
                    "amount": amount,
                    "allocations": [],
                    "evidence_ids": body["evidence_ids"],
                }
            )

    def term(name, amount, date, payer, payee, side):
        if amount is None or date is None:
            return
        terms.append(
            {
                "id": workspace["id"] + "_term_" + name,
                "side": side,
                "payer_id": ids[payer],
                "payee_id": ids[payee],
                "invoice_id": ids[
                    "invoice_buyer" if side == "buyer" else "invoice_supplier"
                ],
                "amount": amount,
                "invoice_fraction": None,
                "schedule": {"kind": "fixed", "due": date},
                "instrument": "milestone",
                "instrument_details": "User planning assumption, not agreement",
                "status": "proposed",
                "allocations": [],
                "evidence_ids": body["evidence_ids"],
                "unknowns": [],
            }
        )

    if deposit:
        if (
            not invoice
            or deposit["currency"] != invoice["currency"]
            or number(deposit["amount"]) > number(invoice["amount"])
        ):
            raise DomainError(
                "DEPOSIT_AMOUNT",
                "Deposit must use the invoice currency and not exceed the invoice.",
            )
        term("deposit", deposit, body["deposit_at"], "buyer", "seller", "buyer")
    if invoice:
        balance = {
            "amount": format(
                number(invoice["amount"])
                - (number(deposit["amount"]) if deposit else Decimal(0)),
                "f",
            ),
            "currency": invoice["currency"],
        }
        term("balance", balance, body["balance_at"], "buyer", "seller", "buyer")
    term("cost", cost, body["supplier_payment_at"], "seller", "supplier", "supplier")
    supplier_terms = [t["id"] for t in terms if t["payee_id"] == ids["supplier"]]
    if workspace["business_profile"] == "reseller":
        procurement = {
            "business_profile": "reseller",
            "purchase_lines": [
                {
                    "line_item_id": ids["line"],
                    "supplier_party_id": ids["supplier"],
                    "quantity": body["quantity"],
                    "unit": body["unit"],
                    "unit_cost": unit_cost,
                    "payment_term_ids": supplier_terms,
                    "evidence_ids": body["evidence_ids"],
                }
            ],
            "unknowns": [],
        }
    else:
        procurement = {
            "business_profile": "producer",
            "inputs": [
                {
                    "id": workspace["id"] + "_input",
                    "description": "User-estimated production input economics; expand BOM before execution.",
                    "quantity": body["quantity"],
                    "unit": body["unit"],
                    "unit_cost": unit_cost,
                    "supplier_party_id": ids["supplier"],
                    "payment_term_ids": supplier_terms,
                    "evidence_ids": body["evidence_ids"],
                }
            ],
            "costs": [],
            "usable_yield": None,
            "batch_quantity": body["quantity"],
            "unit": body["unit"],
            "capacity_quantity": None,
            "capacity_period": None,
            "milestone_ids": [],
            "unknowns": [
                {
                    "field_path": "/procurement/capacity",
                    "status": "missing",
                    "reason": "Detailed production capacity/yield remain unconfirmed.",
                }
            ],
        }
    if workspace["business_profile"] == "producer":
        next(p for p in parties if p["id"] == ids["supplier"])["roles"] = [
            "production_input"
        ]
        for invoice in invoices:
            if invoice["side"] == "supplier":
                invoice["side"] = "production_input"
        for payment in terms:
            if payment["side"] == "supplier":
                payment["side"] = "production_input"
    return {
        "parties": parties,
        "line_items": [line],
        "shipments": [],
        "payment_terms": terms,
        "procurement": procurement,
        "constraints": {
            "cash_snapshot": body["cash_snapshot"],
            "target_contribution_margin": body["target_margin"],
            "delivery_deadline": None,
            "credit_tenor_limit_days": None,
            "allowable_changes": [],
            "ranking_preference": None,
            "unknowns": [],
        },
        "invoices": invoices,
        "cost_lines": [],
        "fx_observations": [],
    }
