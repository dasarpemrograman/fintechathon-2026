"""Lease recovery and stale completion through PostgreSQL worker transactions."""

import unittest
from datetime import timedelta
from unittest.mock import patch
import sqlalchemy as sa
import test_workflow_commands as workflow_fixture
import test_document_pipeline as document_fixture
from services.api import store, commands
from services.worker.jobs import claim, process


class JobRecoveryTests(unittest.TestCase):
    def setUp(self):
        self.fixture = workflow_fixture.WorkflowCommandTests()
        self.fixture.setUp()
        self.conn = self.fixture.conn
        self.context = self.fixture.context
        self.parent = self.fixture.deal
        self.dataset = store.uid("job_fixture")
        self.parent["dataset_id"] = self.dataset
        store.save(
            self.conn,
            self.context["tenant"],
            "deal",
            self.parent,
            parent=self.parent["workspace_id"],
            dataset=self.dataset,
        )
        self.engine = patch.object(store, "engine", document_fixture.Engine(self.conn))
        self.engine.start()

    def tearDown(self):
        self.engine.stop()
        self.fixture.tearDown()

    def enqueue(self):
        return commands.enqueue(
            self.conn,
            self.context,
            self.parent,
            "analysis",
            {"scenario_id": None, "scope": "full", "execution": "deterministic"},
        )["run"]["id"]

    def expire(self, identifier):
        self.conn.execute(
            store.jobs.update()
            .where(store.jobs.c.id == identifier)
            .values(lease_until=store.now() - timedelta(seconds=1))
        )

    def test_three_interrupted_claims_exhaust_budget_without_charge(self):
        identifier = self.enqueue()
        for attempt in range(3):
            claimed = claim("real", self.dataset)
            self.assertEqual(claimed["id"], identifier)
            self.assertEqual(claimed["attempts"], attempt)
            self.expire(identifier)
        self.assertIsNone(claim("real", self.dataset))
        run = store.get(self.conn, self.context["tenant"], "run", identifier)
        self.assertEqual(run["status"], "failed")
        self.assertEqual(run["blockers"][0]["code"], "JOB_ATTEMPTS_EXHAUSTED")
        self.assertEqual(
            commands.all_records(self.conn, self.context["tenant"], "usage"), []
        )

    def test_older_input_completion_retains_output_without_replacing_head(self):
        identifier = self.enqueue()
        claimed = claim("real", self.dataset)
        self.parent["revision"] += 2
        self.parent["states"]["analysis"] = "needs_input"
        store.save(
            self.conn,
            self.context["tenant"],
            "deal",
            self.parent,
            parent=self.parent["workspace_id"],
            dataset=self.dataset,
        )
        result = process(claimed)
        self.assertEqual(result["status"], "partial")
        self.assertIn("STALE_INPUT", [w["code"] for w in result["warnings"]])
        self.assertTrue(result["output_refs"])
        current = store.get(
            self.conn, self.context["tenant"], "deal", self.parent["id"]
        )
        self.assertEqual(current["revision"], self.parent["revision"])
        self.assertEqual(current["states"]["analysis"], "needs_input")

    def test_cancellation_preserves_committed_outputs(self):
        from types import SimpleNamespace
        from services.api.handlers import write_operation

        identifier = self.enqueue()
        claimed = claim("real", self.dataset)
        self.parent["revision"] += 1
        store.save(
            self.conn,
            self.context["tenant"],
            "deal",
            self.parent,
            parent=self.parent["workspace_id"],
            dataset=self.dataset,
        )
        result = process(claimed)
        self.assertTrue(result["output_refs"])
        cancelled = write_operation(
            self.conn,
            self.context,
            "cancelRun",
            None,
            {},
            SimpleNamespace(path_params={"id": identifier}),
        )["result"]
        self.assertEqual(cancelled["output_refs"], result["output_refs"])
        self.assertEqual(cancelled["status"], result["status"])
        for ref in result["output_refs"]:
            self.assertIsNotNone(
                store.get(self.conn, self.context["tenant"], ref["kind"], ref["id"])
            )
