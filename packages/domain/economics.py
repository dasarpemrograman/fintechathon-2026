"""Deterministic Decimal economics. No network, model calls or wire-schema copies."""

from collections import defaultdict
from copy import deepcopy
from datetime import datetime, timedelta
from decimal import (
    Decimal,
    localcontext,
    ROUND_HALF_UP,
    ROUND_FLOOR,
    ROUND_CEILING,
    InvalidOperation,
)
import re
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError
import pycountry
from services.api.store import DomainError, issue

DECIMAL = re.compile(r"^(0|[1-9][0-9]*)(\.[0-9]+)?$")


def number(value, signed=False):
    if not isinstance(value, str) or not re.fullmatch(
        r"-?(0|[1-9][0-9]*)(\.[0-9]+)?" if signed else DECIMAL.pattern, value
    ):
        raise DomainError("INVALID_DECIMAL", "Use finite base-10 decimal strings.")
    result = Decimal(value)
    if not result.is_finite():
        raise DomainError("INVALID_DECIMAL", "Amount must be finite.")
    return result


def output(value, rounding=ROUND_HALF_UP):
    return format(value.quantize(Decimal(".01"), rounding=rounding), "f")


def currency(code):
    if pycountry.currencies.get(alpha_3=code) is None:
        raise DomainError("INVALID_CURRENCY", "Unknown ISO currency code.")
    return code


def convert(money, target, fx):
    currency(target)
    currency(money["currency"])
    amount = number(money["amount"])
    if money["currency"] == target:
        return amount
    for observation in reversed(fx):
        rate = number(observation["rate"])
        if rate <= 0:
            raise DomainError("INVALID_FX", "FX rate must be positive.")
        if (observation["base_currency"], observation["quote_currency"]) == (
            money["currency"],
            target,
        ):
            return amount * rate
        if (observation["quote_currency"], observation["base_currency"]) == (
            money["currency"],
            target,
        ):
            return amount / rate
    raise DomainError(
        "FX_MISSING", "No dated FX observation covers this currency conversion."
    )


def freight(mode, packages, gross_kg, rate, minimum="0", divisor=None, containers=None):
    gross = number(gross_kg)
    price = number(rate)
    floor = number(minimum)
    if mode == "sea_lcl":
        volume = sum(
            (
                Decimal(p["count"])
                * number(p["length_cm"])
                * number(p["width_cm"])
                * number(p["height_cm"])
                / Decimal("1000000")
                for p in packages
            ),
            Decimal(0),
        )
        basis = max(volume, gross / Decimal(1000))
    elif mode == "air":
        if divisor is None or number(divisor) <= 0:
            raise DomainError("AIR_DIVISOR_MISSING", "Use the quoted provider divisor.")
        volume = sum(
            (
                Decimal(p["count"])
                * number(p["length_cm"])
                * number(p["width_cm"])
                * number(p["height_cm"])
                for p in packages
            ),
            Decimal(0),
        )
        basis = max(gross, volume / number(divisor))
    elif mode == "sea_fcl":
        if containers is None:
            raise DomainError(
                "CONTAINER_COUNT_MISSING", "Container quantity is required."
            )
        basis = number(containers)
    else:
        raise DomainError(
            "UNSUPPORTED_FREIGHT", "No applicable quoted calculation rule is declared."
        )
    return max(floor, basis * price)


def temporal(value):
    if not value or "instant" not in value:
        raise DomainError(
            "EXACT_TIME_MISSING",
            "An exact dated scenario instant is required; preserve local dates separately.",
        )
    result = datetime.fromisoformat(value["instant"].replace("Z", "+00:00"))
    if result.tzinfo is None:
        raise DomainError("TIMEZONE_MISSING", "Scenario instants require an offset.")
    try:
        return result.astimezone(ZoneInfo(value["timezone"]))
    except ZoneInfoNotFoundError:
        raise DomainError("INVALID_TIMEZONE", "Use a known IANA timezone.")


def validate_date_graph(milestones):
    complete = set()
    active = set()

    def visit(identifier):
        if identifier in active:
            raise DomainError(
                "DATE_CYCLE",
                "Milestone dependencies must be acyclic even when a forecast is known.",
            )
        if identifier in complete:
            return
        active.add(identifier)
        schedule = milestones[identifier].get("schedule", {})
        if schedule.get("kind") == "event_relative":
            target = schedule["anchor_milestone_id"]
            if target not in milestones:
                raise DomainError("ANCHOR_MISSING", "Milestone anchor is unresolved.")
            visit(target)
        active.remove(identifier)
        complete.add(identifier)

    for identifier in milestones:
        visit(identifier)


