from copy import deepcopy
from datetime import date
import unittest
import test_demo_goldens as goldens
from packages.domain.finance import screen, preparation
from packages.domain.economics import compute


class FinancePreparationTests(unittest.TestCase):
    def setUp(self):
        self.parent, _, _ = goldens.DemoGoldenTests().fixture("id-reseller")
        self.parent["seller_domicile"] = "ID"
        for term in self.parent["payment_terms"]:
            if term["side"] == "buyer" and term["instrument"] != "advance":
                term["instrument"] = "open_account"
        self.evidence = {
            "proof": {
                "review_status": "confirmed",
                "valid_until": None,
                "effective_from": None,
                "canonical_url": "https://provider.example.test/terms",
            }
        }
        self.product = {
            "provider": "Declared lender",
            "jurisdiction": "ID",
            "source_ids": ["proof"],
            "stage": "pre_shipment",
            "eligible_entity_types": ["PT"],
            "eligible_instruments": ["open_account"],
            "minimum_tenor_days": 30,
            "maximum_tenor_days": 180,
            "eligibility_predicates": [
                {
                    "name": "Entity",
                    "status": "satisfied",
                    "reason": "Reviewed",
                    "evidence_ids": ["proof"],
                }
            ],
            "document_requirements": [
                {
                    "name": "Registration",
                    "basis": "provider_required",
                    "status": "present",
                    "evidence_ids": ["proof"],
                }
            ],
            "rate": "0.12",
            "rate_basis": "annual_simple",
            "fees": [],
            "currency": "IDR",
            "minimum_amount": None,
            "maximum_amount": None,
            "recourse": "yes",
            "security_requirements": ["Guarantee"],
            "indicative_lead_days": 2,
            "valid_until": None,
        }
        self.request = {
            "company": {
                "entity_type": "PT",
                "registration_evidence_ids": ["proof"],
                "financial_evidence_ids": ["proof"],
                "security_predicates": [
                    {
                        "name": "Guarantee",
                        "status": "satisfied",
                        "reason": "Reviewed",
                        "evidence_ids": ["proof"],
                    }
                ],
                "unknowns": [],
            },
            "requested_amount": {"amount": "60000000", "currency": "IDR"},
            "required_by": {"date": "2026-11-01", "timezone": "Asia/Jakarta"},
            "funding_stage": "pre_shipment",
            "requested_tenor_days": 60,
        }

    def test_stage_instrument_entity_tenor_and_currency_fit_are_independent(self):
        self.assertEqual(
            screen(
                self.product,
                self.parent,
                self.request,
                self.evidence,
                date(2026, 10, 16),
            )["fit"],
            "potentially_suitable",
        )
        for field, value in [
            ("stage", "post_shipment"),
            ("eligible_instruments", ["lc"]),
            ("eligible_entity_types", ["Other"]),
            ("maximum_tenor_days", 30),
            ("currency", "USD"),
        ]:
            product = {**self.product, field: value}
            result = screen(
                product, self.parent, self.request, self.evidence, date(2026, 10, 16)
            )
            self.assertEqual(result["fit"], "incompatible")
            self.assertTrue(result["failed_predicates"])

    def test_missing_rate_and_unreviewed_security_stay_unknown(self):
        product = {**self.product, "rate": None}
        result = screen(
            product, self.parent, self.request, self.evidence, date(2026, 10, 16)
        )
        self.assertEqual(result["fit"], "needs_information")
        self.assertTrue(any("Rate" in item for item in result["unknown_predicates"]))
        request = deepcopy(self.request)
        request["company"]["security_predicates"] = []
        self.assertEqual(
            screen(
                self.product, self.parent, request, self.evidence, date(2026, 10, 16)
            )["fit"],
            "needs_information",
        )

    def test_unknown_recourse_blocks_fit_and_application_ready_preparation(self):
        product = {**self.product, "recourse": "unknown"}
        self.assertEqual(
            screen(
                product, self.parent, self.request, self.evidence, date(2026, 10, 16)
            )["fit"],
            "needs_information",
        )
        pack = preparation(
            self.parent,
            self.option(),
            product,
            ["proof"],
            self.evidence,
            [],
            {},
            {},
            date(2026, 10, 16),
        )
        self.assertEqual(pack["preparation_status"], "needs_information")
        self.assertIn("FINANCE_RECOURSE_UNKNOWN", [row["code"] for row in pack["gaps"]])

    def option(self):
        def event(kind, day, amount):
            return {
                "kind": kind,
                "amount": {"amount": amount, "currency": "IDR"},
                "schedule": {
                    "kind": "fixed",
                    "due": {
                        "instant": f"2026-11-{day:02d}T12:00:00Z",
                        "timezone": "UTC",
                    },
                },
                "status": "proposed",
                "evidence_ids": ["proof"],
            }

        return {
            "id": "option",
            "fit": "potentially_suitable",
            "draw": {"amount": "60000000", "currency": "IDR"},
            "schedule": [
                event("loan_draw", 1, "60000000"),
                event("principal_repayment", 30, "60000000"),
                event("finance_cost", 30, "600000"),
            ],
            "status": "proposed",
        }

    def test_ready_pack_is_preparation_and_missing_required_document_blocks_it(self):
        seller = next(p["id"] for p in self.parent["parties"] if "seller" in p["roles"])
        obligation = {
            "id": "use",
            "payer_party_id": seller,
            "amount": {"amount": "60000000", "currency": "IDR"},
            "status": "open",
            "schedule": self.option()["schedule"][0]["schedule"],
        }
        option = self.option()
        before = deepcopy(option)
        pack = preparation(
            self.parent,
            option,
            self.product,
            ["proof"],
            self.evidence,
            [obligation],
            {},
            {},
            date(2026, 10, 16),
        )
        self.assertEqual(pack["preparation_status"], "application_ready")
        self.assertEqual(pack["tenor_days"], 29)
        self.assertEqual(option, before)
        self.assertNotIn("lender_approval", pack)
        self.assertEqual(pack["funds_use_schedule"][0]["obligation_ref"]["id"], "use")
        product = deepcopy(self.product)
        product["document_requirements"][0]["status"] = "missing"
        self.assertEqual(
            preparation(
                self.parent,
                option,
                product,
                [],
                self.evidence,
                [obligation],
                {},
                {},
                date(2026, 10, 16),
            )["preparation_status"],
            "needs_information",
        )

    def test_missing_financing_schedule_does_not_become_free_financing(self):
        parent, costs, obligations = goldens.DemoGoldenTests().fixture("id-reseller")
        option = self.option()
        option["schedule"] = []
        result = compute(parent, costs, obligations, [], [], [], [option])
        self.assertEqual(result["completeness"], "partial")
        self.assertIsNone(result["after_financing"]["funding_cost"])
        self.assertIsNone(result["after_financing"]["cash_metrics"])
        self.assertEqual(
            result["before_financing"]["contribution"]["amount"], "26000000.00"
        )
