from copy import deepcopy
from decimal import Decimal
import unittest
import test_demo_goldens as goldens
from packages.domain.comparison import assess, rank_views
from packages.domain.economics import compute


class ScenarioComparisonTests(unittest.TestCase):
    def fixture(self):
        parent, costs, obligations = goldens.DemoGoldenTests().fixture("id-reseller")
        parent["id"] = "parent"
        return parent, costs, obligations

    def test_cash_and_margin_preferences_rank_declared_metrics_without_mutation(self):
        parent, costs, obligations = self.fixture()
        result = compute(parent, costs, obligations, [], [], [])
        scenario = {"patches": []}
        view = assess(
            parent, scenario, result, obligations, [], [], [], parent["constraints"]
        )
        first = {"id": "a", "current_for_use": True, "owner_comparison": view, **result}
        first["owner_comparison"]["ranking_preference"] = "cash"
        second = deepcopy(first)
        second["id"] = "b"
        second["cash_metrics"]["buffer_shortfall"] = "0.00"
        second["owner_comparison"]["checks"] = [
            {**check, "status": "satisfied"}
            for check in second["owner_comparison"]["checks"]
        ]
        original = deepcopy([first, second])
        ranked = rank_views([first, second])
        self.assertEqual(
            next(row for row in ranked if row["id"] == "b")["owner_comparison"]["rank"],
            1,
        )
        self.assertEqual([first, second], original)
        stale = deepcopy(first)
        stale["current_for_use"] = False
        self.assertIsNone(rank_views([stale])[0]["owner_comparison"]["rank"])

    def test_joint_terms_retain_all_required_counterparties_and_owner_scope(self):
        parent, costs, obligations = self.fixture()
        base = deepcopy(parent)
        terms = deepcopy(parent["payment_terms"])
        terms[0]["amount"]["amount"] = "40000000"
        supplier = next(term for term in terms if term["side"] == "supplier")
        supplier["amount"]["amount"] = "40000000"
        scenario = {
            "patches": [
                {
                    "path": "/payment_terms",
                    "value": terms,
                    "agreement_required_from": [],
                }
            ]
        }
        parent["payment_terms"] = terms
        result = compute(base, costs, obligations, [], [], [])
        view = assess(
            parent, scenario, result, obligations, [], [], [], base["constraints"], base
        )
        expected = {p["id"] for p in parent["parties"] if "seller" not in p["roles"]}
        self.assertEqual(set(view["required_counterparty_ids"]), expected)
        restricted = deepcopy(base["constraints"])
        restricted["allowable_changes"] = ["buyer payment terms"]
        view = assess(
            parent, scenario, result, obligations, [], [], [], restricted, base
        )
        self.assertEqual(
            next(
                check for check in view["checks"] if check["code"] == "ALLOWABLE_CHANGE"
            )["status"],
            "failed",
        )

    def test_local_date_deadline_does_not_assume_utc_midnight(self):
        parent, costs, obligations = self.fixture()
        parent["constraints"]["delivery_deadline"] = {
            "date": "2026-10-16",
            "timezone": "Asia/Jakarta",
        }
        milestone = {
            "id": "arrival",
            "kind": "arrival",
            "schedule": {
                "kind": "fixed",
                "due": {"instant": "2026-10-16T12:00:00Z", "timezone": "UTC"},
            },
            "actual": None,
            "forecast": None,
            "agreed": None,
            "proposed": None,
        }
        result = compute(parent, costs, obligations, [milestone], [], [])
        view = assess(
            parent,
            {"patches": []},
            result,
            obligations,
            [milestone],
            [],
            [],
            parent["constraints"],
        )
        self.assertEqual(
            next(
                check
                for check in view["checks"]
                if check["code"] == "DELIVERY_DEADLINE"
            )["status"],
            "satisfied",
        )
