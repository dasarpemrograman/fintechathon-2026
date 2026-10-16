import unittest
import test_demo_goldens as goldens
from packages.domain.economics import compute
from packages.domain.artifacts import render


class ArtifactTests(unittest.TestCase):
    def test_template_binds_exact_scenario_amounts_dates_and_missing_legal_terms(self):
        parent, costs, obligations = goldens.DemoGoldenTests().fixture("id-reseller")
        result = compute(parent, costs, obligations, [], [], [])
        result.update(snapshot_hash="a" * 64, evidence_digest="b" * 64)
        text, placeholders = render(
            parent, {"id": "scenario_selected"}, result, "recommendation", "id"
        )
        self.assertIn("IDR 26000000.00", text)
        self.assertIn("IDR 160000000", text)
        self.assertIn("2026-10-16T11:00:00+00:00", text)
        self.assertIn("[governing law]", text)
        self.assertIn("belum dikirim", text)
        self.assertIn("Skenario: scenario_selected", text)
        self.assertTrue(placeholders)

    def test_unsupported_language_is_an_explicit_limitation(self):
        from services.api.store import DomainError

        with self.assertRaises(DomainError):
            render({}, {}, {}, "agreement", "unavailable")

    def test_counterparty_templates_exclude_internal_profit_and_upstream_terms(self):
        parent, costs, obligations = goldens.DemoGoldenTests().fixture("id-reseller")
        result = compute(parent, costs, obligations, [], [], [])
        result.update(snapshot_hash="a" * 64, evidence_digest="b" * 64)
        for kind in ["message", "agreement", "clause_revision", "amendment"]:
            text, placeholders = render(
                parent, {"id": "scenario_selected"}, result, kind, "en"
            )
            self.assertIn("IDR 160000000", text)
            self.assertNotIn("Planned contribution", text)
            self.assertNotIn("Minimum cash:", text)
            self.assertNotIn("IDR 50000000", text)
            self.assertIn("[governing law]", text)
            if kind == "amendment":
                self.assertIn("[original agreement reference]", text)
