import unittest
from packages.domain.cash_availability import native_resources_supported


class NativeCashTests(unittest.TestCase):
    def test_reference_valuation_does_not_cover_unsettled_foreign_currency(self):
        parent = {
            "constraints": {"cash_snapshot": {"available": {"currency": "IDR"}}},
            "parties": [{"id": "seller", "roles": ["seller"]}],
        }
        obligation = {
            "id": "freight",
            "payer_party_id": "seller",
            "status": "open",
            "amount": {"amount": "350", "currency": "USD"},
        }
        self.assertFalse(native_resources_supported(parent, [obligation], []))
        receipt = {
            "id": "proof",
            "status": "verified",
            "supersedes": None,
            "allocations": [
                {
                    "obligation_id": "freight",
                    "amount": {"amount": "350", "currency": "USD"},
                }
            ],
        }
        self.assertTrue(native_resources_supported(parent, [obligation], [receipt]))
        receipt["allocations"][0]["amount"]["amount"] = "349.999"
        self.assertFalse(native_resources_supported(parent, [obligation], [receipt]))
        obligation["status"] = "written_off"
        self.assertTrue(native_resources_supported(parent, [obligation], []))
