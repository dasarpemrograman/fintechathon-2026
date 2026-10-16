"""Real PostgreSQL checkpoint acceptance, including the actual HTTP closure boundary."""

from contextlib import contextmanager
from unittest.mock import patch
import unittest
import sqlalchemy as sa
from fastapi.testclient import TestClient
from services.api import store, commands
from services.api.app import app
from services.api.settings import settings
from packages.domain.demo import seed, analyze_seeded, DATASET
from packages.domain.demo_stages import seed_stages, seed_sandbox_plans, drain
from packages.domain.workflow import readiness


class ConnectionEngine:
    def __init__(self, conn):
        self.conn = conn

    @contextmanager
    def begin(self):
        with self.conn.begin_nested():
            yield self.conn


class SeededAcceptanceTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        with patch.object(settings, "mode", "demo"):
            seed()
            drain()
            analyze_seeded()
            drain()
            seed_sandbox_plans()
            seed_stages()

    def test_four_checkpoint_histories_have_causal_and_independent_states(self):
        with patch.object(settings, "mode", "demo"), store.engine.connect() as conn:
            stages = {}
            for stage in ["negotiation", "blocked_goods", "reconciling", "closed"]:
                workspace = store.get(
                    conn, "demo_org_id", "workspace", "demo_stage_" + stage
                )
                deal = store.get(conn, "demo_org_id", "deal", workspace["deal_id"])
                stages[stage] = deal
                self.assertGreater(
                    len(commands.children(conn, "demo_org_id", "analysis", deal)), 1
                )
                self.assertTrue(
                    commands.children(conn, "demo_org_id", "artifact", deal)
                )
                self.assertTrue(commands.children(conn, "demo_org_id", "audit", deal))
            gate, blockers = readiness(
                conn, {"tenant": "demo_org_id"}, stages["blocked_goods"], "shipment"
            )
            self.assertEqual(gate["status"], "blocked")
            self.assertIn("GOODS_CONFORMITY", {b["code"] for b in blockers})
            self.assertEqual(stages["reconciling"]["states"]["buyer_payment"], "paid")
            self.assertEqual(
                stages["reconciling"]["states"]["internal_closure"], "reconciling"
            )
            self.assertEqual(stages["closed"]["states"]["buyer_payment"], "paid")
            self.assertEqual(stages["closed"]["states"]["shipment"], "delivered")
            self.assertEqual(stages["closed"]["states"]["internal_closure"], "closed")
            gate, blockers = readiness(
                conn, {"tenant": "demo_org_id"}, stages["closed"], "internal_close"
            )
            self.assertEqual(blockers, [], blockers)

    def test_full_actual_http_closure_payload_and_tenant_denial(self):
        conn = store.engine.connect()
        tx = conn.begin()
        try:
            with (
                patch.object(settings, "mode", "demo"),
                patch.object(store, "engine", ConnectionEngine(conn)),
                TestClient(app) as client,
            ):
                login = client.post(
                    "/v2/auth/demo-session",
                    json={"user_id": "demo_id_owner"},
                    headers={"Idempotency-Key": store.uid("auth")},
                )
                self.assertEqual(login.status_code, 200, login.text)
                headers = {
                    "Authorization": "Bearer " + login.json()["result"]["access_token"]
                }
                workspace = store.get(
                    conn, "demo_org_id", "workspace", "demo_stage_closed"
                )
                deal = store.get(conn, "demo_org_id", "deal", workspace["deal_id"])
                reconciliation = commands.children(
                    conn, "demo_org_id", "reconciliation", deal
                )[-1]
                response = client.post(
                    "/v2/deals/" + deal["id"] + "/close",
                    json={
                        "expected_revision": deal["revision"],
                        "reconciliation_hash": reconciliation["reconciliation_hash"],
                    },
                    headers={**headers, "Idempotency-Key": store.uid("close")},
                )
                self.assertEqual(response.status_code, 200, response.text)
                payload = response.json()
                self.assertEqual(payload["status"], "completed")
                self.assertEqual(
                    payload["result"]["deal"]["states"]["internal_closure"], "closed"
                )
                self.assertIn("line_items", payload["result"]["deal"])
                self.assertEqual(
                    payload["result"]["gate"]["status"], "ready_for_next_action"
                )
                cn = store.get(
                    conn, "demo_org_cn", "workspace", "demo_cn-reseller_deal"
                )
                self.assertEqual(
                    client.get(
                        "/v2/workspaces/" + cn["id"], headers=headers
                    ).status_code,
                    404,
                )
                analysis = commands.children(conn, "demo_org_id", "analysis", deal)[-1]
                if analysis.get("numeric_lineage"):
                    refs = analysis["numeric_lineage"][0]["evidence_refs"]
                    self.assertTrue(refs)
                    source = client.get(
                        "/v2/inputs/"
                        + refs[0]["id"]
                        + "/revisions/"
                        + str(refs[0]["revision"]),
                        headers=headers,
                    )
                    self.assertEqual(source.status_code, 200, source.text)
        finally:
            tx.rollback()
            conn.close()

    def test_seed_replay_does_not_duplicate_resources(self):
        with store.engine.connect() as conn:
            before = conn.execute(
                sa.select(sa.func.count())
                .select_from(store.registry)
                .where(store.registry.c.dataset_id == DATASET)
            ).scalar_one()
        with patch.object(settings, "mode", "demo"):
            seed()
            seed_sandbox_plans()
            seed_stages()
        with store.engine.connect() as conn:
            after = conn.execute(
                sa.select(sa.func.count())
                .select_from(store.registry)
                .where(store.registry.c.dataset_id == DATASET)
            ).scalar_one()
        self.assertEqual(before, after)

    def test_reconciliation_uses_preserved_baselines_after_estimate_changes(self):
        from services.api.reconciliation import reconcile_command
        from decimal import Decimal

        with patch.object(settings, "mode", "demo"), store.engine.connect() as conn:
            tx = conn.begin()
            try:
                workspace = store.get(
                    conn, "demo_org_id", "workspace", "demo_stage_closed"
                )
                deal = store.get(conn, "demo_org_id", "deal", workspace["deal_id"])
                analyses = commands.children(conn, "demo_org_id", "analysis", deal)
                cost = commands.children(conn, "demo_org_id", "cost_line", deal)[0]
                # Retain a baseline in this rollback transaction. Older installed
                # seed revisions may predate cost breakdowns.
                from packages.domain.economics import compute
                from copy import deepcopy

                baseline = deepcopy(analyses[0])
                baseline.update(
                    id=store.uid("analysis"),
                    created_at="2000-01-01T00:00:00Z",
                    snapshot_hash="a" * 64,
                )
                calculated = compute(
                    deal,
                    commands.children(conn, "demo_org_id", "cost_line", deal),
                    commands.children(conn, "demo_org_id", "obligation", deal),
                    commands.children(conn, "demo_org_id", "milestone", deal),
                    commands.children(conn, "demo_org_id", "fx_observation", deal),
                    [],
                    [],
                    commands.children(conn, "demo_org_id", "receipt", deal),
                )
                baseline["cost_breakdown"] = calculated["cost_breakdown"]
                store.save(
                    conn,
                    "demo_org_id",
                    "analysis",
                    baseline,
                    parent=deal["id"],
                    dataset=DATASET,
                )
                expected = next(
                    row["reporting_amount"]
                    for row in baseline["cost_breakdown"]
                    if row["cost_line_ref"]["id"] == cost["id"]
                )
                cost["estimate"]["base"] = {
                    "amount": "999999999",
                    "currency": deal["reporting_currency"],
                }
                store.save(
                    conn,
                    "demo_org_id",
                    "cost_line",
                    cost,
                    parent=deal["id"],
                    dataset=DATASET,
                )
                context = {
                    "tenant": "demo_org_id",
                    "actor": "demo_id_owner",
                    "request_id": store.uid("request"),
                    "roles": ["owner"],
                    "scope": "demo",
                }
                result = reconcile_command(
                    conn,
                    context,
                    "reconcileDeal",
                    deal,
                    {"actual_evidence_ids": [], "adjustments": []},
                )["result"]
                rows = [
                    v
                    for v in result["variances"]
                    if v["cost_line_ref"]["id"] == cost["id"]
                ]
                initial = next(v for v in rows if v["baseline_kind"] == "initial")
                self.assertEqual(initial["baseline"], expected)
                self.assertEqual(
                    initial["baseline_analysis_hash"], baseline["snapshot_hash"]
                )
                self.assertEqual(
                    Decimal(initial["difference"]["amount"]),
                    Decimal(initial["actual"]["amount"]) - Decimal(expected["amount"]),
                )
                self.assertEqual(
                    {r["baseline_kind"] for r in rows}, {"initial", "latest_approved"}
                )
            finally:
                tx.rollback()
