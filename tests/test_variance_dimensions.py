from copy import deepcopy
import unittest
from packages.domain.variance import dimensions


class VarianceDimensionTests(unittest.TestCase):
    def test_allocated_or_multiple_invoices_do_not_invent_per_unit_prices(self):
        parent = {
            "line_items": [{"id": "coffee", "quantity": "10", "unit": "kg"}],
            "invoices": [
                {
                    "id": "buyer",
                    "side": "buyer",
                    "amount": {"amount": "160", "currency": "USD"},
                    "allocations": [],
                    "evidence_ids": [],
                }
            ],
            "payment_terms": [],
        }

        def compare(value):
            return [
                row
                for row in dimensions(value, value, [], [], [], [], None)
                if row["category"] == "unit_price"
            ]

        self.assertEqual(compare(parent)[0]["baseline_value"], "16.00")
        multiple = deepcopy(parent)
        multiple["invoices"].append(
            {**deepcopy(multiple["invoices"][0]), "id": "second-buyer"}
        )
        self.assertTrue(all(row["baseline_value"] is None for row in compare(multiple)))
        allocated = deepcopy(parent)
        allocated["invoices"][0]["allocations"] = [
            {"line_item_id": "coffee", "shipment_id": None, "fraction": "1"}
        ]
        self.assertIsNone(compare(allocated)[0]["actual_value"])
        supplier = deepcopy(parent)
        supplier["invoices"][0]["side"] = "production_input"
        self.assertEqual(compare(supplier), [])
