"""Dimensioned comparisons retain unknown actuals and immutable baselines."""

from datetime import datetime
from decimal import Decimal
from packages.domain.economics import number, output, resolve_schedule
from services.api.store import DomainError


def dimensions(
    baseline, parent, goods, obligations, receipts, fx_pairs, funding_actual
):
    rows = []

    def add(category, identifier, before, after, unit, basis, ids=(), difference=None):
        if before is not None and after is not None and difference is None:
            try:
                difference = format(Decimal(after) - Decimal(before), "f")
            except Exception:
                pass
        rows.append(
            {
                "category": category,
                "resource_ref": {"id": identifier},
                "baseline_value": before,
                "actual_value": after,
                "difference": difference,
                "unit": unit,
                "basis": basis,
                "evidence_ids": list(ids),
            }
        )

    original = baseline or {}
    for line in original.get("line_items", []):
        reviewed = [
            m
            for g in goods
            if g["status"] == "ready" and g["shipment_id"] is None
            for m in g.get("measurements", [])
            if m["line_item_id"] == line["id"]
            and m["attribute"] == "quantity"
            and m["unit"] == line["unit"]
        ]
        measured = reviewed[-1] if reviewed else None
        add(
            "quantity",
            line["id"],
            line["quantity"],
            measured["value"] if measured else None,
            line["unit"],
            "Whole-deal measured quantity; shipment-only or absent measurements remain unknown.",
            measured["evidence_ids"] if measured else [],
        )
    buyer_before = [
        row for row in original.get("invoices", []) if row["side"] == "buyer"
    ]
    buyer_after = [row for row in parent.get("invoices", []) if row["side"] == "buyer"]
    for invoice in buyer_before:
        current = next(
            (row for row in parent["invoices"] if row["id"] == invoice["id"]), None
        )
        # Only homogeneous invoice quantities support a meaningful unit price.
        old_lines = original.get("line_items", [])
        new_lines = parent.get("line_items", [])
        compatible = (
            len(buyer_before) == len(buyer_after) == 1
            and not invoice.get("allocations")
            and current is not None
            and not current.get("allocations")
            and old_lines
            and new_lines
            and len({r["unit"] for r in old_lines + new_lines}) == 1
        )
        old_qty = sum((number(row["quantity"]) for row in old_lines), Decimal(0))
        new_qty = sum((number(row["quantity"]) for row in new_lines), Decimal(0))
        old = (
            output(number(invoice["amount"]["amount"]) / old_qty)
            if compatible and old_qty
            else None
        )
        new = (
            output(number(current["amount"]["amount"]) / new_qty)
            if compatible
            and new_qty
            and current
            and current["amount"]["currency"] == invoice["amount"]["currency"]
            else None
        )
        add(
            "unit_price",
            invoice["id"],
            old,
            new,
            invoice["amount"]["currency"] + "/" + old_lines[0]["unit"]
            if compatible
            else invoice["amount"]["currency"],
            "Aggregate whole-deal buyer invoice per declared homogeneous goods quantity. Multiple or allocated invoices have no independently established unit price; verified cash recovery remains separate.",
            current.get("evidence_ids", []) if current else [],
        )
    by_id = {row["id"]: row for row in obligations}
    superseded = {r["supersedes"] for r in receipts if r.get("supersedes")}
    verified = [
        r for r in receipts if r["status"] == "verified" and r["id"] not in superseded
    ]
    for term in original.get("payment_terms", []):
        try:
            before = resolve_schedule(term["schedule"], {}, {}).isoformat()
        except DomainError:
            before = None
        relevant = [
            r
            for r in verified
            if any(a["obligation_id"] == term["id"] for a in r["allocations"])
        ]
        obligation = by_id.get(term["id"])
        actual = None
        if (
            obligation
            and obligation["status"] == "settled"
            and relevant
            and all(r.get("settled_at") for r in relevant)
        ):
            actual = max(r["settled_at"] for r in relevant)
        delta = (
            format(
                Decimal(
                    str(
                        (
                            datetime.fromisoformat(actual.replace("Z", "+00:00"))
                            - datetime.fromisoformat(before)
                        ).total_seconds()
                    )
                )
                / Decimal(86400),
                "f",
            )
            if actual and before
            else None
        )
        add(
            "timing",
            term["id"],
            before,
            actual,
            "days",
            "Final verified collection/payment against preserved fixed due instant. Relative or date-only anchors require review; no midnight is fabricated.",
            [i for r in relevant for i in r["evidence_ids"]],
            delta,
        )
    for identifier, before, after, unit, ids in fx_pairs:
        add(
            "fx",
            identifier,
            before,
            after,
            unit,
            "Preserved reference rate versus current reference valuation; this does not establish an executed bank conversion.",
            ids,
        )
    return rows
