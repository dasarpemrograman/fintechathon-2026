"""Material source selection; unrelated/retired evidence stays in history."""

from decimal import Decimal, localcontext
from services.api.store import digest

CALCULATOR_VERSION = "decimal-2"
DEPENDENCY_POLICY = "scoped-evidence-2"


def references(value):
    result = set()
    if isinstance(value, dict):
        for key, item in value.items():
            if key.endswith("evidence_ids") and isinstance(item, list):
                result.update(item)
            else:
                result.update(references(item))
    elif isinstance(value, list):
        for item in value:
            result.update(references(item))
    return result


def selected_fx(parent, resources, funding_ids=()):
    currencies = {parent["reporting_currency"]}

    def money(value):
        if isinstance(value, dict):
            for key, item in value.items():
                if key == "currency" and isinstance(item, str):
                    currencies.add(item)
                else:
                    money(item)
        elif isinstance(value, list):
            for item in value:
                money(item)

    money(parent)
    for kind in ["cost_line", "obligation", "market_observation"]:
        money(resources.get(kind, []))
    money(
        [row for row in resources.get("funding_option", []) if row["id"] in funding_ids]
    )
    selected = []
    seen = set()
    explicit = {
        row.get("actual_fx_observation_id") for row in resources.get("cost_line", [])
    } | {row.get("fx_observation_id") for row in resources.get("receipt", [])}
    for row in reversed(resources.get("fx_observation", [])):
        pair = frozenset([row["base_currency"], row["quote_currency"]])
        if row["id"] in explicit or pair <= currencies and pair not in seen:
            selected.append(row)
            seen.add(pair)
    return list(reversed(selected))


def material_ids(parent, resources, funding_ids=(), bank_reviews=(), today=None):
    result = references(
        {
            key: value
            for key, value in parent.items()
            if key not in {"evidence_ids", "procurement"}
        }
    )
    for row in resources.get("cost_line", []):
        result.update(
            row.get("actual_evidence_ids", row["evidence_ids"])
            if row.get("actual_amount") is not None
            else row["evidence_ids"]
        )
    for kind in ["obligation", "requirement", "milestone"]:
        for row in resources.get(kind, []):
            result.update(references(row))
    receipts = resources.get("receipt", [])
    superseded = {row["supersedes"] for row in receipts if row.get("supersedes")}
    for row in receipts:
        if row["status"] == "verified" and row["id"] not in superseded:
            result.update(row["evidence_ids"])
    for row in selected_fx(parent, resources, funding_ids):
        result.update(row["evidence_ids"])
    snapshot = parent.get("constraints", {}).get("cash_snapshot")
    if snapshot:
        for review in bank_reviews:
            if (
                review["purpose"] == "cash_resources"
                and review["decision"] == "approved"
                and review["analysis_hash"] == digest(snapshot)
            ):
                result.update(review.get("evidence_ids", []))
    chosen = [
        row for row in resources.get("funding_option", []) if row["id"] in funding_ids
    ]
    product_ids = {row["product_id"] for row in chosen if row["product_id"]}
    for row in chosen + [
        row for row in resources.get("finance_product", []) if row["id"] in product_ids
    ]:
        result.update(references(row))
        result.update(row.get("source_ids", []))
    if today is not None and parent.get("line_items"):
        from packages.domain.pricing import normalized_range

        price = normalized_range(
            parent,
            {"seller_floor": None, "assumptions": []},
            resources.get("market_observation", []),
            selected_fx(parent, resources, funding_ids),
            today,
            resources.get("evidence", []),
        )
        for row in resources.get("market_observation", []):
            if row["id"] in price.get("comparator_ids", []):
                result.update(row["evidence_ids"])
    return result
