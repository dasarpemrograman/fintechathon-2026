"""Exercise the example traversal itself, using copies of the canonical document."""

from copy import deepcopy
from pathlib import Path
import subprocess
import sys
from tempfile import TemporaryDirectory
import unittest

import yaml

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
from validate_contract import check, load_contract


class ExampleValidationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.base = load_contract()

    def document(self):
        return deepcopy(self.base)

    def add_money_response(self, document):
        media = {
            "schema": {"$ref": "#/components/schemas/Money"},
            "examples": {
                "validMoney": {"value": {"amount": "10.00", "currency": "EUR"}}
            },
        }
        response = {
            "description": "Example traversal fixture",
            "content": {"application/json": media},
        }
        document["components"]["responses"]["TestMoney"] = response
        document["paths"]["/v2/entitlements"]["get"]["responses"]["200"] = {
            "$ref": "#/components/responses/TestMoney"
        }
        return media

    def test_inline_and_referenced_schema_response_and_example(self):
        document = self.document()
        media = self.add_money_response(document)
        document["components"].setdefault("examples", {})["Money"] = media["examples"][
            "validMoney"
        ]
        media["examples"]["validMoney"] = {"$ref": "#/components/examples/Money"}
        before = check(document)
        self.assertGreater(before.response_examples, 0)
        media["schema"] = {
            "type": "object",
            "required": ["amount"],
            "properties": {
                "amount": {"type": "string"},
                "currency": {"type": "string"},
            },
        }
        self.assertEqual(check(document), before)

    def test_local_request_body_and_singular_example(self):
        document = self.document()
        op = document["paths"]["/v2/workspaces"]["post"]
        body = op["requestBody"]
        media = body["content"]["application/json"]
        media["example"] = media["examples"].pop("minimalReseller")["value"]
        document["components"]["requestBodies"] = {"Entry": body}
        op["requestBody"] = {"$ref": "#/components/requestBodies/Entry"}
        self.assertEqual(
            check(document).request_examples, check(self.base).request_examples
        )

    def test_invalid_nested_money_has_operation_status_and_name(self):
        document = self.document()
        media = self.add_money_response(document)
        media["examples"]["validMoney"]["value"]["amount"] = 10.0
        with self.assertRaisesRegex(
            ValueError, r"GET /v2/entitlements .*response 200.*example validMoney"
        ):
            check(document)

    def test_external_and_missing_references_fail_locally(self):
        for target, message in [
            ("https://example.com/schema", "Only local"),
            ("#/components/schemas/Absent", "Unresolved local"),
        ]:
            document = self.document()
            self.add_money_response(document)["schema"] = {"$ref": target}
            with (
                self.subTest(target=target),
                self.assertRaisesRegex(ValueError, message),
            ):
                check(document)

    def test_cyclic_response_and_example_reference_chains(self):
        for kind in ["responses", "examples"]:
            document = self.document()
            document["components"].setdefault(kind, {}).update(
                {
                    "LoopA": {"$ref": f"#/components/{kind}/LoopB"},
                    "LoopB": {"$ref": f"#/components/{kind}/LoopA"},
                }
            )
            with (
                self.subTest(kind=kind),
                self.assertRaisesRegex(ValueError, "Cyclic reference chain"),
            ):
                check(document)

    def test_external_example_value_and_missing_value_are_rejected(self):
        for example, message in [
            ({"externalValue": "https://example.com/data"}, "External example"),
            ({"summary": "No value"}, "local value"),
        ]:
            document = self.document()
            self.add_money_response(document)["examples"]["validMoney"] = example
            with (
                self.subTest(example=example),
                self.assertRaisesRegex(ValueError, message),
            ):
                check(document)

    def test_invalid_example_cli_returns_nonzero(self):
        document = self.document()
        self.add_money_response(document)["examples"]["validMoney"]["value"][
            "amount"
        ] = 10
        with TemporaryDirectory() as directory:
            path = Path(directory) / "invalid.yaml"
            path.write_text(yaml.safe_dump(document))
            result = subprocess.run(
                [
                    sys.executable,
                    str(
                        Path(__file__).resolve().parents[1]
                        / "scripts/validate_contract.py"
                    ),
                    str(path),
                ],
                capture_output=True,
                text=True,
            )
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("response 200", result.stderr)
        self.assertIn("validMoney", result.stderr)
        self.assertNotIn("OpenAPI valid", result.stdout)

    def test_unused_dynamic_references_fail_before_retrieval(self):
        for target in [
            "https://example.invalid/schema",
            "#/components/schemas/Absent",
            "#anchor",
        ]:
            document = self.document()
            document["components"]["schemas"]["UnsupportedDynamic"] = {
                "$dynamicRef": target
            }
            with (
                self.subTest(target=target),
                self.assertRaisesRegex(
                    ValueError, r"UnsupportedDynamic.*dynamicRef is unsupported"
                ),
            ):
                check(document)

    def test_counts_are_separate(self):
        document = self.document()
        before = check(document)
        self.add_money_response(document)
        after = check(document)
        self.assertEqual(before.operations, after.operations)
        self.assertEqual(before.request_examples, after.request_examples)
        self.assertGreater(after.response_examples, before.response_examples)


if __name__ == "__main__":
    unittest.main()