def resolve_schedule(schedule, milestones, calendars, trail=()):
    if not trail:
        validate_date_graph(milestones)
    if schedule["kind"] == "fixed":
        return temporal(schedule["due"])
    identifier = schedule["anchor_milestone_id"]
    if identifier in trail:
        raise DomainError("DATE_CYCLE", "Milestone dependencies must be acyclic.")
    anchor = milestones.get(identifier)
    if not anchor:
        raise DomainError("ANCHOR_MISSING", "Payment anchor is unresolved.")
    value = (
        anchor.get("actual")
        or anchor.get("forecast")
        or anchor.get("agreed")
        or anchor.get("proposed")
    )
    instant = (
        temporal(value)
        if value
        else resolve_schedule(
            anchor["schedule"], milestones, calendars, trail + (identifier,)
        )
    )
    offset = schedule["offset_days"]
    if schedule["day_basis"] == "calendar":
        return instant + timedelta(days=offset)
    calendar = calendars.get(schedule.get("business_calendar_id"))
    if not calendar:
        raise DomainError(
            "BUSINESS_CALENDAR_MISSING",
            "A named business-day/holiday calendar is required.",
        )
    local = instant.astimezone(ZoneInfo(calendar["timezone"]))
    step = 1 if offset >= 0 else -1
    remaining = abs(offset)
    while remaining:
        local += timedelta(days=step)
        if (
            local.weekday() not in calendar["weekend_days"]
            and local.date().isoformat() not in calendar["holidays"]
        ):
            remaining -= 1
    return local


def cash_metrics(events, opening, buffer, currency_code, horizon=None, unresolved=None):
    """Events are internal exact Decimal values; original source strings remain outside."""
    warnings = []
    grouped = defaultdict(list)
    for event in events:
        grouped[event["at"]].append(event)
    ordered = []
    for at, items in sorted(grouped.items()):
        ambiguous = len(items) > 1 and any(
            item.get("sequence") is None for item in items
        )
        if ambiguous:
            warnings.append(
                issue(
                    "SAME_DAY_SEQUENCE_UNKNOWN", "Debit-first stress ordering was used."
                )
            )
        ordered += sorted(
            items,
            key=lambda e: (0 if e["direction"] == "out" else 1, e.get("id", ""))
            if ambiguous
            else (e.get("sequence") or 0, e.get("id", "")),
        )
    balance = opening
    minimum = opening
    operating = Decimal(0)
    minimum_operating = Decimal(0)
    minimum_at = None
    negative_start = None
    intervals = []
    timeline = []
    for event in ordered:
        change = event["amount"] * (1 if event["direction"] == "in" else -1)
        balance += change
        source = event.get("source_id") or event.get("id")
        timeline.append(
            {
                "at": event["at"].isoformat(),
                "direction": event["direction"],
                "amount": {
                    "amount": output(event["amount"]),
                    "currency": currency_code,
                },
                "balance": {"amount": output(balance), "currency": currency_code},
                "source_ref": {"id": source} if source else None,
            }
        )
        operating += change
        minimum_operating = min(minimum_operating, operating)
        if balance < minimum:
            minimum = balance
            minimum_at = event["at"]
        if balance < 0 and negative_start is None:
            negative_start = event["at"]
        if balance >= 0 and negative_start is not None:
            intervals.append(
                {"start": negative_start.isoformat(), "end": event["at"].isoformat()}
            )
            negative_start = None
    if negative_start:
        intervals.append({"start": negative_start.isoformat(), "end": None})
    if horizon is None:
        if not events:
            raise DomainError(
                "CASH_HORIZON_MISSING", "A dated snapshot or event horizon is required."
            )
        horizon = max(e["at"] for e in events)
    result = {
        "reporting_currency": currency_code,
        "minimum_cash": output(minimum, ROUND_FLOOR),
        "minimum_at": minimum_at.isoformat() if minimum_at else None,
        "peak_cash_gap": output(max(Decimal(0), -minimum), ROUND_CEILING),
        "buffer_shortfall": output(max(Decimal(0), buffer - minimum), ROUND_CEILING),
        "required_own_funds": output(
            max(Decimal(0), buffer - min(Decimal(0), minimum_operating)), ROUND_CEILING
        ),
        "final_cash": output(balance),
        "negative_intervals": intervals,
        "event_balances": timeline,
        "horizon_end": horizon.isoformat(),
        "unresolved_obligation_ids": unresolved or [],
        "calculation_scope": "known_items_only"
        if unresolved
        else "complete_for_declared_inputs",
    }
    return result, warnings


