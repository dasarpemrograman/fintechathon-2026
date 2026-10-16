"""Supported explicit bank deductions and recovery of reviewed advances."""

from copy import deepcopy
from decimal import Decimal
from services.api import commands, store
from services.api.store import DomainError
from packages.domain.economics import number, convert


def adjust(conn, context, parent, obligation, adjustment, proof, remaining):
    tenant = context["tenant"]
    actor = context["actor"]
    dataset = parent["dataset_id"]
    amount = adjustment["amount"]
    sellers = {p["id"] for p in parent["parties"] if "seller" in p["roles"]}
    if obligation["payee_party_id"] not in sellers:
        raise DomainError(
            "ADJUSTMENT_DIRECTION",
            "Deducted bank fees and reimbursement claims apply to a buyer-to-seller obligation. Seller payment fees require their own actual charge and liability.",
        )
    ids = list(dict.fromkeys(adjustment["agreement_evidence_ids"] + proof))
    if not proof or any(
        store.get(conn, tenant, "evidence", i)["review_status"] != "confirmed"
        for i in ids
    ):
        raise DomainError(
            "ACTUAL_ADJUSTMENT_PROOF",
            "A financial adjustment needs confirmed agreement and actual supporting evidence.",
        )

    def save(kind, row):
        store.save(conn, tenant, kind, row, parent=parent["id"], dataset=dataset)

    if adjustment["kind"] == "fee":
        if (
            number(amount["amount"]) > remaining
            or obligation["status"] == "written_off"
        ):
            raise DomainError(
                "FEE_EXCEEDS_BALANCE",
                "An agreed bank deduction cannot exceed the remaining receivable or change a write-off.",
            )
        obligation.setdefault("settlement_deductions", []).append(deepcopy(adjustment))
        obligation["evidence_ids"] = list(
            dict.fromkeys(obligation["evidence_ids"] + ids)
        )
        save("obligation", obligation)
        row = {
            **store.meta(tenant, actor, "cost_line"),
            "component_key": "settlement-fee:" + store.uid("fee"),
            "category": "bank_fee",
            "location": "settlement",
            "payer_party_id": obligation["payer_party_id"],
            "economic_bearer_party_id": obligation["payee_party_id"],
            "basis": "fixed",
            "quantity": None,
            "unit": None,
            "rate": None,
            "minimum_charge": None,
            "calculation_rule_ref": None,
            "estimate": {"low": None, "base": None, "high": None},
            "evidence_ids": ids,
            "actual_evidence_ids": ids,
            "covered_components": [],
            "treatment": "expense",
            "allocations": deepcopy(obligation["allocations"]),
            "payment_term_ids": [obligation["id"]],
            "status": "user_assumed",
            "conditional": False,
            "valid_until": None,
            "actual_amount": deepcopy(amount),
            "unknowns": [],
            "cash_treatment": "deducted_from_settlement",
        }
        save("cost_line", row)
        parent["cost_line_ids"].append(row["id"])
    elif adjustment["kind"] == "reimbursement":
        cost = store.get(conn, tenant, "cost_line", adjustment["cost_line_id"])
        if (
            not any(
                row["id"] == cost["id"]
                for row in commands.children(conn, tenant, "cost_line", parent)
            )
            or cost["treatment"] != "reimbursable_advance"
            or not cost.get("actual_amount")
            or cost["actual_amount"]["currency"] != amount["currency"]
            or cost["payer_party_id"] not in sellers
        ):
            raise DomainError(
                "REIMBURSEMENT_ADVANCE",
                "Select this deal’s actual seller-paid reimbursable advance in the claim currency.",
            )
        costs = commands.children(conn, tenant, "cost_line", parent)
        fx = commands.children(conn, tenant, "fx_observation", parent)
        advances = sum(
            (
                convert(row["actual_amount"], amount["currency"], fx)
                for row in costs
                if row["treatment"] == "reimbursable_advance"
                and row.get("actual_amount")
            ),
            Decimal(0),
        )
        invoiced = sum(
            (
                convert(row["reimbursable_amount"], amount["currency"], fx)
                for row in parent["invoices"]
                if row.get("reimbursable_amount")
            ),
            Decimal(0),
        )
        claims = [
            row
            for row in commands.children(conn, tenant, "obligation", parent)
            if row.get("reimbursement_cost_line_id")
        ]
        claimed = sum(
            (convert(row["amount"], amount["currency"], fx) for row in claims),
            Decimal(0),
        )
        same = sum(
            (
                number(row["amount"]["amount"])
                for row in claims
                if row["reimbursement_cost_line_id"] == cost["id"]
            ),
            Decimal(0),
        )
        if (
            same + number(amount["amount"]) > number(cost["actual_amount"]["amount"])
            or claimed + invoiced + number(amount["amount"]) > advances
        ):
            raise DomainError(
                "REIMBURSEMENT_DUPLICATE",
                "Claims and invoice reimbursements cannot exceed reviewed advances or recover one outlay twice.",
            )
        row = {
            **store.meta(tenant, actor, "obligation"),
            "payer_party_id": obligation["payer_party_id"],
            "payee_party_id": obligation["payee_party_id"],
            "amount": deepcopy(amount),
            "schedule": deepcopy(obligation["schedule"]),
            "allocations": deepcopy(cost["allocations"]),
            "status": "open",
            "evidence_ids": ids,
            "unknowns": [],
            "reimbursement_cost_line_id": cost["id"],
        }
        save("obligation", row)
