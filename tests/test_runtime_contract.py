from copy import deepcopy
from pathlib import Path
import sys
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
from validate_contract import load_contract, schema_validator


class RuntimeContractTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.document = load_contract()

    def test_explicit_auth_and_revision_boundaries(self):
        operations = {
            op["operationId"]: op
            for item in self.document["paths"].values()
            for op in item.values()
        }
        self.assertEqual(
            {k for k, v in operations.items() if v["x-public-auth"]},
            {"login", "demoLogin", "getDemoIdentities"},
        )
        for name in [
            "recordCostLine",
            "reviewGoods",
            "reviewRequirement",
            "reserveCash",
            "recordShipmentEvent",
        ]:
            self.assertEqual(operations[name]["x-revision-scope"], "deal")
        self.assertEqual(
            operations["reviewGoods"]["x-required-roles"],
            ["owner", "production_procurement"],
        )

    def test_review_and_financial_payloads_are_typed(self):
        for name in [
            "EvidenceIngestRequest",
            "FactReviewRequest",
            "CostLineRequest",
            "RequirementReviewRequest",
            "GoodsReviewRequest",
            "ActualChargeRequest",
            "ObligationRequest",
            "ReservationRequest",
        ]:
            schema = self.document["components"]["schemas"][name]
            self.assertFalse(schema["additionalProperties"])
            self.assertIn("expected_revision", schema["required"])
            self.assertFalse(
                schema_validator(self.document, name).is_valid(
                    {"expected_revision": 1, "override": True}
                )
            )

    def test_calendar_preview_excludes_attendee_payload(self):
        value = {
            "expected_revision": 1,
            "connection_id": "connection_1",
            "milestone_ids": ["arrival"],
            "action": "insert",
        }
        validator = schema_validator(self.document, "CalendarPreviewRequest")
        validator.validate(value)
        self.assertFalse(
            validator.is_valid({**value, "attendees": ["buyer@example.test"]})
        )

    def test_cost_actuals_require_nonempty_evidence(self):
        value = {
            "expected_revision": 1,
            "cost_line_id": "cost_1",
            "amount": {"amount": "10.00", "currency": "EUR"},
            "evidence_ids": ["source_1"],
            "reason": "Reviewed actual",
        }
        validator = schema_validator(self.document, "ActualChargeRequest")
        validator.validate(value)
        self.assertFalse(validator.is_valid({**value, "evidence_ids": []}))

    def test_invoice_patch_cannot_modify_authority(self):
        value = {
            "op": "replace",
            "path": "/invoices",
            "value": [],
            "reason": "Known invoices",
            "evidence_ids": [],
            "agreement_required_from": [],
        }
        validator = schema_validator(self.document, "FactPatch")
        validator.validate(value)
        self.assertFalse(
            validator.is_valid({**value, "path": "/execution_scope", "value": "demo"})
        )