def cost_amount(line, reporting, fx, revenue=None):
    if line.get("actual_amount"):
        selected = fx
        if line["actual_amount"]["currency"] != reporting:
            selected = [
                row
                for row in fx
                if row.get("id") == line.get("actual_fx_observation_id")
            ]
            if not selected:
                return None
        return convert(line["actual_amount"], reporting, selected)
    shipment = line.get("freight_input")
    if shipment:
        rate = line.get("rate")
        if not rate:
            return None
        minimum = (
            convert(line["minimum_charge"], rate["currency"], fx)
            if line.get("minimum_charge")
            else Decimal(0)
        )
        amount = freight(
            shipment["mode"],
            shipment["packages"],
            shipment["gross_kg"],
            rate["amount"],
            format(minimum, "f"),
            shipment["quoted_divisor"],
            shipment["containers"],
        )
        return convert(
            {"amount": format(amount, "f"), "currency": rate["currency"]}, reporting, fx
        )
    explicit = line.get("estimate", {}).get("base")
    if explicit:
        return convert(explicit, reporting, fx)
    if line.get("basis") == "percentage":
        fraction = line.get("percentage_rate")
        return (
            revenue * number(fraction)
            if fraction is not None and revenue is not None
            else None
        )
    rate = line.get("rate")
    if rate and line.get("quantity") is not None:
        amount = convert(rate, reporting, fx) * number(line["quantity"])
        return max(
            amount,
            convert(line["minimum_charge"], reporting, fx)
            if line.get("minimum_charge")
            else Decimal(0),
        )
    return None


def validate_allocations(allocations):
    if not allocations:
        return
    total = Decimal(0)
    seen = set()
    for allocation in allocations:
        if not allocation["line_item_id"] and not allocation["shipment_id"]:
            raise DomainError(
                "ALLOCATION_TARGET", "Allocation requires a line or shipment."
            )
        target = (allocation["line_item_id"], allocation["shipment_id"])
        if target in seen:
            raise DomainError(
                "DUPLICATE_ALLOCATION", "Allocation target is duplicated."
            )
        seen.add(target)
        fraction = number(allocation["fraction"])
        if fraction > 1:
            raise DomainError(
                "ALLOCATION_FRACTION", "Allocation fraction cannot exceed one."
            )
        total += fraction
    if total != 1:
        raise DomainError("ALLOCATION_TOTAL", "Allocation fractions must sum to one.")


def compute(
    deal, costs, obligations, milestones, fx, calendars, funding=None, receipts=None
):
    with localcontext() as context:
        context.prec = 50
        return _compute(
            deal,
            costs,
            obligations,
            milestones,
            fx,
            calendars,
            funding or [],
            receipts or [],
        )


