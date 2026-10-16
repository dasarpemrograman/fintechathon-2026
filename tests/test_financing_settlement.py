from copy import deepcopy
from datetime import datetime, timedelta
import unittest
import test_demo_goldens as goldens
from packages.domain.economics import compute
from services.api.store import DomainError


def event(kind, amount, day, sequence=0):
    at = datetime.fromisoformat("2026-10-16T12:00:00+00:00") + timedelta(days=day)
    return {
        "kind": kind,
        "amount": {"amount": amount, "currency": "IDR"},
        "schedule": {
            "kind": "fixed",
            "due": {"instant": at.isoformat(), "timezone": "UTC"},
        },
        "status": "proposed",
        "evidence_ids": ["proof"],
        "sequence": sequence,
    }


class FinancingSettlementTests(unittest.TestCase):
    def setUp(self):
        self.parent, self.costs, self.obligations = goldens.DemoGoldenTests().fixture(
            "id-reseller"
        )

    def calculate(self, option, obligations=None):
        return compute(
            self.parent,
            self.costs,
            obligations or self.obligations,
            [],
            [],
            [],
            [option],
        )

    def loan(self):
        return {
            "id": "loan",
            "schedule": [
                event("loan_draw", "60000000", 13),
                event("withheld_fee", "1000000", 13),
                event("interest", "1200000", 54, 1),
                event("principal_repayment", "60000000", 54, 2),
            ],
        }

    def test_net_loan_preserves_goldens_and_late_buyer_misses_fixed_maturity(self):
        option = self.loan()
        result = self.calculate(option)
        self.assertEqual(result["cash_metrics"]["minimum_cash"], "7000000.00")
        self.assertEqual(result["cash_metrics"]["final_cash"], "73800000.00")
        self.assertEqual(
            result["after_financing"]["contribution"]["amount"], "23800000.00"
        )
        self.assertTrue(
            any(
                row["amount"]["amount"] == "59000000.00"
                for row in result["cash_metrics"]["event_balances"]
            )
        )
        late = deepcopy(option)
        for item in late["schedule"][:2]:
            item["schedule"] = event("loan_draw", "0", 15)["schedule"]
        self.assertEqual(
            self.calculate(late)["cash_metrics"]["minimum_cash"], "-46000000.00"
        )
        obligations = deepcopy(self.obligations)
        obligation = next(
            row for row in obligations if row["amount"]["amount"] == "128000000"
        )
        obligation["schedule"] = event("loan_draw", "0", 84)["schedule"]
        self.assertEqual(
            self.calculate(option, obligations)["cash_metrics"]["minimum_cash"],
            "-54200000.00",
        )

    def factoring(self):
        row = next(
            row for row in self.obligations if row["amount"]["amount"] == "128000000"
        )
        return {
            "id": "factor",
            "schedule": [
                event("loan_draw", "100000000", 13),
                event("withheld_fee", "2000000", 13),
            ],
            "receivable_assignments": [
                {
                    "obligation_id": row["id"],
                    "amount": {"amount": "128000000", "currency": "IDR"},
                    "reserve_amount": {"amount": "28000000", "currency": "IDR"},
                    "reserve_delay_days": 2,
                    "evidence_ids": ["proof"],
                }
            ],
        }

    def test_assigned_invoice_is_not_received_twice_and_reserve_follows_buyer(self):
        option = self.factoring()
        result = self.calculate(option)
        self.assertEqual(result["cash_metrics"]["final_cash"], "74000000.00")
        self.assertEqual(
            result["after_financing"]["contribution"]["amount"], "24000000.00"
        )
        timeline = result["cash_metrics"]["event_balances"]
        self.assertFalse(
            any(
                row["amount"]["amount"] == "128000000.00" and row["direction"] == "in"
                for row in timeline
            )
        )
        reserve = next(
            row for row in timeline if row["amount"]["amount"] == "28000000.00"
        )
        obligations = deepcopy(self.obligations)
        next(
            row
            for row in obligations
            if row["id"] == option["receivable_assignments"][0]["obligation_id"]
        )["schedule"] = event("loan_draw", "0", 84)["schedule"]
        late = self.calculate(option, obligations)
        late_reserve = next(
            row
            for row in late["cash_metrics"]["event_balances"]
            if row["amount"]["amount"] == "28000000.00"
        )
        self.assertEqual(
            (
                datetime.fromisoformat(late_reserve["at"])
                - datetime.fromisoformat(reserve["at"])
            ).days,
            30,
        )

    def test_partial_assignment_preserves_unassigned_buyer_receipt(self):
        option = self.factoring()
        assignment = option["receivable_assignments"][0]
        assignment["amount"]["amount"] = "120000000"
        assignment["reserve_amount"]["amount"] = "20000000"
        result = self.calculate(option)
        self.assertTrue(
            any(
                row["amount"]["amount"] == "8000000.00" and row["direction"] == "in"
                for row in result["cash_metrics"]["event_balances"]
            )
        )
        self.assertEqual(result["cash_metrics"]["final_cash"], "74000000.00")

    def test_assignment_and_fee_integrity_errors_do_not_become_zero_cost(self):
        option = self.factoring()
        option["receivable_assignments"][0]["reserve_amount"]["amount"] = "1"
        with self.assertRaises(DomainError) as error:
            self.calculate(option)
        self.assertEqual(error.exception.code, "ASSIGNMENT_SETTLEMENT_MISMATCH")
        option = self.loan()
        option["schedule"][1]["amount"]["amount"] = "60000001"
        with self.assertRaises(DomainError) as error:
            self.calculate(option)
        self.assertEqual(error.exception.code, "WITHHELD_FEE_AMOUNT")
        option = self.factoring()
        option["schedule"].append(event("principal_repayment", "100000000", 54))
        with self.assertRaises(DomainError) as error:
            self.calculate(option)
        self.assertEqual(error.exception.code, "ASSIGNMENT_DOUBLE_REPAYMENT")

    def test_executed_fx_retains_actual_values_and_native_outstanding(self):
        from packages.domain.economics import cost_amount

        locked = {
            "id": "executed",
            "base_currency": "USD",
            "quote_currency": "IDR",
            "rate": "15000",
        }
        latest = {
            "id": "reference",
            "base_currency": "USD",
            "quote_currency": "IDR",
            "rate": "16000",
        }
        line = deepcopy(self.costs[0])
        line["actual_amount"] = {"amount": "350", "currency": "USD"}
        line["actual_fx_observation_id"] = "executed"
        self.assertEqual(cost_amount(line, "IDR", [locked, latest]), 5250000)
        latest["rate"] = "17000"
        self.assertEqual(cost_amount(line, "IDR", [locked, latest]), 5250000)
        line.pop("actual_fx_observation_id")
        self.assertIsNone(cost_amount(line, "IDR", [locked, latest]))
        latest["rate"] = "16000"
        obligation = next(
            row for row in self.obligations if row["amount"]["amount"] == "128000000"
        )
        obligation["amount"] = {"amount": "8000", "currency": "USD"}
        receipt = {
            "id": "settled",
            "status": "verified",
            "supersedes": None,
            "settled_at": "2026-12-09T12:00:00Z",
            "value_date": "2026-12-09",
            "fx_observation_id": "executed",
            "allocations": [
                {
                    "obligation_id": obligation["id"],
                    "amount": {"amount": "4000", "currency": "USD"},
                }
            ],
        }
        result = compute(
            self.parent,
            self.costs,
            self.obligations,
            [],
            [locked, latest],
            [],
            receipts=[receipt],
        )
        self.assertEqual(result["cash_metrics"]["final_cash"], "72000000.00")
        self.assertEqual(
            result["before_financing"]["contribution"]["amount"], "22000000.00"
        )
        self.assertTrue(
            any(
                row["source_ref"]["id"] == obligation["id"]
                and row["amount"]["amount"] == "64000000.00"
                for row in result["cash_metrics"]["event_balances"]
            )
        )
