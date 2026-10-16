from copy import deepcopy
import unittest
from packages.domain.discovery import plan
from services.api.store import DomainError


class DiscoveryPlanningTests(unittest.TestCase):
    def test_outward_china_uses_export_and_destination_import_separately(self):
        queries, warnings = plan(
            {
                "dispatch_country": "CN",
                "seller_domicile": "CN",
                "destination_country": "SG",
            },
            {
                "approved_public_terms": ["green coffee beans wholesale"],
                "categories": ["requirements", "market_price", "finance"],
            },
        )
        outbound = next(
            q
            for q in queries
            if q["jurisdiction"] == "CN" and q["category"] == "requirements"
        )
        self.assertEqual(outbound["direction"], "export")
        self.assertIn("出口", outbound["query"])
        self.assertNotIn("进口", outbound["query"])
        self.assertIn("site:customs.gov.cn", outbound["query"])
        inbound = next(
            q
            for q in queries
            if q["jurisdiction"] == "SG" and q["category"] == "requirements"
        )
        self.assertIn("import", inbound["query"])
        self.assertNotIn("customs.gov.cn", inbound["query"])

    def test_private_legal_and_display_names_bank_details_and_contract_text_are_excluded(
        self,
    ):
        parent = {
            "dispatch_country": "KE",
            "seller_domicile": "KE",
            "destination_country": "DE",
            "parties": [
                {"legal_name": "Private Legal Buyer", "display_name": "Private Alias"}
            ],
        }
        for term in [
            "coffee Private Legal Buyer",
            "coffee Private Alias",
            "IBAN GB29NWBK60161331926819",
            "bank account 12345678",
            "private contract excerpt",
        ]:
            with self.assertRaises(DomainError):
                plan(
                    parent,
                    {"approved_public_terms": [term], "categories": ["requirements"]},
                )
        queries, _ = plan(
            parent,
            {
                "approved_public_terms": ["dried mango food grade"],
                "categories": ["requirements"],
            },
        )
        self.assertTrue(all("Private" not in q["query"] for q in queries))
        self.assertTrue(any("Einfuhr" in q["query"] for q in queries))

    def test_unknown_country_authority_is_a_limitation_not_a_copied_rule(self):
        queries, warnings = plan(
            {
                "dispatch_country": "BR",
                "seller_domicile": "BR",
                "destination_country": "NO",
            },
            {
                "approved_public_terms": ["declared goods"],
                "categories": ["requirements"],
            },
        )
        self.assertTrue(warnings)
        self.assertTrue(
            all(
                "CN" not in q["query"] and "customs.gov.cn" not in q["query"]
                for q in queries
            )
        )
