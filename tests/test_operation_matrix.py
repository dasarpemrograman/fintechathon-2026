"""Every route's role boundary and authenticated read/error paths use the real DB."""

from copy import deepcopy
import json, re, unittest
from unittest.mock import patch
import sqlalchemy as sa
from starlette.requests import Request
from fastapi.testclient import TestClient
from services.api import auth, store, commands
from services.api.app import app, context_for
from services.api.handlers import SEGMENTS
from services.api.settings import settings
from packages.contracts.runtime import OPERATIONS
from packages.domain.demo import seed, analyze_seeded
from packages.domain.demo_stages import drain, seed_stages, seed_sandbox_plans
from test_document_pipeline import Engine


class OperationMatrixTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        with patch.object(settings, "mode", "demo"):
            seed()
            drain()
            analyze_seeded()
            drain()
            seed_sandbox_plans()
            seed_stages()

    def test_every_protected_operation_enforces_current_membership_roles(self):
        with store.engine.connect() as conn:
            tx = conn.begin()
            try:
                identity = auth.bootstrap(
                    conn,
                    store.uid("matrix") + "@example.test",
                    "matrix-test-password",
                    "Matrix Reviewer",
                    "Matrix Organization",
                )
                user = (
                    conn.execute(
                        sa.select(store.users).where(
                            store.users.c.id == identity["user_id"]
                        )
                    )
                    .mappings()
                    .one()
                )
                token = auth.create_session(conn, user)["access_token"]
                request = Request(
                    {
                        "type": "http",
                        "headers": [(b"authorization", ("Bearer " + token).encode())],
                    }
                )
                exemptions = {
                    "getSession",
                    "logout",
                    "selectOrganization",
                    "createOrganization",
                }
                for role in [
                    "owner",
                    "export_admin",
                    "finance_reviewer",
                    "production_procurement",
                ]:
                    conn.execute(
                        store.memberships.update()
                        .where(store.memberships.c.user_id == identity["user_id"])
                        .values(roles=[role])
                    )
                    for operation, (_, _, definition) in OPERATIONS.items():
                        if definition["x-public-auth"]:
                            continue
                        allowed = (
                            operation in exemptions
                            or not definition["x-required-roles"]
                            or role in definition["x-required-roles"]
                        )
                        with self.subTest(operation=operation, role=role):
                            if allowed:
                                self.assertEqual(
                                    context_for(conn, request, operation, "matrix")[
                                        "roles"
                                    ],
                                    [role],
                                )
                            else:
                                with self.assertRaises(store.DomainError) as error:
                                    context_for(conn, request, operation, "matrix")
                                self.assertEqual(error.exception.status, 403)
            finally:
                tx.rollback()

    def test_every_read_route_has_canonical_success_or_owned_missing_resource_error(
        self,
    ):
        with patch.object(settings, "mode", "demo"), store.engine.connect() as conn:
            tx = conn.begin()
            try:
                token = auth.demo_login(conn, "demo_id_owner")["access_token"]
                headers = {"Authorization": "Bearer " + token}
                workspace = store.get(
                    conn, "demo_org_id", "workspace", "demo_stage_closed"
                )
                deal = store.get(conn, "demo_org_id", "deal", workspace["deal_id"])
                foreign = auth.bootstrap(
                    conn,
                    store.uid("foreign") + "@example.test",
                    "matrix-foreign-password",
                    "Other Owner",
                    "Other Tenant",
                )
                foreign_user = (
                    conn.execute(
                        sa.select(store.users).where(
                            store.users.c.id == foreign["user_id"]
                        )
                    )
                    .mappings()
                    .one()
                )
                foreign_token = auth.create_session(conn, foreign_user)["access_token"]
                with (
                    patch.object(store, "engine", Engine(conn)),
                    TestClient(app) as client,
                ):
                    self.populate_read_families(conn, client, headers)
                    for operation, (path, method, definition) in OPERATIONS.items():
                        if method != "get":
                            continue
                        values = {
                            "id": deal["id"] if "/deals/" in path else workspace["id"],
                            "resource_id": "missing_owned_resource",
                            "revision": "1",
                        }
                        if "/organizations/" in path:
                            values["id"] = "demo_org_id"
                        if "/runs/" in path:
                            rows = commands.all_records(conn, "demo_org_id", "run")
                            values["id"] = (
                                rows[0]["id"] if rows else "missing_owned_run"
                            )
                        if operation == "getInputRevision":
                            values["id"] = deal["id"]
                            values["revision"] = str(deal["revision"])
                        if "{resource_id}" in path:
                            parts = path.split("/")
                            segment = parts[parts.index("{resource_id}") - 1]
                            kind = (
                                "finance_options"
                                if operation == "getFinanceOptions"
                                else SEGMENTS[segment]
                            )
                            for candidate in commands.all_records(
                                conn, "demo_org_id", kind
                            ):
                                parent_id = conn.execute(
                                    sa.select(store.records[kind].c.parent_id).where(
                                        store.records[kind].c.tenant_id
                                        == "demo_org_id",
                                        store.records[kind].c.id == candidate["id"],
                                    )
                                ).scalar_one()
                                parent_registry = conn.execute(
                                    sa.select(store.registry.c.kind).where(
                                        store.registry.c.tenant_id == "demo_org_id",
                                        store.registry.c.id == parent_id,
                                    )
                                ).scalar_one_or_none()
                                if (
                                    "/workspaces/" in path
                                    and parent_registry == "workspace"
                                ):
                                    values.update(
                                        id=parent_id, resource_id=candidate["id"]
                                    )
                                    break
                                if "/deals/" in path and parent_registry == "deal":
                                    values.update(
                                        id=parent_id, resource_id=candidate["id"]
                                    )
                                    break
                                if "/deals/" in path and parent_registry == "workspace":
                                    linked = store.get(
                                        conn, "demo_org_id", "workspace", parent_id
                                    ).get("deal_id")
                                    if linked:
                                        values.update(
                                            id=linked, resource_id=candidate["id"]
                                        )
                                        break
                        concrete = re.sub(
                            r"\{([^}]+)\}", lambda match: values[match[1]], path
                        )
                        with self.subTest(operation=operation):
                            result = client.get(
                                concrete,
                                params={"stage": "shipment", "limit": 100},
                                headers=headers,
                            )
                            self.assertIn(
                                result.status_code, {200, 404}, result.text[:300]
                            )
                            if "{id}" in path:
                                isolated = client.get(
                                    concrete,
                                    params={"stage": "shipment", "limit": 100},
                                    headers={
                                        "Authorization": "Bearer " + foreign_token
                                    },
                                )
                                self.assertEqual(
                                    isolated.status_code, 404, isolated.text[:300]
                                )
                            denied = client.get(
                                concrete, params={"stage": "shipment", "limit": 100}
                            )
                            self.assertEqual(
                                denied.status_code,
                                200 if definition["x-public-auth"] else 401,
                                denied.text[:300],
                            )
            finally:
                tx.rollback()

    def populate_read_families(self, conn, client, headers):
        from services.worker.jobs import process
        from packages.domain.artifacts import render
        from packages.contracts.runtime import validate_response

        tenant = "demo_org_id"
        workspace = store.get(conn, tenant, "workspace", "demo_id-reseller_deal")
        root = "/v2/deals/" + workspace["deal_id"]

        def current():
            return client.get(root, headers=headers).json()["result"]["deal"]

        def post(suffix, body):
            result = client.post(
                root + suffix,
                json={"expected_revision": current()["revision"], **body},
                headers={**headers, "Idempotency-Key": store.uid("matrix")},
            )
            self.assertIn(result.status_code, {200, 201, 202}, result.text[:500])
            return result.json()["result"]

        def process_job(accepted):
            identifier = accepted["run"]["id"]
            row = dict(
                conn.execute(sa.select(store.jobs).where(store.jobs.c.id == identifier))
                .mappings()
                .one()
            )
            conn.execute(
                store.jobs.update()
                .where(store.jobs.c.id == identifier)
                .values(state="running", attempts=1)
            )
            result = process(row)
            self.assertIn(
                result["status"], {"succeeded", "partial"}, result.get("blockers")
            )
            return result

        deal = current()
        source = commands.children(conn, tenant, "evidence", deal)[0]["id"]
        seller = next(row["id"] for row in deal["parties"] if "seller" in row["roles"])
        process_job(
            post(
                "/analyses",
                {"scenario_id": None, "scope": "full", "execution": "deterministic"},
            )
        )
        analysis = commands.children(conn, tenant, "analysis", current())[-1]
        process_job(
            post(
                "/finance-options",
                {
                    "analysis_id": analysis["id"],
                    "company": {
                        "seller_party_id": seller,
                        "registration_evidence_ids": [],
                        "financial_evidence_ids": [],
                        "unknowns": [],
                    },
                    "requested_amount": None,
                    "required_by": None,
                },
            )
        )
        option = commands.children(conn, tenant, "funding_option", current())[-1]
        scenario = post(
            "/scenarios",
            {
                "base_revision": {"id": deal["id"], "revision": current()["revision"]},
                "patches": [],
                "funding_option_ids": [option["id"]],
            },
        )
        process_job(scenario["job"])
        scenario_id = scenario["scenario"]["id"]
        process_job(
            post(
                "/finance-packs",
                {
                    "funding_option_id": option["id"],
                    "scenario_id": scenario_id,
                    "evidence_ids": [source],
                },
            )
        )
        post(
            "/milestones",
            {
                "milestone_id": None,
                "kind": "arrival",
                "schedule": {
                    "kind": "fixed",
                    "due": {"date": "2026-12-10", "timezone": "Asia/Jakarta"},
                },
                "date_kind": "forecast",
                "value": {"date": "2026-12-10", "timezone": "Asia/Jakarta"},
                "evidence_ids": [source],
            },
        )
        fx = post(
            "/fx-observations",
            {
                "observation": {
                    "base_currency": "USD",
                    "quote_currency": "IDR",
                    "rate": "16000",
                    "as_of": "2026-10-16T12:00:00Z",
                    "evidence_ids": [source],
                    "mode": "synthetic_demo",
                }
            },
        )
        sandbox = store.get(conn, tenant, "workspace", "demo_id-reseller_sandbox")
        hypothetical = {**sandbox, **deepcopy(sandbox["planning_inputs"])}
        sandbox_source = commands.children(conn, tenant, "evidence", sandbox)[0]["id"]
        context = {"tenant": tenant, "actor": "demo_id_owner"}
        # Imported/retained sandbox output families use their normal storage and
        # template services; these interfaces are intentionally read-only.
        for row in commands.procurement_costs(context, hypothetical):
            store.save(
                conn, tenant, "cost_line", row, parent=sandbox["id"], dataset="demo-v1"
            )
        sandbox_fx = {
            **fx,
            **store.meta(tenant, "demo_id_owner", "fx_observation"),
            "evidence_ids": [sandbox_source],
        }
        store.save(
            conn,
            tenant,
            "fx_observation",
            sandbox_fx,
            parent=sandbox["id"],
            dataset="demo-v1",
        )
        sandbox_analysis = commands.children(conn, tenant, "analysis", sandbox)[-1]
        sandbox_scenario = store.get(
            conn, tenant, "scenario", sandbox_analysis["scenario_id"]
        )
        content, placeholders = render(
            hypothetical, sandbox_scenario, sandbox_analysis, "recommendation", "id"
        )
        artifact = {
            **store.meta(tenant, "demo_id_owner", "artifact"),
            "kind": "recommendation",
            "scenario_id": sandbox_scenario["id"],
            "analysis_id": sandbox_analysis["id"],
            "template_version": "controlled-id-1",
            "content_hash": store.digest(content),
            "content": content,
            "media_type": "text/markdown",
            "placeholders": placeholders,
            "state": "draft",
        }
        store.save(
            conn, tenant, "artifact", artifact, parent=sandbox["id"], dataset="demo-v1"
        )
        from operation_actions import exercise

        exercise(self, conn, client, headers, current(), sandbox, source)
