"""Reference FX valuations never assert executed native-currency resources."""

from decimal import Decimal
from packages.domain.economics import number
from packages.domain.settlement import collectible_amount


def native_resources_supported(parent, obligations, receipts):
    snapshot = parent["constraints"]["cash_snapshot"]
    if not snapshot:
        return False
    primary = snapshot["available"]["currency"]
    sellers = {party["id"] for party in parent["parties"] if "seller" in party["roles"]}
    superseded = {row["supersedes"] for row in receipts if row.get("supersedes")}
    for obligation in obligations:
        if obligation["payer_party_id"] not in sellers or obligation.get("status") in {
            "settled",
            "written_off",
        }:
            continue
        amount = obligation.get("amount")
        if amount is None:
            return False
        paid = sum(
            (
                number(allocation["amount"]["amount"])
                for receipt in receipts
                if receipt["status"] == "verified" and receipt["id"] not in superseded
                for allocation in receipt["allocations"]
                if allocation["obligation_id"] == obligation["id"]
                and allocation["amount"]["currency"] == amount["currency"]
            ),
            Decimal(0),
        )
        if collectible_amount(obligation) > paid and amount["currency"] != primary:
            return False
    return True
