"""Deterministic owner-constraint comparisons; rankings never authorize action."""

from copy import deepcopy
from datetime import datetime
from packages.domain.settlement import collectible_amount
from decimal import Decimal, localcontext
from zoneinfo import ZoneInfo
from packages.domain.economics import number, convert, resolve_schedule
from services.api.store import DomainError


def assess(
    parent,
    scenario,
    result,
    obligations,
    milestones,
    fx,
    calendars,
    base_constraints,
    base_parent=None,
    receipts=None,
):
    with localcontext() as context:
        context.prec = 50
        return _assess(
            parent,
            scenario,
            result,
            obligations,
            milestones,
            fx,
            calendars,
            base_constraints,
            base_parent or parent,
            receipts or [],
        )


def _assess(
    parent,
    scenario,
    result,
    obligations,
    milestones,
    fx,
    calendars,
    constraints,
    base_parent,
    receipts,
):
    checks = []

    def check(code, status, reason):
        checks.append({"code": code, "status": status, "reason": reason})

    cash = result["cash_metrics"]
    contribution = result["after_financing"]["contribution"]
    expense = result["cost_totals"]["seller_operating_expense"]
    financing = result["after_financing"]["funding_cost"]
    margin = None
    if contribution is not None and expense is not None and financing is not None:
        revenue = (
            number(contribution["amount"], signed=True)
            + number(expense)
            + number(financing["amount"])
        )
        if revenue > 0:
            margin = number(contribution["amount"], signed=True) / revenue
    check(
        "DECLARED_INPUT_COMPLETENESS",
        "satisfied" if result["completeness"] != "partial" else "unknown",
        "Partial/unknown financial inputs remain explicit.",
    )
    check(
        "CASH_BUFFER",
        "unknown"
        if cash is None
        else "satisfied"
        if number(cash["buffer_shortfall"]) == 0
        else "failed",
        "Owner buffer must be preserved through the full liability horizon.",
    )
    if constraints["target_contribution_margin"] is not None:
        check(
            "TARGET_MARGIN",
            "unknown"
            if margin is None
            else "satisfied"
            if margin >= number(constraints["target_contribution_margin"])
            else "failed",
            "Compare after-financing contribution with the declared owner margin.",
        )
    deadline = constraints["delivery_deadline"]
    delivery = []
    shipment = []
    for milestone in milestones:
        try:
            at = (
                resolve_schedule(
                    milestone["schedule"],
                    {m["id"]: m for m in milestones},
                    {c["id"]: c for c in calendars},
                )
                if not (
                    milestone.get("actual")
                    or milestone.get("forecast")
                    or milestone.get("agreed")
                    or milestone.get("proposed")
                )
                else resolve_schedule(
                    {
                        "kind": "event_relative",
                        "anchor_milestone_id": milestone["id"],
                        "offset_days": 0,
                        "day_basis": "calendar",
                        "business_calendar_id": None,
                    },
                    {m["id"]: m for m in milestones},
                    {c["id"]: c for c in calendars},
                )
            )
        except DomainError:
            continue
        if milestone["kind"] in {"arrival", "delivery", "acceptance"}:
            delivery.append(at)
        if milestone["kind"] in {"shipment", "dispatch", "departure", "sailing"}:
            shipment.append(at)
    if deadline:
        status = "unknown"
        if delivery:
            if "instant" in deadline:
                fits = max(delivery) <= datetime.fromisoformat(
                    deadline["instant"].replace("Z", "+00:00")
                )
            else:
                fits = (
                    max(delivery)
                    .astimezone(ZoneInfo(deadline["timezone"]))
                    .date()
                    .isoformat()
                    <= deadline["date"]
                )
            status = "satisfied" if fits else "failed"
        check(
            "DELIVERY_DEADLINE",
            status,
            "Delivery needs a resolved dated forecast; no ETA is invented.",
        )
    sellers = {p["id"] for p in parent["parties"] if "seller" in p["roles"]}
    exposure = Decimal(0)
    due = []
    exposure_known = True
    for obligation in obligations:
        if obligation["payee_party_id"] not in sellers or obligation.get("status") in {
            "settled",
            "written_off",
        }:
            continue
        if obligation["amount"] is None:
            exposure_known = False
            continue
        try:
            superseded = {
                row["supersedes"] for row in receipts if row.get("supersedes")
            }
            paid = sum(
                (
                    convert(allocation["amount"], parent["reporting_currency"], fx)
                    for row in receipts
                    if row["status"] == "verified" and row["id"] not in superseded
                    for allocation in row["allocations"]
                    if allocation["obligation_id"] == obligation["id"]
                ),
                Decimal(0),
            )
            outstanding = max(
                Decimal(0),
                convert(
                    {
                        "amount": format(collectible_amount(obligation), "f"),
                        "currency": obligation["amount"]["currency"],
                    },
                    parent["reporting_currency"],
                    fx,
                )
                - paid,
            )
            exposure += outstanding
            if not outstanding:
                continue
            due.append(
                resolve_schedule(
                    obligation["schedule"],
                    {m["id"]: m for m in milestones},
                    {c["id"]: c for c in calendars},
                )
            )
        except DomainError:
            exposure_known = False
    if constraints["credit_tenor_limit_days"] is not None:
        status = (
            "unknown"
            if not shipment or not due
            else "satisfied"
            if (max(due) - min(shipment)).days <= constraints["credit_tenor_limit_days"]
            else "failed"
        )
        check(
            "CREDIT_TENOR",
            status,
            "Credit tenor needs shipment and buyer-payment anchors; exposure is not a default probability.",
        )
    allowed = {value.casefold().strip() for value in constraints["allowable_changes"]}
    for patch in scenario["patches"]:
        path = patch["path"]
        categories = []
        if path == "/payment_terms":
            old = {term["id"]: term for term in base_parent["payment_terms"]}
            changed = [
                term for term in patch["value"] if old.get(term["id"]) != term
            ] + [
                term
                for term in old.values()
                if term["id"] not in {new["id"] for new in patch["value"]}
            ]
            categories = [
                (
                    "buyer payment terms"
                    if term["side"] == "buyer"
                    else "supplier payment terms"
                )
                for term in changed
            ]
        else:
            categories = [
                {
                    "/procurement": "production inputs"
                    if parent["business_profile"] == "producer"
                    else "supplier procurement",
                    "/line_items": "goods specifications",
                    "/shipments": "shipment terms",
                    "/parties": "counterparty identities",
                    "/invoices": "invoice terms",
                    "/constraints": "owner constraints",
                }.get(path, path)
            ]
        check(
            "ALLOWABLE_CHANGE",
            "satisfied"
            if path in allowed or all(category in allowed for category in categories)
            else "failed",
            "Required change scope: " + ", ".join(sorted(set(categories))),
        )
    required = {
        identifier
        for patch in scenario["patches"]
        for identifier in patch["agreement_required_from"]
    }
    if any(
        patch["path"]
        in {
            "/payment_terms",
            "/procurement",
            "/line_items",
            "/shipments",
            "/parties",
            "/invoices",
        }
        for patch in scenario["patches"]
    ):
        required |= {
            party["id"] for party in parent["parties"] if "seller" not in party["roles"]
        }
    return {
        "rank": None,
        "ranking_preference": constraints["ranking_preference"],
        "margin_ratio": format(margin, "f") if margin is not None else None,
        "buyer_receivable_exposure": {
            "amount": format(exposure, "f"),
            "currency": parent["reporting_currency"],
        }
        if exposure_known
        else None,
        "checks": checks,
        "required_counterparty_ids": sorted(required),
        "basis": "Relative deterministic comparison of owner constraints, cash shortfall, margin and unpaid receivable exposure; not lender approval, default probability or execution authority.",
    }


def rank_views(rows):
    result = deepcopy(rows)
    eligible = [
        row
        for row in result
        if row.get("current_for_use", False)
        and row.get("owner_comparison", {}).get("ranking_preference")
    ]

    def key(row):
        view = row["owner_comparison"]
        failed = sum(check["status"] == "failed" for check in view["checks"])
        unknown = sum(check["status"] == "unknown" for check in view["checks"])
        cash = row["cash_metrics"]
        margin = (
            number(view["margin_ratio"], signed=True)
            if view["margin_ratio"] is not None
            else Decimal("-Infinity")
        )
        exposure = (
            number(view["buyer_receivable_exposure"]["amount"])
            if view["buyer_receivable_exposure"]
            else Decimal("Infinity")
        )
        gap = number(cash["buffer_shortfall"]) if cash else Decimal("Infinity")
        pref = view["ranking_preference"]
        metrics = (
            (-margin, gap, exposure)
            if pref == "margin"
            else (exposure, gap, -margin)
            if pref == "payment_risk"
            else (gap, -margin, exposure)
        )
        return (bool(failed), failed, unknown, *metrics, row["id"])

    for rank, row in enumerate(sorted(eligible, key=key), 1):
        row["owner_comparison"]["rank"] = rank
    return result
