"""Nominal liabilities retain separately evidenced deductions and losses."""

from decimal import Decimal
from packages.domain.economics import number


def due_amount(obligation):
    if obligation["amount"] is None:
        return None
    return number(obligation["amount"]["amount"]) - sum(
        (
            number(row["amount"]["amount"])
            for row in obligation.get("settlement_deductions", [])
            if row["kind"] == "fee"
        ),
        Decimal(0),
    )


def approved_loss(obligation):
    value = obligation.get("write_off_amount")
    return number(value["amount"]) if value else Decimal(0)


def collectible_amount(obligation):
    due = due_amount(obligation)
    return None if due is None else max(Decimal(0), due - approved_loss(obligation))
