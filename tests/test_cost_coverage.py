from copy import deepcopy
import unittest
from packages.domain.cost_coverage import covered


class CashCostCoverageTests(unittest.TestCase):
    def setUp(self):
        self.parent = {
            "parties": [{"id": "seller", "roles": ["seller"]}],
            "invoices": [],
        }
        self.obligations = [
            {
                "id": key,
                "payer_party_id": "seller",
                "amount": {"amount": "100", "currency": "USD"},
            }
            for key in ["x", "y"]
        ]

    def cost(self, key, amount, targets):
        return {
            "id": key,
            "payer_party_id": "seller",
            "estimate": {"base": {"amount": amount, "currency": "USD"}},
            "actual_amount": None,
            "payment_term_ids": targets,
            "cash_treatment": "scheduled",
        }

    def test_shared_liability_is_allocated_once_and_flexible_costs_can_move(self):
        costs = [self.cost("a", "100", ["x", "y"]), self.cost("b", "100", ["x"])]
        self.assertTrue(covered(self.parent, costs, self.obligations, []))
        costs = [self.cost("a", "150", ["x"]), self.cost("b", "50", ["x", "y"])]
        self.assertFalse(covered(self.parent, costs, self.obligations, []))

    def test_actual_charge_increase_needs_a_corresponding_liability(self):
        cost = self.cost("a", "100", ["x"])
        self.assertTrue(covered(self.parent, [cost], self.obligations, []))
        cost["actual_amount"] = {"amount": "100.004", "currency": "USD"}
        self.assertFalse(covered(self.parent, [cost], self.obligations, []))
        cost["cash_treatment"] = "paid_before_snapshot"
        self.assertTrue(covered(self.parent, [cost], self.obligations, []))

    def test_unknown_cost_is_blocked_and_reference_fx_cannot_change_native_capacity(
        self,
    ):
        cost = self.cost("a", "100", ["x"])
        cost["estimate"]["base"] = None
        self.assertFalse(covered(self.parent, [cost], self.obligations, []))
        cost["estimate"]["base"] = {"amount": "100", "currency": "EUR"}
        self.assertFalse(
            covered(
                self.parent,
                [cost],
                self.obligations,
                [{"base_currency": "EUR", "quote_currency": "USD", "rate": "1"}],
            )
        )
