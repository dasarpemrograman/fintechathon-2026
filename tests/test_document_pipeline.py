"""Real HTTP, PostgreSQL worker, extraction-cache metering and source-version lineage."""

from contextlib import contextmanager
from copy import deepcopy
import hashlib, unittest
from unittest.mock import patch
import sqlalchemy as sa
from fastapi.testclient import TestClient
from services.api import store, auth, commands
from services.api.app import app
from services.api.settings import settings
from services.worker.jobs import process
from packages.domain.planning import estimate


class Engine:
    def __init__(self, conn):
        self.conn = conn

    @contextmanager
    def begin(self):
        with self.conn.begin_nested():
            yield self.conn


class DocumentPipelineTests(unittest.TestCase):
    def setUp(self):
        self.conn = store.engine.connect()
        self.tx = self.conn.begin()
        self.identity = auth.bootstrap(
            self.conn,
            store.uid("pipeline") + "@example.test",
            "pipeline-test-password",
            "Owner",
            "Pipeline Test",
        )
        self.tenant = self.identity["organization_id"]
        self.actor = self.identity["user_id"]
        self.engine = patch.object(store, "engine", Engine(self.conn))
        self.engine.start()
        self.client = TestClient(app)
        response = self.client.post(
            "/v2/auth/login",
            json={
                "email": self.conn.execute(
                    sa.select(store.users.c.email).where(store.users.c.id == self.actor)
                ).scalar_one(),
                "password": "pipeline-test-password",
            },
            headers={"Idempotency-Key": store.uid("login")},
        )
        self.assertEqual(response.status_code, 200, response.text)
        self.headers = {
            "Authorization": "Bearer " + response.json()["result"]["access_token"]
        }

    def tearDown(self):
        self.engine.stop()
        self.tx.rollback()
        self.conn.close()

    def post(self, path, body):
        return self.client.post(
            "/v2/" + path,
            json=body,
            headers={**self.headers, "Idempotency-Key": store.uid("command")},
        )

    def workspace(self):
        response = self.post(
            "workspaces",
            {
                "mode": "sandbox",
                "business_profile": "reseller",
                "seller_domicile": "KE",
                "dispatch_country": "KE",
                "destination_country": "DE",
                "reporting_currency": "USD",
                "owner_timezone": "Africa/Nairobi",
                "product": {"description": "Test-only goods"},
            },
        )
        self.assertEqual(response.status_code, 201, response.text)
        return response.json()["result"]

    def upload(self, workspace):
        response = self.client.post(
            "/v2/workspaces/" + workspace["id"] + "/documents",
            data={
                "expected_revision": str(workspace["revision"]),
                "document_role": "quotation",
            },
            files={
                "files": (
                    "quote.txt",
                    b"Test-only goods\nQuantity 10 kg\nPrice USD 350.00\n",
                    "text/plain",
                )
            },
            headers={**self.headers, "Idempotency-Key": store.uid("upload")},
        )
        self.assertEqual(response.status_code, 202, response.text)
        return response.json()["result"]

    def run_job(self, identifier):
        row = dict(
            self.conn.execute(
                sa.select(store.jobs).where(store.jobs.c.id == identifier)
            )
            .mappings()
            .one()
        )
        self.conn.execute(
            store.jobs.update()
            .where(store.jobs.c.id == identifier)
            .values(state="running", attempts=row["attempts"] + 1)
        )
        return process(row)

    def current(self, workspace):
        return self.client.get(
            "/v2/workspaces/" + workspace["id"], headers=self.headers
        ).json()["result"]

    def test_duplicate_and_cached_documents_never_charge_again(self):
        workspace = self.workspace()
        first = self.upload(workspace)
        duplicate = self.upload(self.current(workspace))
        self.assertEqual(first["job"]["run"]["id"], duplicate["job"]["run"]["id"])
        self.run_job(first["job"]["run"]["id"])
        another = self.workspace()
        cached = self.upload(another)
        result = self.run_job(cached["job"]["run"]["id"])
        self.assertTrue(result["usage"]["cache_hit"])
        self.assertEqual(result["usage"].get("charged_pages", 0), 0)
        self.assertIn("cached", result["data_modes"])
        usage = commands.all_records(self.conn, self.tenant, "usage")
        self.assertEqual(sum(r["document_pages"] for r in usage), 1)
        self.assertEqual(sum(r["enriched_runs"] for r in usage), 0)
        document = cached["documents"][0]
        download = self.client.get(
            "/v2/workspaces/"
            + another["id"]
            + "/documents/"
            + document["id"]
            + "/content",
            headers=self.headers,
        )
        self.assertEqual(
            hashlib.sha256(download.content).hexdigest(), document["content_hash"]
        )

    def test_supported_original_types_round_trip_through_authorized_http(self):
        from io import BytesIO
        from pathlib import Path
        from PIL import Image

        sources = Path(__file__).resolve().parents[1] / "fixtures/demo/documents"
        jpeg = BytesIO()
        with Image.open(sources / "scan.png") as image:
            image.convert("RGB").save(jpeg, format="JPEG")
        workspace = self.workspace()
        for name, media, content in [
            ("quotation.txt", "text/plain", (sources / "quotation.txt").read_bytes()),
            (
                "quotation.pdf",
                "application/pdf",
                (sources / "quotation.pdf").read_bytes(),
            ),
            ("scan.png", "image/png", (sources / "scan.png").read_bytes()),
            ("scan.jpg", "image/jpeg", jpeg.getvalue()),
        ]:
            with self.subTest(media=media):
                response = self.client.post(
                    "/v2/workspaces/" + workspace["id"] + "/documents",
                    data={
                        "expected_revision": str(self.current(workspace)["revision"]),
                        "document_role": "quotation",
                    },
                    files={"files": (name, content, media)},
                    headers={**self.headers, "Idempotency-Key": store.uid("upload")},
                )
                self.assertEqual(response.status_code, 202, response.text)
                result = response.json()["result"]
                self.run_job(result["job"]["run"]["id"])
                document = result["documents"][0]
                download = self.client.get(
                    "/v2/workspaces/"
                    + workspace["id"]
                    + "/documents/"
                    + document["id"]
                    + "/content",
                    headers=self.headers,
                )
                self.assertEqual(download.status_code, 200, download.text)
                self.assertEqual(download.content, content)
                self.assertEqual(
                    hashlib.sha256(download.content).hexdigest(),
                    document["content_hash"],
                )

    def test_numeric_output_keeps_the_original_source_revision_after_conflict(self):
        workspace = self.workspace()
        ingestion = self.upload(workspace)
        self.run_job(ingestion["job"]["run"]["id"])
        workspace = self.current(workspace)
        evidence = next(
            e
            for e in commands.children(self.conn, self.tenant, "evidence", workspace)
            if e["claim"] == "USD 350.00"
        )
        self.assertEqual(
            evidence["content_hash"], ingestion["documents"][0]["content_hash"]
        )
        self.assertIn("chars", evidence["locator"])
        self.assertEqual(evidence["hash_scope"], "original_document")
        inputs = estimate(
            workspace,
            {
                "quantity": "10",
                "unit": "kg",
                "unit_cost": {"amount": "35", "currency": "USD"},
                "invoice_amount": {"amount": "500", "currency": "USD"},
                "deposit_amount": {"amount": "0", "currency": "USD"},
                "deposit_at": {"instant": "2026-10-16T10:00:00Z", "timezone": "UTC"},
                "balance_at": {"instant": "2026-12-10T10:00:00Z", "timezone": "UTC"},
                "supplier_payment_at": {
                    "instant": "2026-10-17T10:00:00Z",
                    "timezone": "UTC",
                },
                "cash_snapshot": {
                    "available": {"amount": "100", "currency": "USD"},
                    "committed_elsewhere": {"amount": "0", "currency": "USD"},
                    "minimum_buffer": {"amount": "0", "currency": "USD"},
                    "as_of": "2026-10-16T00:00:00Z",
                },
                "target_margin": None,
                "evidence_ids": [evidence["id"]],
            },
        )
        inputs.pop("cost_lines")
        inputs.pop("fx_observations")
        converted = self.post(
            "workspaces/" + workspace["id"] + "/convert-to-deal",
            {"expected_revision": workspace["revision"], **inputs},
        )
        self.assertEqual(converted.status_code, 201, converted.text)
        deal = converted.json()["result"]["deal"]
        root = "deals/" + deal["id"]
        reviewed = self.post(
            root + "/evidence-reviews",
            {
                "expected_revision": deal["revision"],
                "evidence_id": evidence["id"],
                "disposition": "confirmed",
                "reason": "Confirm the uploaded quoted amount",
            },
        )
        self.assertEqual(reviewed.status_code, 200, reviewed.text)
        deal = self.client.get("/v2/" + root, headers=self.headers).json()["result"][
            "deal"
        ]
        accepted = self.post(
            root + "/analyses",
            {
                "expected_revision": deal["revision"],
                "scenario_id": None,
                "scope": "full",
                "execution": "deterministic",
            },
        )
        self.assertEqual(accepted.status_code, 202, accepted.text)
        self.run_job(accepted.json()["result"]["run"]["id"])
        analysis = self.client.get(
            "/v2/" + root + "/analyses", headers=self.headers
        ).json()["result"]["items"][-1]
        self.assertEqual(analysis["cost_totals"]["seller_operating_expense"], "350.00")
        self.assertEqual(
            analysis["before_financing"]["contribution"]["amount"], "150.00"
        )
        ref = next(
            r
            for r in analysis["numeric_lineage"][0]["evidence_refs"]
            if r["id"] == evidence["id"]
        )
        original = self.client.get(
            "/v2/inputs/" + ref["id"] + "/revisions/" + str(ref["revision"]),
            headers=self.headers,
        )
        self.assertEqual(original.status_code, 200, original.text)
        self.assertEqual(original.json()["result"]["claim"], "USD 350.00")
        from packages.contracts.runtime import DOCUMENT

        values = {
            key: value
            for key, value in evidence.items()
            if key in DOCUMENT["components"]["schemas"]["EvidenceInput"]["properties"]
        }
        values.update(
            document_id=None,
            canonical_url="https://quotes.example.test/retired",
            claim="Alternative USD 450 quotation",
            content_hash=hashlib.sha256(b"Alternative USD 450 quotation").hexdigest(),
            hash_scope="manual_excerpt",
            valid_until="2020-01-01",
        )
        deal = self.client.get("/v2/" + root, headers=self.headers).json()["result"][
            "deal"
        ]
        unused = self.post(
            root + "/evidence",
            {"expected_revision": deal["revision"], "evidence": values},
        )
        self.assertEqual(unused.status_code, 200, unused.text)
        still_current = self.client.get(
            "/v2/" + root + "/analyses/" + analysis["id"], headers=self.headers
        )
        self.assertEqual(still_current.status_code, 200, still_current.text)
        self.assertTrue(still_current.json()["result"]["current_for_use"])
        self.assertNotIn(
            unused.json()["result"]["id"],
            still_current.json()["result"]["input_evidence_ids"],
        )
        deal = self.client.get("/v2/" + root, headers=self.headers).json()["result"][
            "deal"
        ]
        conflict = self.post(
            root + "/evidence-reviews",
            {
                "expected_revision": deal["revision"],
                "evidence_id": evidence["id"],
                "disposition": "conflicted",
                "reason": "A conflicting quote was received",
            },
        )
        self.assertEqual(conflict.status_code, 200, conflict.text)
        historic = self.client.get(
            "/v2/" + root + "/analyses/" + analysis["id"], headers=self.headers
        )
        self.assertEqual(historic.status_code, 200, historic.text)
        self.assertFalse(historic.json()["result"]["current_for_use"])
        again = self.client.get(
            "/v2/inputs/" + ref["id"] + "/revisions/" + str(ref["revision"]),
            headers=self.headers,
        )
        self.assertEqual(again.json()["result"], original.json()["result"])
        self.assertEqual(again.json()["result"]["review_status"], "confirmed")
        deal = self.client.get("/v2/" + root, headers=self.headers).json()["result"][
            "deal"
        ]
        approval = self.post(
            root + "/approvals",
            {
                "expected_revision": deal["revision"],
                "purpose": "plan",
                "analysis_hash": analysis["snapshot_hash"],
                "artifact_hash": None,
                "evidence_digest": analysis["evidence_digest"],
                "decision": "approved",
            },
        )
        self.assertEqual(approval.status_code, 409, approval.text)

    def test_conflicting_candidates_and_archived_exports_preserve_originals(self):
        import json

        workspace = self.workspace()
        response = self.client.post(
            "/v2/workspaces/" + workspace["id"] + "/documents",
            data={
                "expected_revision": str(workspace["revision"]),
                "document_role": "quotation",
            },
            files={
                "files": (
                    "conflict.txt",
                    b"Quantity 10 kg\nQuantity 12 kg\n",
                    "text/plain",
                )
            },
            headers={**self.headers, "Idempotency-Key": store.uid("upload")},
        )
        self.assertEqual(response.status_code, 202, response.text)
        uploaded = response.json()["result"]
        self.run_job(uploaded["job"]["run"]["id"])
        workspace = self.current(workspace)
        candidates = commands.children(
            self.conn, self.tenant, "fact_candidate", workspace
        )
        self.assertEqual(len(candidates), 2)
        for candidate in candidates:
            reviewed = self.post(
                "workspaces/" + workspace["id"] + "/fact-reviews",
                {
                    "expected_revision": workspace["revision"],
                    "candidate_id": candidate["id"],
                    "disposition": "conflicted",
                    "reason": "Two contradictory supplier quantities require a decision.",
                    "patch": None,
                },
            )
            self.assertEqual(reviewed.status_code, 200, reviewed.text)
            workspace = self.current(workspace)
        remaining = commands.children(
            self.conn, self.tenant, "fact_candidate", workspace
        )
        self.assertEqual(len(remaining), 2)
        self.assertTrue(all(c["status"] == "conflicted" for c in remaining))
        archived = self.post(
            "workspaces/" + workspace["id"] + "/archive",
            {"expected_revision": workspace["revision"], "archived": True},
        )
        self.assertEqual(archived.status_code, 200, archived.text)
        workspace = self.current(workspace)
        denied = self.post(
            "workspaces/" + workspace["id"] + "/analyses",
            {
                "expected_revision": workspace["revision"],
                "scenario_id": None,
                "scope": "full",
                "execution": "deterministic",
            },
        )
        self.assertEqual(denied.status_code, 409, denied.text)
        root = "/v2/workspaces/" + workspace["id"]
        self.assertEqual(self.client.get(root + "/export").status_code, 401)
        exported = self.client.get(root + "/export", headers=self.headers)
        self.assertEqual(exported.status_code, 200, exported.text)
        bundle = json.loads(exported.content)
        self.assertTrue(bundle["snapshot"]["archived"])
        self.assertTrue(bundle["immutable_history"])
        document = uploaded["documents"][0]
        content = self.client.get(
            root + "/documents/" + document["id"] + "/content", headers=self.headers
        )
        self.assertEqual(content.status_code, 200, content.text)
        self.assertEqual(
            hashlib.sha256(content.content).hexdigest(), document["content_hash"]
        )

    def test_effective_dates_and_expiry_invalidate_reviews_without_editing_history(
        self,
    ):
        from datetime import timedelta

        workspace = self.workspace()
        ingestion = self.upload(workspace)
        self.run_job(ingestion["job"]["run"]["id"])
        workspace = self.current(workspace)
        source = commands.children(self.conn, self.tenant, "evidence", workspace)[0]
        source["effective_from"] = (store.now().date() + timedelta(days=1)).isoformat()
        store.save(self.conn, self.tenant, "evidence", source, parent=workspace["id"])
        # Bind current facts to isolate date applicability from revision invalidation.
        analysis = {
            "base_deal_hash": commands.current_fact_hash(
                self.conn, self.tenant, workspace
            ),
            "input_evidence_ids": [source["id"]],
        }
        view = commands.analysis_view(self.conn, self.tenant, workspace, analysis)
        self.assertFalse(view["current_for_use"])
        self.assertIn(
            "FUTURE_EVIDENCE", [r["code"] for r in view["invalidation_reasons"]]
        )
        source["effective_from"] = None
        source["valid_until"] = (store.now().date() - timedelta(days=1)).isoformat()
        store.save(self.conn, self.tenant, "evidence", source, parent=workspace["id"])
        analysis["base_deal_hash"] = commands.current_fact_hash(
            self.conn, self.tenant, workspace
        )
        view = commands.analysis_view(self.conn, self.tenant, workspace, analysis)
        self.assertFalse(view["current_for_use"])
        self.assertIn(
            "EXPIRED_EVIDENCE", [r["code"] for r in view["invalidation_reasons"]]
        )
