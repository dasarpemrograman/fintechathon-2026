from copy import deepcopy
from datetime import datetime, timezone
from decimal import Decimal
import unittest
from packages.domain.demo import financial_case, MANIFEST
from services.api.commands import procurement_costs
from packages.domain.economics import compute


class DemoGoldenTests(unittest.TestCase):
    def fixture(self, key):
        case = next(c for c in MANIFEST["cases"] if c["key"] == key)
        deal, components, seller, ops = financial_case(
            case, datetime(2026, 10, 16, tzinfo=timezone.utc), "source"
        )
        deal.update(
            id="fixture",
            reporting_currency=case["currency"],
            business_profile=case["profile"],
        )
        costs = procurement_costs({"tenant": "test", "actor": "test"}, deal)
        for category, amount in components:
            if category in {"procurement", "materials", "labor", "process", "overhead"}:
                continue
            costs.append(
                {
                    "id": category,
                    "component_key": category,
                    "covered_components": [category],
                    "allocations": [],
                    "actual_amount": None,
                    "estimate": {
                        "base": {"amount": amount, "currency": case["currency"]}
                    },
                    "economic_bearer_party_id": seller,
                    "treatment": "expense",
                    "payment_term_ids": [
                        t["id"] for t in deal["payment_terms"] if t["payee_id"] == ops
                    ],
                    "cash_treatment": "scheduled",
                }
            )
        obligations = [
            {
                "id": t["id"],
                "payer_party_id": t["payer_id"],
                "payee_party_id": t["payee_id"],
                "amount": t["amount"],
                "schedule": t["schedule"],
                "sequence": t["sequence"],
            }
            for t in deal["payment_terms"]
        ]
        return deal, costs, obligations

    def test_producer_and_reseller_full_engine_goldens(self):
        for key, contribution, minimum, shortfall, final in [
            (
                "id-reseller",
                "26000000.00",
                "-52000000.00",
                "57000000.00",
                "76000000.00",
            ),
            ("cn-producer", "17000.00", "-16000.00", "19000.00", "40000.00"),
        ]:
            deal, costs, obligations = self.fixture(key)
            result = compute(deal, costs, obligations, [], [], [])
            with self.subTest(case=key):
                self.assertEqual(
                    result["completeness"], "scoped_complete", result["blockers"]
                )
                self.assertEqual(
                    result["before_financing"]["contribution"]["amount"], contribution
                )
                self.assertEqual(result["cash_metrics"]["minimum_cash"], minimum)
                self.assertEqual(result["cash_metrics"]["buffer_shortfall"], shortfall)
                self.assertEqual(result["cash_metrics"]["final_cash"], final)

    def test_fx_and_freight_shock_affect_all_unlocked_exposures(self):
        deal, costs, obligations = self.fixture("id-reseller")
        deal["invoices"][0]["amount"] = {"amount": "10000", "currency": "USD"}
        for obligation in obligations:
            if obligation["payee_party_id"] == deal["parties"][0]["id"]:
                obligation["amount"] = {
                    "amount": format(
                        Decimal(obligation["amount"]["amount"]) / 16000, "f"
                    ),
                    "currency": "USD",
                }
            elif obligation["amount"]["amount"] == "16000000":
                obligation["amount"] = {"amount": "1000", "currency": "USD"}
        freight = next(c for c in costs if c["component_key"] == "main_freight")
        freight["estimate"]["base"] = {"amount": "1000", "currency": "USD"}
        fx = [
            {
                "id": "rate",
                "base_currency": "USD",
                "quote_currency": "IDR",
                "rate": "15000",
            }
        ]
        result = compute(deal, costs, obligations, [], fx, [])
        self.assertEqual(
            result["before_financing"]["contribution"]["amount"], "17000000.00"
        )
        self.assertEqual(result["cash_metrics"]["minimum_cash"], "-53000000.00")
        deal, costs, obligations = self.fixture("id-reseller")
        next(c for c in costs if c["component_key"] == "main_freight")["estimate"][
            "base"
        ]["amount"] = "19200000"
        next(o for o in obligations if o["amount"]["amount"] == "16000000")["amount"][
            "amount"
        ] = "19200000"
        result = compute(deal, costs, obligations, [], [], [])
        self.assertEqual(
            result["before_financing"]["contribution"]["amount"], "22800000.00"
        )
        self.assertEqual(result["cash_metrics"]["minimum_cash"], "-55200000.00")

    def test_prior_paid_economic_overhead_has_no_new_cash_event(self):
        deal, costs, obligations = self.fixture("cn-producer")
        overhead = next(
            c for c in costs if c["component_key"].startswith("production-overhead")
        )
        self.assertEqual(overhead["cash_treatment"], "paid_before_snapshot")
        self.assertEqual(overhead["payment_term_ids"], [])
        self.assertEqual(
            sum(
                Decimal(o["amount"]["amount"])
                for o in obligations
                if o["payer_party_id"] == deal["parties"][0]["id"]
            ),
            Decimal(50000),
        )

    def test_unknown_required_cost_timing_is_partial(self):
        deal, costs, obligations = self.fixture("id-reseller")
        costs[0]["payment_term_ids"] = []
        costs[0]["cash_treatment"] = "unknown"
        result = compute(deal, costs, obligations, [], [], [])
        self.assertEqual(result["completeness"], "partial")
        self.assertEqual(
            result["cash_metrics"]["calculation_scope"], "known_items_only"
        )

    def test_pre_snapshot_verified_payments_are_not_added_to_opening_cash_again(self):
        deal, costs, obligations = self.fixture("id-reseller")
        deal["constraints"]["cash_snapshot"]["as_of"] = "2026-10-17T00:00:00Z"
        deal["constraints"]["cash_snapshot"]["available"]["amount"] = "32000000"
        receipts = []
        for obligation in obligations:
            if obligation["schedule"]["due"]["instant"].startswith("2026-10-16"):
                receipts.append(
                    {
                        "id": "proof_" + obligation["id"],
                        "status": "verified",
                        "supersedes": None,
                        "settled_at": obligation["schedule"]["due"]["instant"],
                        "value_date": "2026-10-16",
                        "allocations": [
                            {
                                "obligation_id": obligation["id"],
                                "amount": obligation["amount"],
                            }
                        ],
                    }
                )
        result = compute(deal, costs, obligations, [], [], [], receipts=receipts)
        self.assertEqual(result["cash_metrics"]["minimum_cash"], "-52000000.00")
        self.assertEqual(result["cash_metrics"]["final_cash"], "76000000.00")
        self.assertTrue(
            all(
                p["at"] >= "2026-10-17"
                for p in result["cash_metrics"]["event_balances"]
            )
        )

    def test_producer_yield_and_capacity_cover_finished_output(self):
        from services.api.commands import validate_deal
        from services.api.store import DomainError

        parent, _, _ = self.fixture("cn-producer")
        parent["procurement"]["usable_yield"] = "0.5"
        with self.assertRaises(DomainError) as caught:
            validate_deal(parent)
        self.assertEqual(caught.exception.code, "PRODUCTION_OUTPUT_SHORTFALL")
        parent["procurement"]["batch_quantity"] = "20"
        with self.assertRaises(DomainError) as caught:
            validate_deal(parent)
        self.assertEqual(caught.exception.code, "CAPACITY_EXCEEDED")
        parent["procurement"]["capacity_quantity"] = "20"
        validate_deal(parent)
