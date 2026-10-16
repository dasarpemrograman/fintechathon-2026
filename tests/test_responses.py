"""Response outcome constraints, separate from future runtime behavior."""

from copy import deepcopy
from pathlib import Path
import sys
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
from validate_contract import check, instance_validator, load_contract, schema_validator


class ResponseTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.document = load_contract()

    def test_operation_outcomes(self):
        schemas = self.document["components"]["schemas"]
        for item in self.document["paths"].values():
            for method, operation in item.items():
                for code, response in operation["responses"].items():
                    if not code.startswith("2"):
                        continue
                    if "application/json" not in response["content"]:
                        self.assertEqual(method, "get")
                        continue
                    name = response["content"]["application/json"]["schema"][
                        "$ref"
                    ].rsplit("/", 1)[-1]
                    if name == "PendingReceiptResponse":
                        name = "ReceiptResponse"
                    status = schemas[name]["properties"]["status"]
                    expected = "accepted" if code == "202" else "completed"
                    with self.subTest(operation=operation["operationId"], code=code):
                        if "const" in status:
                            self.assertEqual(expected, status["const"])
                        else:
                            self.assertNotIn("accepted", status["enum"])

    def test_accepted_constraints_reject_completed(self):
        for name in ["JobResponse", "ScenarioJobResponse", "IngestionResponse"]:
            schema = self.document["components"]["schemas"][name]["properties"][
                "status"
            ]
            from jsonschema import Draft202012Validator

            validator = Draft202012Validator(schema)
            self.assertTrue(validator.is_valid("accepted"))
            self.assertFalse(validator.is_valid("completed"))

    def readiness(self):
        return {
            "request_id": "request_1",
            "workspace_id": "workspace_1",
            "revision": 1,
            "status": "blocked",
            "output_refs": [],
            "warnings": [],
            "blockers": [
                {
                    "code": "FUNDS_UNVERIFIED",
                    "field_path": None,
                    "reason": "Buyer funds not verified",
                    "required_action": "Review settlement evidence",
                    "evidence_refs": [],
                }
            ],
            "result": {
                "gate_id": "gate_1",
                "stage": "shipment",
                "evaluated_revision": 1,
                "status": "blocked",
                "conditions": [
                    {
                        "code": "FUNDS_UNVERIFIED",
                        "status": "unresolved",
                        "reason": "Awaiting evidence",
                        "required_action": "Review evidence",
                        "evidence_refs": [],
                    }
                ],
                "evidence_refs": [],
                "evaluated_at": "2026-10-16T10:00:00Z",
            },
        }

    def test_blocked_readiness_consistency(self):
        payload = self.readiness()
        validator = schema_validator(self.document, "ReadinessResponse")
        validator.validate(payload)
        self.assertFalse(validator.is_valid({**payload, "status": "completed"}))
        self.assertFalse(validator.is_valid({**payload, "blockers": []}))
        contradictory = deepcopy(payload)
        contradictory["result"]["status"] = "ready_for_next_action"
        self.assertFalse(validator.is_valid(contradictory))
        ready = deepcopy(payload)
        ready.update(status="completed", blockers=[])
        ready["result"]["status"] = "ready_for_next_action"
        ready["result"]["conditions"][0].update(
            status="satisfied", required_action=None
        )
        validator.validate(ready)

    def test_closure_conditional_uses_nested_gate(self):
        # Exercise the actual conditional independently of unrelated Deal payload fields.
        from jsonschema import Draft202012Validator

        schema = {
            "allOf": self.document["components"]["schemas"]["ClosureResponse"]["allOf"]
        }
        validator = Draft202012Validator(schema)
        payload = {
            "status": "blocked",
            "result": {"gate": {"status": "blocked"}},
            "blockers": [{}],
        }
        validator.validate(payload)
        self.assertFalse(validator.is_valid({**payload, "status": "completed"}))

    def test_partial_analysis_consistency(self):
        from jsonschema import Draft202012Validator

        schema = {
            "allOf": self.document["components"]["schemas"]["AnalysisResponse"]["allOf"]
        }
        validator = Draft202012Validator(schema)
        payload = {"status": "partial", "result": {"completeness": "partial"}}
        validator.validate(payload)
        self.assertFalse(validator.is_valid({**payload, "status": "completed"}))
        self.assertFalse(
            validator.is_valid(
                {"status": "partial", "result": {"completeness": "scoped_complete"}}
            )
        )

    def example_response(self, path, method, status, name):
        media = self.document["paths"][path][method]["responses"][status]["content"][
            "application/json"
        ]
        return media["schema"], deepcopy(media["examples"][name]["value"])

    def test_canonical_accepted_job_and_queued_run_read(self):
        schema, value = self.example_response(
            "/v2/workspaces/{id}/discovery-runs", "post", "202", "acceptedDiscovery"
        )
        validator = instance_validator(self.document, schema)
        validator.validate(value)
        self.assertFalse(validator.is_valid({**value, "status": "completed"}))
        read = {**value, "status": "completed", "result": value["result"]["run"]}
        schema_validator(self.document, "RunResponse").validate(read)
        read["result"]["status"] = "partial"
        self.assertFalse(schema_validator(self.document, "RunResponse").is_valid(read))
        read["status"] = "partial"
        schema_validator(self.document, "RunResponse").validate(read)

    def test_canonical_partial_analysis_and_nested_amount(self):
        schema, value = self.example_response(
            "/v2/deals/{id}/analyses/{resource_id}", "get", "200", "partialAnalysis"
        )
        validator = instance_validator(self.document, schema)
        validator.validate(value)
        self.assertFalse(validator.is_valid({**value, "status": "completed"}))
        invalid = deepcopy(value)
        invalid["result"]["cash_metrics"]["minimum_cash"] = -500.0
        self.assertFalse(validator.is_valid(invalid))
        document = deepcopy(self.document)
        media = document["paths"]["/v2/deals/{id}/analyses/{resource_id}"]["get"][
            "responses"
        ]["200"]["content"]["application/json"]
        media["examples"]["partialAnalysis"]["value"] = invalid
        with self.assertRaisesRegex(
            ValueError, "response 200.*example partialAnalysis"
        ):
            check(document)

    def test_canonical_pending_receipt_cannot_have_verifier_or_be_verified(self):
        schema, value = self.example_response(
            "/v2/deals/{id}/receipts", "post", "201", "pendingReceipt"
        )
        validator = instance_validator(self.document, schema)
        validator.validate(value)
        invalid = deepcopy(value)
        invalid["result"]["verified_by"] = "user_example"
        self.assertFalse(validator.is_valid(invalid))
        invalid["result"]["status"] = "verified"
        self.assertFalse(validator.is_valid(invalid))
        invalid["result"]["verified_by"] = None
        self.assertFalse(
            schema_validator(self.document, "ReceiptResponse").is_valid(invalid)
        )
        invalid = deepcopy(value)
        invalid["result"]["received_amount"]["amount"] = 1250.0
        self.assertFalse(validator.is_valid(invalid))

    def test_canonical_blocked_readiness_rejects_completed_envelope(self):
        schema, value = self.example_response(
            "/v2/deals/{id}/readiness", "get", "200", "blockedShipment"
        )
        validator = instance_validator(self.document, schema)
        validator.validate(value)
        self.assertFalse(validator.is_valid({**value, "status": "completed"}))
        invalid = deepcopy(value)
        invalid["result"]["conditions"][0]["status"] = "satisfied"
        self.assertFalse(validator.is_valid(invalid))

    def test_complete_closure_operation_payload(self):
        schema, value = self.example_response(
            "/v2/deals/{id}/close", "post", "200", "closedDeal"
        )
        validator = instance_validator(self.document, schema)
        validator.validate(value)
        invalid = deepcopy(value)
        del invalid["result"]["deal"]["snapshot_hash"]
        self.assertFalse(validator.is_valid(invalid))
        invalid = deepcopy(value)
        invalid["result"]["gate"]["status"] = "blocked"
        invalid["result"]["gate"]["conditions"][0]["status"] = "unresolved"
        self.assertFalse(validator.is_valid(invalid))
        invalid["status"] = "blocked"
        self.assertFalse(validator.is_valid(invalid))
        invalid["blockers"] = self.readiness()["blockers"]
        validator.validate(invalid)

    def test_canonical_response_examples_are_all_visited(self):
        counts = check(self.document)
        self.assertEqual(
            counts.operations,
            sum(len(item) for item in self.document["paths"].values()),
        )
        self.assertGreaterEqual(counts.request_examples, 5)
        self.assertGreaterEqual(counts.response_examples, 6)


if __name__ == "__main__":
    unittest.main()
