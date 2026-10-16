from copy import deepcopy
from datetime import date
import unittest
import test_demo_goldens as goldens
from packages.domain.economics import compute
from packages.domain.pricing import normalized_range


class PricingTreatmentTests(unittest.TestCase):
    def fixture(self):
        return goldens.DemoGoldenTests().fixture("id-reseller")

    def observation(self, parent):
        p = parent["line_items"][0]["product"]
        return {
            "id": "market",
            "price": {"amount": "15000000", "currency": "IDR"},
            "unit": "kg",
            "destination_country": "SG",
            "product_description": p["description"],
            "form": p.get("form"),
            "grade": p.get("grade"),
            "intended_use": p.get("intended_use"),
            "minimum_quantity": "10",
            "segment": "wholesale",
            "as_of": "2026-10-16",
            "valid_until": "2026-10-20",
            "evidence_ids": ["source_a"],
            "review_status": "confirmed",
        }

    def test_unknown_buyer_charge_does_not_erase_known_seller_expense(self):
        parent, costs, obligations = self.fixture()
        unknown = deepcopy(costs[0])
        unknown.update(
            id="buyer_tax",
            component_key="buyer_tax",
            covered_components=["buyer_tax"],
            economic_bearer_party_id=parent["parties"][1]["id"],
            rate=None,
            estimate={"base": None},
            actual_amount=None,
        )
        result = compute(parent, costs + [unknown], obligations, [], [], [])
        self.assertEqual(
            result["cost_totals"]["seller_operating_expense"], "134000000.00"
        )
        self.assertEqual(
            result["before_financing"]["contribution"]["amount"], "26000000.00"
        )
        self.assertIsNone(result["cost_totals"]["buyer_total"])
        self.assertEqual(result["completeness"], "partial")

    def test_reimbursement_is_not_revenue_and_is_not_twice_buyer_total(self):
        parent, costs, obligations = self.fixture()
        parent["invoices"][0]["reimbursable_amount"] = {
            "amount": "5000000",
            "currency": "IDR",
        }
        advance = deepcopy(costs[0])
        advance.update(
            id="advance",
            component_key="advance",
            covered_components=["advance"],
            rate=None,
            estimate={"base": {"amount": "5000000", "currency": "IDR"}},
            economic_bearer_party_id=parent["parties"][1]["id"],
            treatment="reimbursable_advance",
        )
        result = compute(parent, costs + [advance], obligations, [], [], [])
        self.assertEqual(
            result["before_financing"]["contribution"]["amount"], "21000000.00"
        )
        self.assertEqual(result["cost_totals"]["buyer_total"], "160000000.00")

    def test_floor_accounts_for_percentage_sales_cost(self):
        parent, costs, obligations = self.fixture()
        parent["constraints"]["target_contribution_margin"] = "0.2"
        fee = deepcopy(costs[0])
        fee.update(
            id="salesfee",
            component_key="salesfee",
            covered_components=["salesfee"],
            basis="percentage",
            percentage_rate="0.1",
            rate=None,
            estimate={"base": None},
        )
        result = compute(parent, costs + [fee], obligations, [], [], [])
        self.assertEqual(result["price_range"]["seller_floor"], "191428571.43")

    def test_comparator_exclusions_normalization_and_floor_market_conflict(self):
        parent, costs, obligations = self.fixture()
        parent["constraints"]["target_contribution_margin"] = "0.2"
        result = compute(parent, costs, obligations, [], [], [])
        observation = self.observation(parent)
        inputs = [
            observation,
            {**deepcopy(observation), "id": "retail", "segment": "retail"},
            {**deepcopy(observation), "id": "moq", "minimum_quantity": "100"},
            {**deepcopy(observation), "id": "ppp", "segment": "ppp"},
        ]
        price = normalized_range(
            parent, result["price_range"], inputs, [], date(2026, 10, 16)
        )
        self.assertEqual(price["seller_floor"], "16750000.00")
        self.assertEqual(price["market_high"], "15000000.00")
        self.assertIsNone(price["recommended_high"])
        self.assertEqual(len(price["rejected_comparators"]), 3)
        by_tonne = {
            **observation,
            "price": {"amount": "15000000000", "currency": "IDR"},
            "unit": "tonne",
            "minimum_quantity": "0.01",
        }
        price = normalized_range(
            parent, result["price_range"], [by_tonne], [], date(2026, 10, 16)
        )
        self.assertEqual(price["market_high"], "15000000.00")

    def test_typed_freight_input_reaches_cost_breakdown_and_total(self):
        parent, costs, obligations = self.fixture()
        freight = next(c for c in costs if c["component_key"] == "main_freight")
        freight.update(
            rate={"amount": "100", "currency": "USD"},
            minimum_charge={"amount": "350", "currency": "USD"},
            freight_input={
                "shipment_id": parent["shipments"][0]["id"],
                "mode": "sea_lcl",
                "packages": [
                    {
                        "count": 1,
                        "length_cm": "300",
                        "width_cm": "100",
                        "height_cm": "100",
                    }
                ],
                "gross_kg": "2000",
                "quoted_divisor": None,
                "containers": None,
            },
        )
        fx = [
            {
                "id": "fx",
                "base_currency": "USD",
                "quote_currency": "IDR",
                "rate": "16000",
            }
        ]
        result = compute(parent, costs, obligations, [], fx, [])
        line = next(
            b
            for b in result["cost_breakdown"]
            if b["cost_line_ref"]["id"] == freight["id"]
        )
        self.assertEqual(line["reporting_amount"]["amount"], "5600000.00")
        self.assertEqual(
            result["cost_totals"]["seller_operating_expense"], "123600000.00"
        )
