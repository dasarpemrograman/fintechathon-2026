from copy import deepcopy
from unittest.mock import patch
import importlib
import unittest
import sqlalchemy as sa
from fastapi.testclient import TestClient
from services.api import store, auth
from services.api.app import app
from migrations.schema_v2 import auth_commands


class HttpFoundationTests(unittest.TestCase):
    def setUp(self):
        self.email = store.uid("http") + "@example.test"
        self.password = "synthetic-http-test-password"
        with store.engine.begin() as conn:
            self.identity = auth.bootstrap(
                conn, self.email, self.password, "HTTP Owner", "HTTP Test Organization"
            )
        self.client = TestClient(app)
        response = self.client.post(
            "/v2/auth/login",
            json={"email": self.email, "password": self.password},
            headers={"Idempotency-Key": store.uid("login")},
        )
        self.assertEqual(response.status_code, 200, response.text)
        self.headers = {
            "Authorization": "Bearer " + response.json()["result"]["access_token"]
        }

    def tearDown(self):
        tenant = self.identity["organization_id"]
        user = self.identity["user_id"]
        with store.engine.begin() as conn:
            for table in [
                store.commands,
                store.snapshots,
                store.references,
                store.jobs,
                store.outbox,
                store.cash,
            ]:
                conn.execute(table.delete().where(table.c.tenant_id == tenant))
            for table in store.records.values():
                conn.execute(table.delete().where(table.c.tenant_id == tenant))
            conn.execute(
                store.registry.delete().where(store.registry.c.tenant_id == tenant)
            )
            conn.execute(
                store.sessions.delete().where(store.sessions.c.user_id == user)
            )
            conn.execute(
                store.memberships.delete().where(store.memberships.c.user_id == user)
            )
            conn.execute(auth_commands.delete().where(auth_commands.c.actor_id == user))
            conn.execute(
                store.organizations.delete().where(store.organizations.c.id == tenant)
            )
            conn.execute(store.users.delete().where(store.users.c.id == user))

    def body(self):
        return {
            "mode": "sandbox",
            "business_profile": "producer",
            "reporting_currency": "EUR",
            "owner_timezone": "Africa/Nairobi",
            "product": {"description": "Dried mango"},
        }

    def test_create_read_replay_conflict_and_tenant_scope(self):
        headers = {**self.headers, "Idempotency-Key": store.uid("workspace")}
        first = self.client.post("/v2/workspaces", json=self.body(), headers=headers)
        self.assertEqual(first.status_code, 201, first.text)
        workspace = first.json()["result"]
        replay = self.client.post("/v2/workspaces", json=self.body(), headers=headers)
        self.assertEqual(replay.json(), first.json())
        conflict = self.client.post(
            "/v2/workspaces",
            json={**self.body(), "business_profile": "reseller"},
            headers=headers,
        )
        self.assertEqual(conflict.status_code, 409)
        listing = self.client.get("/v2/workspaces", headers=self.headers)
        self.assertEqual(listing.status_code, 200, listing.text)
        self.assertEqual(
            [r["id"] for r in listing.json()["result"]["items"]], [workspace["id"]]
        )
        self.assertEqual(
            self.client.get("/v2/workspaces/" + workspace["id"]).status_code, 401
        )
        with store.engine.begin() as conn:
            conn.execute(
                store.sessions.update()
                .where(store.sessions.c.user_id == self.identity["user_id"])
                .values(organization_id=None)
            )
        self.assertEqual(
            self.client.get(
                "/v2/workspaces/" + workspace["id"], headers=self.headers
            ).status_code,
            403,
        )

    def test_invalid_response_is_sanitized_and_transaction_rolled_back(self):
        module = importlib.import_module("services.api.app")
        original = module.write_operation

        def invalid(*args, **kwargs):
            value = original(*args, **kwargs)
            value["result"]["unrecognized_field"] = "must not escape"
            return value

        with patch.object(module, "write_operation", invalid):
            response = self.client.post(
                "/v2/workspaces",
                json=self.body(),
                headers={**self.headers, "Idempotency-Key": store.uid("bad")},
            )
        self.assertEqual(response.status_code, 500)
        self.assertEqual(response.json()["code"], "INTERNAL_ERROR")
        self.assertNotIn("unrecognized", response.text)
        with store.engine.connect() as conn:
            self.assertEqual(
                store.list_records(conn, self.identity["organization_id"], "workspace")[
                    "items"
                ],
                [],
            )

    def test_auth_receipts_are_idempotent_and_encrypted(self):
        headers = {"Idempotency-Key": store.uid("login")}
        body = {"email": self.email, "password": self.password}
        first = self.client.post("/v2/auth/login", json=body, headers=headers)
        second = self.client.post("/v2/auth/login", json=body, headers=headers)
        self.assertEqual(first.status_code, 200, first.text)
        self.assertEqual(first.json(), second.json())
        with store.engine.connect() as conn:
            stored = conn.execute(
                sa.select(auth_commands.c.receipt).where(
                    auth_commands.c.actor_id == self.identity["user_id"],
                    auth_commands.c.key == headers["Idempotency-Key"],
                )
            ).scalar_one()
        self.assertNotIn(first.json()["result"]["access_token"], stored)

    def test_invalid_body_never_becomes_an_authorized_mutation(self):
        response = self.client.post(
            "/v2/workspaces",
            json={**self.body(), "tenant_id": "another"},
            headers={**self.headers, "Idempotency-Key": store.uid("bad")},
        )
        self.assertEqual(response.status_code, 422)

    def test_stale_revision_replay_returns_original_command_receipt(self):
        first = self.client.post(
            "/v2/workspaces",
            json=self.body(),
            headers={**self.headers, "Idempotency-Key": store.uid("create")},
        )
        workspace = first.json()["result"]
        headers = {**self.headers, "Idempotency-Key": store.uid("edit")}
        body = {
            "expected_revision": workspace["revision"],
            "patches": [
                {
                    "op": "replace",
                    "path": "/product",
                    "value": {"description": "Updated mango"},
                    "reason": "Owner revision",
                    "evidence_ids": [],
                    "agreement_required_from": [],
                }
            ],
        }
        path = "/v2/workspaces/" + workspace["id"] + "/facts"
        changed = self.client.patch(path, json=body, headers=headers)
        self.assertEqual(changed.status_code, 200, changed.text)
        self.assertEqual(changed.json()["result"]["revision"], 2)
        replay = self.client.patch(path, json=body, headers=headers)
        self.assertEqual(replay.json(), changed.json())
        stale = self.client.patch(
            path,
            json=body,
            headers={**self.headers, "Idempotency-Key": store.uid("stale")},
        )
        self.assertEqual(stale.status_code, 409)
        body["patches"][0]["value"]["description"] = "Different"
        conflict = self.client.patch(path, json=body, headers=headers)
        self.assertEqual(conflict.status_code, 409)

    def test_demo_entry_cookie_boundary_and_normal_mode_rejection(self):
        from services.api.settings import settings

        with store.engine.begin() as conn:
            conn.execute(
                store.users.update()
                .where(store.users.c.id == self.identity["user_id"])
                .values(dataset_id="isolated_test_demo")
            )
        with patch.object(settings, "mode", "demo"):
            response = self.client.post(
                "/v2/auth/demo-session",
                json={"user_id": self.identity["user_id"]},
                headers={"Idempotency-Key": store.uid("demo")},
            )
            self.assertEqual(response.status_code, 200, response.text)
            bearer = {
                "Authorization": "Bearer " + response.json()["result"]["access_token"]
            }
            self.assertEqual(
                self.client.get("/v2/auth/session", headers=bearer).status_code, 200
            )
        with patch.object(settings, "mode", "normal"):
            self.assertEqual(
                self.client.get("/v2/auth/session", headers=bearer).status_code, 401
            )
            self.assertEqual(
                self.client.post(
                    "/v2/auth/demo-session",
                    json={"user_id": self.identity["user_id"]},
                    headers={"Idempotency-Key": store.uid("demo")},
                ).status_code,
                404,
            )

    def test_diagnostics_are_tenant_scoped_and_admin_only(self):
        response = self.client.get("/v2/diagnostics", headers=self.headers)
        self.assertEqual(response.status_code, 200, response.text)
        result = response.json()["result"]
        self.assertEqual(result["queue"]["queued"], 0)
        self.assertEqual(result["run_issues"], [])
        self.assertEqual(result["stale_analyses"], 0)
        with store.engine.begin() as conn:
            conn.execute(
                store.memberships.update()
                .where(store.memberships.c.user_id == self.identity["user_id"])
                .values(roles=["finance_reviewer"])
            )
        self.assertEqual(
            self.client.get("/v2/diagnostics", headers=self.headers).status_code, 403
        )
