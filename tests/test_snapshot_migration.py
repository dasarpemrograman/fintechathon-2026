from copy import deepcopy
from pathlib import Path
import sys
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from packages.domain.migration import import_snapshot
from scripts.validate_contract import load_contract, schema_validator


class SnapshotMigrationTests(unittest.TestCase):
    def test_original_retained_and_unknown_invoice_not_invented(self):
        document = load_contract()
        current = document["paths"]["/v2/deals/{id}/close"]["post"]["responses"]["200"][
            "content"
        ]["application/json"]["examples"]["closedDeal"]["value"]["result"]["deal"]
        source = deepcopy(current)
        for key in ["execution_scope", "dataset_id", "archived", "invoices"]:
            source.pop(key)
        source["schema_version"] = "2.1"
        before = deepcopy(source)
        original, migrated = import_snapshot(source, resource="deal")
        self.assertEqual(source, before)
        self.assertEqual(original, before)
        self.assertEqual(migrated["schema_version"], "2.2")
        self.assertEqual(migrated["execution_scope"], "real")
        self.assertIsNone(migrated["dataset_id"])
        self.assertEqual(migrated["invoices"], [])
        self.assertEqual(migrated["unknowns"][-1]["field_path"], "/invoices")
        schema_validator(document, "Deal").validate(migrated)
        migrated["line_items"].clear()
        self.assertTrue(original["line_items"])

    def test_other_versions_cannot_be_silently_reinterpreted(self):
        with self.assertRaises(ValueError):
            import_snapshot({"schema_version": "2.0"}, resource="deal")
