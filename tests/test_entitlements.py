from datetime import timedelta
from unittest.mock import patch
import unittest
import sqlalchemy as sa
from services.api import store, auth, commands
from packages.domain.entitlements import balance, allocations, require_feature


class EntitlementTests(unittest.TestCase):
    def setUp(self):
        self.conn = store.engine.connect()
        self.tx = self.conn.begin()
        self.identity = auth.bootstrap(
            self.conn,
            store.uid("entitlement") + "@example.test",
            "entitlement-test-password",
            "Owner",
            "Entitlement Test",
        )
        self.tenant = self.identity["organization_id"]
        self.actor = self.identity["user_id"]

    def tearDown(self):
        self.tx.rollback()
        self.conn.close()

    def policy(self, value):
        self.conn.execute(
            store.organizations.update()
            .where(store.organizations.c.id == self.tenant)
            .values(policy=value)
        )

    def charge(self, runs=0, pages=0):
        allocated, version = allocations(self.conn, self.tenant, runs, pages)
        row = {
            **store.meta(self.tenant, self.actor, "usage"),
            "run_id": store.uid("run"),
            "enriched_runs": runs,
            "document_pages": pages,
            "allocations": allocated,
            "catalog_version": version,
        }
        store.save(self.conn, self.tenant, "usage", row)
        return row

    def test_included_before_addon_then_expiry_preserves_deterministic_and_manual_work(
        self,
    ):
        expiry = (store.now() + timedelta(days=2)).isoformat()
        self.policy(
            {
                "plan": "pro",
                "runs": 1,
                "pages": 2,
                "active": True,
                "addons": [
                    {
                        "id": "addon_credit",
                        "unit": "enriched_run",
                        "quantity": 2,
                        "expires_at": expiry,
                    }
                ],
            }
        )
        first = self.charge(runs=1)
        second = self.charge(runs=1)
        self.assertEqual(first["allocations"][0]["pool"], "included")
        self.assertEqual(second["allocations"][0]["pool"], "addon")
        self.assertEqual(
            balance(self.conn, self.tenant)["units"]["enriched_run"]["addon_remaining"],
            1,
        )
        self.policy(
            {
                "plan": "pro",
                "runs": 1,
                "pages": 2,
                "active": False,
                "addons": [
                    {
                        "id": "addon_credit",
                        "unit": "enriched_run",
                        "quantity": 2,
                        "expires_at": expiry,
                    }
                ],
            }
        )
        self.assertFalse(
            commands.admission(self.conn, {"tenant": self.tenant})["admitted"]
        )
        self.assertTrue(
            commands.admission(self.conn, {"tenant": self.tenant}, False)["admitted"]
        )
        self.assertFalse(balance(self.conn, self.tenant)["active"])
        with self.assertRaises(store.DomainError):
            require_feature(self.conn, self.tenant, "draft")

    def test_monthly_included_reset_does_not_reset_addon_consumption(self):
        clock = store.now().replace(day=15, hour=12)
        expiry = (clock + timedelta(days=70)).isoformat()
        self.policy(
            {
                "plan": "pro",
                "runs": 1,
                "pages": 2,
                "addons": [
                    {
                        "id": "addon_credit",
                        "unit": "enriched_run",
                        "quantity": 2,
                        "expires_at": expiry,
                    }
                ],
            }
        )
        with patch.object(store, "now", return_value=clock):
            self.charge(runs=1)
            self.charge(runs=1)
        next_month = (clock.replace(day=28) + timedelta(days=5)).replace(day=15)
        with patch.object(store, "now", return_value=next_month):
            state = balance(self.conn, self.tenant)
            self.assertEqual(state["units"]["enriched_run"]["included_remaining"], 1)
            self.assertEqual(state["units"]["enriched_run"]["addon_remaining"], 1)

    def test_free_plan_blocks_deal_activation_and_paid_plan_releases_archived_slot(
        self,
    ):
        self.policy({"plan": "free_sandbox", "active": True})
        with self.assertRaises(store.DomainError):
            require_feature(self.conn, self.tenant, "deal")
        self.policy({"plan": "deal_pass", "active": True, "active_deals": 1})
        workspace = commands.new_workspace(
            self.conn,
            {"tenant": self.tenant, "actor": self.actor, "scope": "real"},
            {
                "mode": "deal",
                "business_profile": "reseller",
                "seller_domicile": "ID",
                "dispatch_country": "ID",
                "destination_country": "SG",
                "reporting_currency": "IDR",
                "owner_timezone": "Asia/Jakarta",
                "product": {"description": "Declared goods"},
            },
        )
        with self.assertRaises(store.DomainError):
            require_feature(self.conn, self.tenant, "deal")
        workspace["archived"] = True
        workspace["revision"] += 1
        store.save(self.conn, self.tenant, "workspace", workspace)
        require_feature(self.conn, self.tenant, "deal")
