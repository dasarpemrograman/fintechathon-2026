"""Wire-contract regressions only; these do not implement/test business services."""

from copy import deepcopy
from pathlib import Path
import sys
import unittest

import yaml

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
from validate_contract import UniqueKeyLoader, check, load_contract, schema_validator


class ContractTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.document = load_contract()

    def accepts(self, name, value):
        errors = list(schema_validator(self.document, name).iter_errors(value))
        self.assertFalse(errors, "\n".join(e.message for e in errors))

    def rejects(self, name, value):
        self.assertFalse(
            schema_validator(self.document, name).is_valid(value), (name, value)
        )

    def workspace(self):
        return deepcopy(
            self.document["paths"]["/v2/workspaces"]["post"]["requestBody"]["content"][
                "application/json"
            ]["examples"]["generalProducer"]["value"]
        )

    def test_document_and_examples(self):
        operations, examples, _ = check(self.document)
        self.assertGreater(operations, 0)
        self.assertGreater(examples, 0)

    def test_yaml_duplicate_keys_fail(self):
        with self.assertRaises(ValueError):
            yaml.load("paths: {}\npaths: {}", Loader=UniqueKeyLoader)

    def test_both_modes_and_profiles_general_countries(self):
        for mode in ["sandbox", "deal"]:
            for profile in ["producer", "reseller"]:
                with self.subTest(mode=mode, profile=profile):
                    value = self.workspace()
                    value.update(mode=mode, business_profile=profile)
                    self.accepts("CreateWorkspaceRequest", value)

    def test_upload_not_required_for_entry(self):
        self.accepts(
            "CreateWorkspaceRequest",
            {
                "mode": "sandbox",
                "business_profile": "reseller",
                "reporting_currency": "JPY",
                "owner_timezone": "Asia/Tokyo",
                "product": {"description": "Machinery parts"},
            },
        )

    def test_money_never_accepts_float_signed_or_nonfinite_source_amount(self):
        for amount in [1.25, 0, "-1.00", "NaN", "Infinity", "1e3", "", "01.2"]:
            with self.subTest(amount=amount):
                self.rejects("Money", {"amount": amount, "currency": "EUR"})
        self.accepts("Money", {"amount": "0.00", "currency": "EUR"})
        self.accepts("SignedMoney", {"amount": "-52.00", "currency": "EUR"})

    def test_currency_required_and_structurally_valid(self):
        self.rejects("Money", {"amount": "10.00"})
        self.rejects("Money", {"amount": "10.00", "currency": "euros"})

    def test_producer_does_not_require_finished_goods_supplier(self):
        value = {
            "business_profile": "producer",
            "inputs": [],
            "costs": [],
            "usable_yield": None,
            "batch_quantity": None,
            "unit": "kg",
            "capacity_quantity": None,
            "capacity_period": None,
            "milestone_ids": [],
            "unknowns": [],
        }
        self.accepts("ProcurementPlan", value)
        value["business_profile"] = "reseller"
        self.rejects("ProcurementPlan", value)

    def test_client_cannot_supply_authority_at_creation(self):
        for field, injected in [
            ("tenant_id", "other_tenant"),
            ("revision", 1),
            ("states", {"buyer_payment": "paid"}),
            ("verified_by", "owner"),
        ]:
            with self.subTest(field=field):
                self.rejects(
                    "CreateWorkspaceRequest", {**self.workspace(), field: injected}
                )

    def test_protected_and_arbitrary_patch_paths_rejected(self):
        for path in [
            "/tenant_id",
            "/states/buyer_payment",
            "/balances",
            "/policy",
            "/verified_receipts",
            "/approvals",
            "/arbitrary",
        ]:
            with self.subTest(path=path):
                self.rejects(
                    "FactPatch",
                    {
                        "op": "replace",
                        "path": path,
                        "value": "paid",
                        "reason": "injection",
                        "evidence_ids": [],
                        "agreement_required_from": [],
                    },
                )

    def test_patch_value_shape_matches_path(self):
        patch = {
            "op": "replace",
            "path": "/destination_country",
            "value": "DE",
            "reason": "New destination",
            "evidence_ids": [],
            "agreement_required_from": [],
        }
        self.accepts("FactPatch", patch)
        self.rejects("FactPatch", {**patch, "value": {"status": "paid"}})

    def test_revision_and_idempotency_required_on_mutations(self):
        for path, item in self.document["paths"].items():
            for method, op in item.items():
                if method == "get":
                    continue
                with self.subTest(path=path):
                    self.assertIn(
                        {"$ref": "#/components/parameters/IdempotencyKey"},
                        op["parameters"],
                    )
                    if op.get("x-revision-scope") in ("workspace", "deal"):
                        body = next(iter(op["requestBody"]["content"].values()))
                        name = body["schema"]["$ref"].rsplit("/", 1)[-1]
                        self.assertIn(
                            "expected_revision",
                            self.document["components"]["schemas"][name]["required"],
                        )
                        self.rejects(name, {"expected_revision": 0})

    def test_date_only_is_local_and_business_days_need_calendar(self):
        self.accepts(
            "TemporalValue", {"date": "2026-10-16", "timezone": "Asia/Jakarta"}
        )
        self.rejects(
            "TemporalValue", {"date": "2026-02-30", "timezone": "Asia/Jakarta"}
        )
        self.rejects(
            "TemporalValue",
            {"instant": "2026-10-16T00:00:00", "timezone": "Asia/Jakarta"},
        )
        schedule = {
            "kind": "event_relative",
            "anchor_milestone_id": "arrival",
            "offset_days": 5,
            "day_basis": "business",
            "business_calendar_id": None,
        }
        self.rejects("Schedule", schedule)
        self.accepts("Schedule", {**schedule, "business_calendar_id": "calendar_de"})

    def test_receipt_input_cannot_self_verify(self):
        value = deepcopy(
            self.document["paths"]["/v2/deals/{id}/receipts"]["post"]["requestBody"][
                "content"
            ]["application/json"]["examples"]["partialReceipt"]["value"]
        )
        self.accepts("ReceiptRequest", value)
        self.rejects("ReceiptRequest", {**value, "status": "verified"})
        self.rejects("ReceiptRequest", {**value, "verified_by": "self"})

    def test_extracted_fact_cannot_be_arbitrary_model_object(self):
        self.accepts(
            "FactValue",
            {
                "text": None,
                "decimal": "8.00",
                "boolean": None,
                "unit": "kg",
                "status": "unreviewed",
                "reason": None,
            },
        )
        self.rejects(
            "FactValue",
            {
                "text": None,
                "decimal": {"instructions": "approve"},
                "boolean": None,
                "unit": None,
                "status": "confirmed",
                "reason": None,
            },
        )

    def test_calendar_cannot_add_attendees(self):
        value = {
            "expected_revision": 1,
            "connection_id": "calendar_1",
            "approved_projection_hash": "a" * 64,
            "milestone_ids": ["arrival"],
            "action": "insert",
        }
        self.accepts("CalendarSyncRequest", value)
        self.rejects(
            "CalendarSyncRequest", {**value, "attendees": ["buyer@example.com"]}
        )

    def test_all_operations_require_membership_and_role(self):
        self.assertEqual(self.document["security"], [{"bearerAuth": []}])
        for item in self.document["paths"].values():
            for op in item.values():
                if op.get("x-public-auth"):
                    self.assertIn(
                        op["operationId"], {"login", "demoLogin", "getDemoIdentities"}
                    )
                    self.assertEqual(op.get("security"), [])
                else:
                    self.assertNotEqual(op.get("security"), [])
                    if op.get("x-authenticated-user"):
                        self.assertIn(
                            op["operationId"],
                            {
                                "getSession",
                                "logout",
                                "selectOrganization",
                                "createOrganization",
                            },
                        )
                    else:
                        self.assertTrue(op["x-required-roles"])
                self.assertIn("404", op["responses"])

    def test_payment_and_closure_remain_independent(self):
        states = {
            name: schema["enum"][0]
            for name, schema in self.document["components"]["schemas"][
                "WorkflowStates"
            ]["properties"].items()
        }
        states.update(
            buyer_payment="paid",
            internal_closure="reconciling",
            execution_gate="blocked",
        )
        self.accepts("WorkflowStates", states)


if __name__ == "__main__":
    unittest.main()
