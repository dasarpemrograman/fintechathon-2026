"""Native-currency cash-cost coverage without reusing one liability twice."""

from collections import defaultdict, deque
from decimal import Decimal, localcontext
from packages.domain.economics import cost_amount, number, convert
from packages.domain.settlement import due_amount
from services.api.store import DomainError


def covered(parent, costs, obligations, fx):
    with localcontext() as context:
        context.prec = 50
        return _covered(parent, costs, obligations, fx)


def _covered(parent, costs, obligations, fx):
    sellers = {party["id"] for party in parent["parties"] if "seller" in party["roles"]}
    capacities = {
        row["id"]: row
        for row in obligations
        if row["payer_party_id"] in sellers and row["amount"] is not None
    }
    demands = []
    for cost in costs:
        if (
            cost["payer_party_id"] not in sellers
            or cost.get("cash_treatment") == "paid_before_snapshot"
        ):
            continue
        native = (
            cost.get("actual_amount") or cost["estimate"]["base"] or cost.get("rate")
        )
        if native is None and cost.get("basis") == "percentage":
            currencies = {
                capacities[identifier]["amount"]["currency"]
                for identifier in cost.get("payment_term_ids", [])
                if identifier in capacities
            }
            if len(currencies) == 1:
                native = {"currency": currencies.pop()}
        if native is None:
            return False
        try:
            revenue = sum(
                (
                    convert(invoice["amount"], native["currency"], fx)
                    - (
                        convert(invoice["reimbursable_amount"], native["currency"], fx)
                        if invoice.get("reimbursable_amount")
                        else Decimal(0)
                    )
                    for invoice in parent.get("invoices", [])
                    if invoice["payee_party_id"] in sellers
                ),
                Decimal(0),
            )
            amount = cost_amount(cost, native["currency"], fx, revenue)
        except DomainError:
            return False
        if amount is None:
            return False
        targets = [
            identifier
            for identifier in cost.get("payment_term_ids", [])
            if identifier in capacities
            and capacities[identifier]["amount"]["currency"] == native["currency"]
        ]
        if amount and not targets:
            return False
        demands.append((cost["id"], amount, targets))
    # A bipartite residual network tests the full allocation constraints. A
    # shared all-in obligation supplies cash capacity once across all its costs.
    residual = defaultdict(dict)

    def edge(left, right, capacity):
        residual[left][right] = capacity
        residual[right].setdefault(left, Decimal(0))

    total = sum((amount for _, amount, _ in demands), Decimal(0))
    for identifier, row in capacities.items():
        edge(
            ("obligation", identifier),
            ("sink",),
            due_amount(row)
            - (
                number(row["write_off_amount"]["amount"])
                if row.get("write_off_amount")
                else Decimal(0)
            ),
        )
    for identifier, amount, targets in demands:
        node = ("cost", identifier)
        edge(("source",), node, amount)
        for target in targets:
            edge(node, ("obligation", target), amount)
    sent = Decimal(0)
    while sent < total:
        prior = {("source",): None}
        queue = deque([("source",)])
        while queue and ("sink",) not in prior:
            left = queue.popleft()
            for right, capacity in residual[left].items():
                if capacity > 0 and right not in prior:
                    prior[right] = left
                    queue.append(right)
        if ("sink",) not in prior:
            return False
        amount = total - sent
        right = ("sink",)
        while prior[right] is not None:
            left = prior[right]
            amount = min(amount, residual[left][right])
            right = left
        right = ("sink",)
        while prior[right] is not None:
            left = prior[right]
            residual[left][right] -= amount
            residual[right][left] += amount
            right = left
        sent += amount
    return True