def _compute(deal, costs, obligations, milestones, fx, calendars, funding, receipts):
    reporting = deal["reporting_currency"]
    currency(reporting)
    warnings = []
    blockers = []
    unknowns = []
    unknown_cost = []
    covered = set()
    unknown_seller = []
    sales_rate = Decimal(0)
    expense = Decimal(0)
    extras = Decimal(0)
    tax = Decimal(0)
    advances = Decimal(0)
    sellers = {party["id"] for party in deal["parties"] if "seller" in party["roles"]}
    gross_revenue = sum(
        (
            convert(invoice["amount"], reporting, fx)
            for invoice in deal["invoices"]
            if invoice["side"] == "buyer"
        ),
        Decimal(0),
    )
    reimbursed = sum(
        (
            convert(invoice["reimbursable_amount"], reporting, fx)
            for invoice in deal["invoices"]
            if invoice["side"] == "buyer" and invoice.get("reimbursable_amount")
        ),
        Decimal(0),
    )
    if reimbursed > gross_revenue:
        raise DomainError(
            "INVOICE_REIMBURSEMENT", "Reimbursable amounts cannot exceed the invoice."
        )
    revenue = gross_revenue - reimbursed
    if not deal["invoices"]:
        blockers.append(
            issue(
                "INVOICES_MISSING",
                "Invoice revenue inputs are not established.",
                "/invoices",
            )
        )
    if not sellers:
        blockers.append(
            issue("SELLER_MISSING", "Seller party is unresolved.", "/parties")
        )
    for line in costs:
        validate_allocations(line["allocations"])
        components = set(line["covered_components"] or [line["component_key"]])
        if covered & components:
            raise DomainError(
                "DUPLICATE_COST_COVERAGE",
                "Overlapping quotation components would be counted twice.",
            )
        covered |= components
        amount = cost_amount(line, reporting, fx, revenue)
        seller_bears = line["economic_bearer_party_id"] in sellers
        if amount is None:
            unknown_cost.append(line["id"])
            if seller_bears and line["treatment"] == "expense":
                unknown_seller.append(line["id"])
            unknowns.append(
                {
                    "status": "missing",
                    "reason": "Applicable cost amount is unknown.",
                    "field_path": "/cost_lines/" + line["id"],
                }
            )
            continue
        seller_bears = line["economic_bearer_party_id"] in sellers
        if line["treatment"] == "expense" and seller_bears:
            expense += amount
            if (
                line.get("basis") == "percentage"
                and not line.get("actual_amount")
                and line.get("percentage_rate") is not None
            ):
                sales_rate += number(line["percentage_rate"])
        elif line["treatment"] == "recoverable_tax":
            tax += amount
        elif line["treatment"] == "reimbursable_advance":
            advances += amount
        if not seller_bears:
            extras += amount
    timing_unknown = [
        line["id"]
        for line in costs
        if line.get("cash_treatment")
        not in {"paid_before_snapshot", "deducted_from_settlement"}
        and not line.get("payment_term_ids")
    ]
    if timing_unknown:
        blockers.append(
            issue(
                "COST_TIMING_UNKNOWN",
                "Material economic costs have no declared payment schedule or prior-payment evidence.",
                "/cost_lines",
            )
        )
    if unknown_cost:
        blockers.append(
            issue("COSTS_UNKNOWN", "Material costs are not established.", "/cost_lines")
        )
    snapshot = deal["constraints"]["cash_snapshot"]
    opening = Decimal(0)
    buffer = Decimal(0)
    if snapshot:
        opening = convert(snapshot["available"], reporting, fx) - convert(
            snapshot["committed_elsewhere"], reporting, fx
        )
        buffer = convert(snapshot["minimum_buffer"], reporting, fx)
    else:
        blockers.append(
            issue(
                "CASH_SNAPSHOT_MISSING",
                "Owner cash snapshot is unresolved.",
                "/constraints/cash_snapshot",
            )
        )
    by_milestone = {m["id"]: m for m in milestones}
    by_calendar = {c["id"]: c for c in calendars}
    events = []
    unresolved = []
    as_of = (
        datetime.fromisoformat(snapshot["as_of"].replace("Z", "+00:00"))
        if snapshot
        else None
    )
    origin = as_of or (
        datetime.fromisoformat(deal["created_at"].replace("Z", "+00:00"))
        if deal.get("created_at")
        else None
    )
    verified = defaultdict(list)
    reversed_ids = {
        r["supersedes"]
        for r in receipts
        if r["status"] == "reversed" and r.get("supersedes")
    }
    for receipt in receipts:
        if receipt["status"] == "verified" and receipt["id"] not in reversed_ids:
            for allocation in receipt["allocations"]:
                verified[allocation["obligation_id"]].append((receipt, allocation))
    from packages.domain.settlement import due_amount, approved_loss, collectible_amount

    write_off_loss = Decimal(0)
    realized_receivable_fx = Decimal(0)
    for obligation in obligations:
        if obligation["amount"] is None:
            unresolved.append(obligation["id"])
            continue
        total = convert(
            {
                "amount": format(due_amount(obligation), "f"),
                "currency": obligation["amount"]["currency"],
            },
            reporting,
            fx,
        )
        settled = Decimal(0)
        settled_native = Decimal(0)
        direction = "in" if obligation["payee_party_id"] in sellers else "out"
        for receipt, allocation in verified[obligation["id"]]:
            settled_native += number(allocation["amount"]["amount"])
            selected_fx = fx
            if allocation["amount"]["currency"] != reporting:
                selected_fx = [
                    row
                    for row in fx
                    if row.get("id") == receipt.get("fx_observation_id")
                ]
                if not selected_fx:
                    unresolved.append(obligation["id"])
                    warnings.append(
                        issue(
                            "ACTUAL_FX_REQUIRED",
                            "Foreign-currency settlement lacks its reviewed executed conversion; actual cash remains unknown.",
                        )
                    )
                    continue
            settled_amount = convert(allocation["amount"], reporting, selected_fx)
            if obligation["payee_party_id"] in sellers:
                realized_receivable_fx += settled_amount - convert(
                    allocation["amount"], reporting, fx
                )
            settled += settled_amount
            if receipt.get("settled_at"):
                actual = datetime.fromisoformat(
                    receipt["settled_at"].replace("Z", "+00:00")
                )
                if as_of and actual < as_of:
                    continue
                events.append(
                    {
                        "id": receipt["id"],
                        "at": actual,
                        "direction": direction,
                        "amount": settled_amount,
                        "sequence": receipt.get("sequence"),
                        "kind": "operating",
                    }
                )
            else:
                if (
                    as_of
                    and receipt["value_date"]
                    < as_of.astimezone(ZoneInfo(deal.get("owner_timezone", "UTC")))
                    .date()
                    .isoformat()
                ):
                    continue
                unresolved.append(obligation["id"])
                warnings.append(
                    issue(
                        "VALUE_DATE_ONLY",
                        "Verified receipt has a local value date but no exact intraday instant; cash timeline remains partial.",
                    )
                )
        native_remaining = max(
            Decimal(0), collectible_amount(obligation) - settled_native
        )
        remaining_valuation = convert(
            {
                "amount": format(native_remaining, "f"),
                "currency": obligation["amount"]["currency"],
            },
            reporting,
            fx,
        )
        if obligation.get("status") == "written_off" and not obligation.get(
            "write_off_amount"
        ):
            unresolved.append(obligation["id"])
            warnings.append(
                issue(
                    "WRITE_OFF_REVIEW_REQUIRED",
                    "The historical write-off needs an explicit reviewed amount; no additional loss is inferred.",
                )
            )
        if obligation["payee_party_id"] in sellers:
            write_off_loss += convert(
                {
                    "amount": format(approved_loss(obligation), "f"),
                    "currency": obligation["amount"]["currency"],
                },
                reporting,
                fx,
            )
        remaining = remaining_valuation
        if not remaining:
            continue
        try:
            at = resolve_schedule(obligation["schedule"], by_milestone, by_calendar)
        except DomainError as error:
            unresolved.append(obligation["id"])
            warnings.append(issue(error.code, error.reason))
            continue
        if remaining:
            if as_of and at < as_of:
                at = as_of
                warnings.append(
                    issue(
                        "OVERDUE_OBLIGATION",
                        "Outstanding past-due payment is stressed at the opening snapshot instant, not treated as already paid.",
                    )
                )
            events.append(
                {
                    "id": obligation["id"],
                    "at": at,
                    "direction": direction,
                    "amount": remaining,
                    "sequence": obligation.get("sequence"),
                    "kind": "operating",
                    "obligation_id": obligation["id"],
                    "forecast": True,
                }
            )
    by_obligation = {o["id"]: o for o in obligations}
    for invoice in deal.get("invoices", []):
        total = Decimal(0)
        for term in deal.get("payment_terms", []):
            if term["invoice_id"] != invoice["id"]:
                continue
            obligation = by_obligation.get(term["id"])
            if obligation and obligation["amount"]:
                total += convert(
                    obligation["amount"], invoice["amount"]["currency"], fx
                )
        if total < number(invoice["amount"]["amount"]):
            unresolved.append(invoice["id"])
            warnings.append(
                issue(
                    "INVOICE_BALANCE_UNSCHEDULED",
                    "Invoice installments do not cover the full declared balance.",
                )
            )
    if not obligations:
        unresolved.append("payment_schedule_unresolved")
    base, extra = cash_metrics(
        events,
        opening,
        buffer,
        reporting,
        horizon=max(
            [e["at"] for e in events] + ([origin] if origin else []), default=None
        ),
        unresolved=unresolved,
    )
    warnings += extra
    from packages.domain.financing import apply_financing

    financed, finance_cost, funding_unknown, finance_warnings, finance_blockers = (
        apply_financing(
            events,
            obligations,
            verified,
            funding,
            reporting,
            fx,
            by_milestone,
            by_calendar,
            as_of,
        )
    )
    warnings += finance_warnings
    blockers += finance_blockers
    after, extra = cash_metrics(
        financed,
        opening,
        buffer,
        reporting,
        horizon=max(
            [e["at"] for e in financed] + ([origin] if origin else []), default=None
        ),
        unresolved=unresolved,
    )
    warnings += extra
    if unresolved:
        blockers.append(
            issue(
                "CASH_TIMING_UNRESOLVED",
                "Funding requirements cover known items only.",
                "/payment_terms",
            )
        )
    if (
        unknown_cost
        or timing_unknown
        or not snapshot
        or not sellers
        or not deal["invoices"]
    ):
        base["calculation_scope"] = after["calculation_scope"] = "known_items_only"
    complete = not blockers
    economic_complete = (
        not unknown_seller
        and bool(sellers)
        and any(i["side"] == "buyer" for i in deal["invoices"])
    )
    contribution = revenue - expense - write_off_loss + realized_receivable_fx
    target = deal["constraints"]["target_contribution_margin"]
    floor = None
    if target is not None and not funding_unknown:
        margin = number(target)
        if margin >= 1:
            raise DomainError(
                "INVALID_MARGIN", "Target contribution margin must be less than one."
            )
        if margin + sales_rate >= 1:
            raise DomainError(
                "INVALID_MARGIN",
                "Margin plus sales-dependent cost fractions must be less than one.",
            )
        floor = (
            output(
                (expense - sales_rate * revenue + finance_cost)
                / (1 - margin - sales_rate)
            )
            if economic_complete
            else None
        )
    totals = {
        "reporting_currency": reporting,
        "seller_operating_expense": output(expense)
        if not unknown_seller and sellers
        else None,
        "buyer_extras_known": output(extras),
        "buyer_total": output(gross_revenue + max(Decimal(0), extras - reimbursed))
        if complete
        else None,
        "recoverable_tax_cash": output(tax),
        "reimbursable_advances": output(advances),
        "unknown_cost_ids": unknown_cost,
        "fx_observation_ids": [f["id"] for f in fx],
    }
    price = {
        "currency": reporting,
        "unit": "deal",
        "seller_floor": floor,
        "market_low": None,
        "market_high": None,
        "recommended_low": None,
        "recommended_high": None,
        "comparator_ids": [],
        "rejected_comparators": [],
        "assumptions": [],
        "label": "insufficient_data",
    }

    def economics(cost, metrics):
        return {
            "contribution": {
                "amount": output(contribution - cost),
                "currency": reporting,
            }
            if economic_complete
            else None,
            "cash_metrics": metrics,
            "funding_cost": {"amount": output(cost), "currency": reporting},
            "unknowns": unknowns,
        }

    breakdown = [
        {
            "cost_line_ref": {"id": line["id"]},
            "reporting_amount": {
                "amount": output(cost_amount(line, reporting, fx, revenue)),
                "currency": reporting,
            }
            if cost_amount(line, reporting, fx, revenue) is not None
            else None,
            "formula": "actual replaces estimate"
            if line.get("actual_amount")
            else "max(quoted minimum, quoted chargeable basis × rate)"
            if line.get("freight_input")
            else "sales revenue × declared fee fraction"
            if line.get("basis") == "percentage"
            else "declared base estimate or quantity × rate",
            "evidence_ids": line.get("evidence_ids", []),
        }
        for line in costs
    ]
    return {
        "cost_breakdown": breakdown,
        "cost_totals": totals,
        "price_range": price,
        "cash_metrics": None if funding_unknown else after if funding else base,
        "before_financing": economics(Decimal(0), base),
        "after_financing": {
            "contribution": None,
            "cash_metrics": None,
            "funding_cost": None,
            "unknowns": unknowns
            + [
                {
                    "status": "missing",
                    "field_path": "/funding/schedule",
                    "reason": "Financing terms are incomplete.",
                }
            ],
        }
        if funding_unknown
        else economics(finance_cost, after),
        "completeness": "scoped_complete" if complete else "partial",
        "blockers": blockers,
        "warnings": warnings,
        "unknowns": unknowns,
    }
