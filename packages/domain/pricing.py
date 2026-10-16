"""Destination comparator normalization; unsupported observations stay excluded."""

from datetime import date
from decimal import Decimal
from packages.domain.economics import number, convert, output
from services.api.store import DomainError


def normalized_range(parent, price, observations, fx, as_of, evidence=None):
    result = dict(price)
    lines = parent["line_items"]
    accepted = []
    rejected = []
    seen = set()
    owners_seen = set()
    evidence_by_id = {row["id"]: row for row in evidence or []}
    if len(lines) != 1:
        result["assumptions"] += [
            "A destination price range needs a separately comparable product line."
        ]
        return result
    line = lines[0]
    product = line["product"]
    quantity = number(line["quantity"])
    unit = line["unit"]
    mass = {"kg": Decimal(1), "tonne": Decimal(1000), "g": Decimal(".001")}
    if quantity <= 0:
        raise DomainError("INVALID_QUANTITY", "Product quantity must be positive.")
    # Floor is per declared line unit, while contribution remains for the full deal.
    result["unit"] = unit
    if result["seller_floor"] is not None:
        result["seller_floor"] = output(number(result["seller_floor"]) / quantity)
    for observation in observations:
        reason = None
        source = tuple(sorted(observation["evidence_ids"]))
        owners = set()
        from packages.domain.discovery import source_owner

        for identifier in observation["evidence_ids"]:
            record = evidence_by_id.get(identifier)
            if record:
                if record.get("canonical_url"):
                    owners.add(source_owner(record["canonical_url"]))
                if record.get("publisher"):
                    owners.add(record["publisher"].strip().casefold())
        if source in seen or owners & owners_seen:
            reason = "Duplicate/syndicated publisher or independent-source set."
        elif observation["review_status"] != "confirmed":
            reason = "Source applicability is unreviewed."
        elif observation["segment"] != "wholesale":
            reason = "Retail/PPP observation is not an executable wholesale comparator."
        elif observation["destination_country"] not in {
            s["destination_country"] for s in parent["shipments"]
        } and observation["destination_country"] != parent.get("destination_country"):
            reason = "Destination jurisdiction differs."
        elif (
            observation["product_description"].casefold()
            != product["description"].casefold()
        ):
            reason = "Product identity differs."
        elif any(
            observation[k] != product.get(k) for k in ["form", "grade", "intended_use"]
        ):
            reason = "Product form, grade or use differs."
        elif date.fromisoformat(observation["as_of"]) > as_of:
            reason = "Observation is from a future date."
        elif (
            observation["valid_until"]
            and date.fromisoformat(observation["valid_until"]) < as_of
        ):
            reason = "Observation has expired."
        elif observation["unit"] != unit and not {observation["unit"], unit} <= set(
            mass
        ):
            reason = "Unit conversion is unsupported."
        else:
            factor = (
                mass[unit] / mass[observation["unit"]]
                if observation["unit"] != unit
                else Decimal(1)
            )
            if quantity * factor < number(observation["minimum_quantity"]):
                reason = "Order quantity does not meet the quoted MOQ."
            else:
                try:
                    value = (
                        convert(observation["price"], parent["reporting_currency"], fx)
                        * factor
                    )
                except DomainError as error:
                    reason = "Currency conversion is unavailable: " + error.code
                else:
                    accepted.append((observation["id"], value))
                    seen.add(source)
                    owners_seen.update(owners)
        if reason:
            rejected.append({"id": observation["id"], "reason": reason})
    result.update(
        rejected_comparators=rejected, comparator_ids=[r[0] for r in accepted]
    )
    if accepted:
        low = min(r[1] for r in accepted)
        high = max(r[1] for r in accepted)
        floor = (
            number(result["seller_floor"])
            if result["seller_floor"] is not None
            else None
        )
        result.update(
            market_low=output(low),
            market_high=output(high),
            recommended_low=output(max(low, floor))
            if floor is not None and floor <= high
            else None,
            recommended_high=output(high)
            if floor is not None and floor <= high
            else None,
            label="quote_supported",
        )
        if floor is not None and floor > high:
            result["assumptions"] += [
                "Seller floor exceeds observed comparable market prices; no feasible recommendation is asserted."
            ]
    return result
