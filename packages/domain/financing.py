"""Explicit loan and assigned-receivable cash, separate from sales revenue."""

from collections import defaultdict
from copy import deepcopy
from datetime import timedelta
from decimal import Decimal
from packages.domain.economics import convert, number, resolve_schedule
from services.api.store import DomainError, issue
from packages.domain.settlement import collectible_amount

COST_KINDS = {"finance_cost", "withheld_fee", "interest"}


def validate_assignments(parent, option, obligations):
    sellers = {party["id"] for party in parent["parties"] if "seller" in party["roles"]}
    by_id = {row["id"]: row for row in obligations}
    seen = set()
    for assignment in option.get("receivable_assignments", []):
        row = by_id.get(assignment["obligation_id"])
        if (
            not row
            or row["id"] in seen
            or row["payee_party_id"] not in sellers
            or not row.get("amount")
            or row.get("status") in {"settled", "written_off"}
        ):
            raise DomainError(
                "ASSIGNMENT_OBLIGATION",
                "Assign distinct outstanding buyer receivables from this deal.",
            )
        seen.add(row["id"])
        if (
            assignment["amount"]["currency"] != row["amount"]["currency"]
            or assignment["reserve_amount"]["currency"] != row["amount"]["currency"]
        ):
            raise DomainError(
                "ASSIGNMENT_CURRENCY",
                "Assigned face, obligation and reserve require matching native currency.",
            )
        amount = number(assignment["amount"]["amount"])
        if (
            amount <= 0
            or amount > number(row["amount"]["amount"])
            or number(assignment["reserve_amount"]["amount"]) > amount
        ):
            raise DomainError(
                "ASSIGNMENT_AMOUNT",
                "Assigned amount must be positive and within the outstanding receivable; reserve cannot exceed it.",
            )


def apply_financing(
    events, obligations, verified, funding, reporting, fx, milestones, calendars, as_of
):
    financed = deepcopy(events)
    cost = Decimal(0)
    unknown = False
    warnings = []
    blockers = []
    by_id = {row["id"]: row for row in obligations}
    assigned = defaultdict(Decimal)
    for option in funding:
        schedule = option["schedule"]
        assignments = option.get("receivable_assignments", [])
        kinds = {event["kind"] for event in schedule}
        if (
            not schedule
            or "loan_draw" not in kinds
            or not kinds & COST_KINDS
            or not assignments
            and "principal_repayment" not in kinds
        ):
            unknown = True
            blockers.append(
                issue(
                    "FUNDING_SCHEDULE_MISSING",
                    "Explicit draw, cost (including a sourced zero) and repayment or assigned-receivable settlement are required.",
                    "/funding",
                )
            )
            continue
        if assignments and "principal_repayment" in kinds:
            raise DomainError(
                "ASSIGNMENT_DOUBLE_REPAYMENT",
                "Assigned collection settles this facility; a second principal repayment would double count it.",
            )
        resolved = []
        for index, event in enumerate(schedule):
            try:
                at = resolve_schedule(event["schedule"], milestones, calendars)
            except DomainError as error:
                unknown = True
                warnings.append(issue(error.code, error.reason))
                continue
            amount = convert(event["amount"], reporting, fx)
            if event["kind"] in COST_KINDS:
                cost += amount
            resolved.append((index, event, at, amount))
        withheld = defaultdict(Decimal)
        for index, event, at, amount in resolved:
            if event["kind"] == "withheld_fee":
                matching = [
                    entry
                    for entry in resolved
                    if entry[1]["kind"] == "loan_draw"
                    and entry[2] == at
                    and entry[1]["amount"]["currency"] == event["amount"]["currency"]
                ]
                if len(matching) != 1:
                    raise DomainError(
                        "WITHHELD_FEE_DRAW",
                        "A withheld fee requires one matching draw at the same instant and currency.",
                    )
                withheld[matching[0][0]] += amount
        for index, event, at, amount in resolved:
            if event["kind"] == "withheld_fee":
                continue
            if event["kind"] == "loan_draw":
                amount -= withheld[index]
                if amount < 0:
                    raise DomainError(
                        "WITHHELD_FEE_AMOUNT", "Withheld fees cannot exceed the draw."
                    )
            if as_of and at < as_of and event["status"] == "actual_verified":
                continue
            financed.append(
                {
                    "id": option["id"] + "_" + str(index),
                    "source_id": option["id"],
                    "at": at,
                    "direction": "in" if event["kind"] == "loan_draw" else "out",
                    "amount": amount,
                    "sequence": event.get("sequence"),
                    "kind": event["kind"],
                }
            )
        face = Decimal(0)
        reserves = Decimal(0)
        for index, assignment in enumerate(assignments):
            row = by_id.get(assignment["obligation_id"])
            if (
                not row
                or not row.get("amount")
                or assignment["amount"]["currency"] != row["amount"]["currency"]
                or assignment["reserve_amount"]["currency"] != row["amount"]["currency"]
            ):
                raise DomainError(
                    "ASSIGNMENT_REFERENCE",
                    "Assignments need a current matching native-currency receivable.",
                )
            amount = convert(assignment["amount"], reporting, fx)
            reserve = convert(assignment["reserve_amount"], reporting, fx)
            paid = sum(
                (
                    convert(allocation["amount"], reporting, fx)
                    for _, allocation in verified[row["id"]]
                ),
                Decimal(0),
            )
            remaining = max(
                Decimal(0),
                convert(
                    {
                        "amount": format(collectible_amount(row), "f"),
                        "currency": row["amount"]["currency"],
                    },
                    reporting,
                    fx,
                )
                - paid,
            )
            assigned[row["id"]] += amount
            if amount <= 0 or reserve > amount or assigned[row["id"]] > remaining:
                raise DomainError(
                    "RECEIVABLE_ALREADY_COLLECTED_OR_ASSIGNED",
                    "Selected assignments exceed the remaining uncollected receivable.",
                )
            forecast = next(
                (
                    entry
                    for entry in financed
                    if entry.get("forecast") and entry.get("obligation_id") == row["id"]
                ),
                None,
            )
            if forecast is None:
                unknown = True
                blockers.append(
                    issue(
                        "ASSIGNED_COLLECTION_UNRESOLVED",
                        "Reserve release remains unknown until the assigned collection date is resolvable.",
                    )
                )
                continue
            forecast["amount"] -= amount
            collection = forecast["at"]
            draw_dates = [
                at for _, event, at, _ in resolved if event["kind"] == "loan_draw"
            ]
            if draw_dates and max(draw_dates) > collection:
                raise DomainError(
                    "ASSIGNMENT_AFTER_COLLECTION",
                    "A receivable advance cannot first draw after the modeled collection.",
                )
            financed.append(
                {
                    "id": option["id"] + "_reserve_" + str(index),
                    "source_id": option["id"],
                    "at": collection + timedelta(days=assignment["reserve_delay_days"]),
                    "direction": "in",
                    "amount": reserve,
                    "sequence": None,
                    "kind": "reserve_release",
                }
            )
            face += amount
            reserves += reserve
        if assignments and not unknown:
            draws = sum(
                (
                    amount
                    for _, event, _, amount in resolved
                    if event["kind"] == "loan_draw"
                ),
                Decimal(0),
            )
            if face != draws + reserves:
                raise DomainError(
                    "ASSIGNMENT_SETTLEMENT_MISMATCH",
                    "Assigned face must equal gross advance plus gross reserve. Financing costs are deducted separately; no unexplained settlement is assumed.",
                )
    return (
        [event for event in financed if event["amount"] != 0],
        cost,
        unknown,
        warnings,
        blockers,
    )
