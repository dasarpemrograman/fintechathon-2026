"""Provision real disposable organization policies through the operator CLI."""

from datetime import timedelta
import subprocess
import sys
import unittest
from packages.domain.entitlements import CATALOG, balance, timestamp
from services.api import commands, store
from services.api.settings import ROOT
import test_http_foundation as foundation


class PilotProvisioningTests(unittest.TestCase):
    def setUp(self):
        self.fixture = foundation.HttpFoundationTests()
        self.fixture.setUp()
        self.tenant = self.fixture.identity["organization_id"]

    def tearDown(self):
        self.fixture.tearDown()

    def provision(self, plan, *args):
        return subprocess.run(
            [
                sys.executable,
                str(ROOT / "scripts/set_plan.py"),
                "--organization",
                self.tenant,
                "--plan",
                plan,
                *args,
            ],
            capture_output=True,
            text=True,
            timeout=20,
            cwd=ROOT,
        )

    def test_catalog_plans_and_explicit_institutional_limits_are_audited(self):
        missing = self.provision("institutional")
        self.assertEqual(missing.returncode, 2)
        self.assertIn("requires all four explicit limits", missing.stderr)
        before = store.now()
        for name in ["free_sandbox", "deal_pass", "pro", "team", "institutional"]:
            with self.subTest(plan=name):
                args = (
                    [
                        "--runs",
                        "7",
                        "--pages",
                        "70",
                        "--users",
                        "4",
                        "--active-deals",
                        "6",
                        "--terms-reference",
                        "synthetic-reviewed-pilot-terms",
                    ]
                    if name == "institutional"
                    else []
                )
                result = self.provision(name, *args)
                self.assertEqual(result.returncode, 0, result.stderr)
                with store.engine.connect() as conn:
                    state = balance(conn, self.tenant)
                    self.assertEqual(state["version"], CATALOG["version"])
                    self.assertEqual(state["policy"]["plan"], name)
                    self.assertEqual(
                        state["policy"]["runs"],
                        (
                            7
                            if name == "institutional"
                            else CATALOG["plans"][name]["runs"]
                        ),
                    )
                    if name == "deal_pass":
                        expires = timestamp(state["policy"]["expires_at"])
                        self.assertGreaterEqual(expires, before + timedelta(days=90))
                        self.assertLessEqual(expires, store.now() + timedelta(days=90))
                    if name == "institutional":
                        self.assertEqual(
                            state["policy"]["terms_reference"],
                            "synthetic-reviewed-pilot-terms",
                        )
                        self.assertIsNone(state["plan"]["price_idr"])
                    audits = commands.all_records(conn, self.tenant, "audit")
                    self.assertTrue(
                        any(
                            row["action"] == "provisionPilotEntitlement"
                            and row["created_by"] == "local_operator"
                            for row in audits
                        )
                    )
