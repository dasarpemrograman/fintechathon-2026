from contextlib import contextmanager
from unittest.mock import patch
from datetime import timedelta
import json, unittest
import httpx
import sqlalchemy as sa
from services.api import store, auth
from services.api.secrets import cipher
from packages.adapters.calendar import deliver_once
from migrations.schema_v3 import connector_credentials, calendar_events


class Engine:
    def __init__(self, conn):
        self.conn = conn

    @contextmanager
    def begin(self):
        with self.conn.begin_nested():
            yield self.conn


class CalendarOutboxTests(unittest.TestCase):
    def setUp(self):
        self.acceptance = patch.dict(
            "os.environ",
            {
                "ALLEXPORT_CALENDAR_LIVE_ENABLED": "true",
                "ALLEXPORT_CALENDAR_ACCEPTANCE_REFERENCE": "synthetic-adapter-test-only",
                "GOOGLE_CLIENT_ID": "test-client",
                "GOOGLE_CLIENT_SECRET": "test-client-secret",
                "GOOGLE_REDIRECT_URI": "http://127.0.0.1:3000/oauth/calendar/callback",
            },
        )
        self.acceptance.start()
        self.addCleanup(self.acceptance.stop)
        self.conn = store.engine.connect()
        self.tx = self.conn.begin()
        identity = auth.bootstrap(
            self.conn,
            store.uid("outbox") + "@example.test",
            "outbox-test-password",
            "Owner",
            "Outbox Test",
        )
        self.tenant = identity["organization_id"]
        self.actor = identity["user_id"]
        self.connection = {
            **store.meta(self.tenant, self.actor, "calendar_connection"),
            "provider": "google",
            "calendar_id": "test-owned",
            "status": "connected",
            "data_mode": "live",
        }
        store.save(self.conn, self.tenant, "calendar_connection", self.connection)
        self.conn.execute(
            connector_credentials.insert().values(
                tenant_id=self.tenant,
                connection_id=self.connection["id"],
                ciphertext=cipher()
                .encrypt(
                    json.dumps(
                        {
                            "access_token": "synthetic-provider-test-token",
                            "expires_at": "2099-01-01T00:00:00+00:00",
                        }
                    ).encode()
                )
                .decode(),
            )
        )

    def tearDown(self):
        self.tx.rollback()
        self.conn.close()

    def enqueue(self, action="insert", key=None):
        event = {
            "milestone_id": "milestone_owned",
            "title": "Arrival forecast",
            "date": {"date": "2026-11-01", "timezone": "Asia/Jakarta"},
            "action": action,
        }
        identifier = store.uid("effect")
        payload = {
            "tenant_id": self.tenant,
            "connection_id": self.connection["id"],
            "deal_id": "test_deal",
            "projection_hash": "a" * 64,
            "event": event,
        }
        self.conn.execute(
            store.outbox.insert().values(
                tenant_id=self.tenant,
                id=identifier,
                effect_key=key or identifier,
                payload=payload,
                state="pending",
            )
        )
        return identifier

    def test_disabled_acceptance_blocks_admission_processing_and_queued_delivery(self):
        from types import SimpleNamespace
        from services.api.job_handlers import accept_job
        from services.api.handlers import read_operation
        from services.api.settings import settings
        from packages.adapters.calendar import process_calendar
        from migrations.schema_v3 import calendar_events

        identifier = self.enqueue()
        context = {
            "tenant": self.tenant,
            "actor": self.actor,
            "scope": "real",
            "request_id": "gate-check",
        }
        with (
            patch.dict("os.environ", {"ALLEXPORT_CALENDAR_LIVE_ENABLED": "false"}),
            patch.object(settings, "mode", "normal"),
            patch("packages.adapters.calendar.httpx.Client") as provider,
        ):
            for action in [
                lambda: accept_job(
                    self.conn,
                    context,
                    "syncCalendar",
                    {"execution_scope": "real"},
                    {"connection_id": self.connection["id"]},
                ),
                lambda: process_calendar(
                    SimpleNamespace(
                        conn=self.conn,
                        tenant=self.tenant,
                        actor=self.actor,
                        body={"connection_id": self.connection["id"]},
                        parent={},
                    )
                ),
            ]:
                with self.assertRaises(store.DomainError) as error:
                    action()
                self.assertEqual(error.exception.code, "CALENDAR_LIVE_DISABLED")
            capabilities = read_operation(
                self.conn,
                context,
                "getCapabilities",
                None,
                SimpleNamespace(path_params={}),
            )
            self.assertEqual(capabilities["result"]["items"][-1]["state"], "blocked")
            with patch.object(store, "engine", Engine(self.conn)):
                result = deliver_once()
            self.assertEqual(result["failure_code"], "CALENDAR_LIVE_DISABLED")
            provider.assert_not_called()
            row = (
                self.conn.execute(
                    sa.select(store.outbox).where(store.outbox.c.id == identifier)
                )
                .mappings()
                .one()
            )
            self.assertEqual(row["state"], "failed")
            self.assertFalse(row["receipt"]["delivered"])
            self.assertIsNone(
                self.conn.execute(
                    sa.select(calendar_events).where(
                        calendar_events.c.connection_id == self.connection["id"]
                    )
                ).first()
            )

    def test_operator_enablement_requires_acceptance_reference_and_credentials(self):
        from packages.adapters.calendar_policy import live_sync_ready

        self.assertTrue(live_sync_ready())
        for name in [
            "ALLEXPORT_CALENDAR_ACCEPTANCE_REFERENCE",
            "GOOGLE_CLIENT_ID",
            "GOOGLE_CLIENT_SECRET",
            "GOOGLE_REDIRECT_URI",
        ]:
            with self.subTest(missing=name), patch.dict("os.environ", {name: ""}):
                self.assertFalse(live_sync_ready())

    def test_demo_runtime_refuses_live_outbox_even_when_operator_enabled(self):
        from services.api.settings import settings

        self.enqueue()
        with (
            patch.object(settings, "mode", "demo"),
            patch.object(store, "engine", Engine(self.conn)),
            patch("packages.adapters.calendar.httpx.Client") as provider,
        ):
            result = deliver_once()
            self.assertEqual(result["failure_code"], "DEMO_CALENDAR_ONLY")
            self.assertFalse(result["delivered"])
            provider.assert_not_called()

    def test_crash_after_insert_reuses_provider_id_and_records_one_external_event(self):
        identifier = self.enqueue()
        external = {}
        posts = []
        real_client = httpx.Client

        def handle(request):
            if request.method == "POST":
                payload = json.loads(request.content)
                posts.append(payload["id"])
                self.assertNotIn("attendees", payload)
                self.assertEqual(request.url.params.get("sendUpdates"), "none")
                if payload["id"] in external:
                    return httpx.Response(409)
                external[payload["id"]] = {**payload, "etag": '"e1"'}
                raise httpx.ReadError("simulated response lost after external insert")
            return httpx.Response(
                200, headers={"etag": '"e1"'}, json=next(iter(external.values()))
            )

        with (
            patch.object(store, "engine", Engine(self.conn)),
            patch(
                "packages.adapters.calendar.httpx.Client",
                side_effect=lambda **kw: real_client(
                    transport=httpx.MockTransport(handle)
                ),
            ),
        ):
            failed = deliver_once()
            self.assertFalse(failed["delivered"])
            self.conn.execute(
                store.outbox.update()
                .where(store.outbox.c.id == identifier)
                .values(available_at=store.now() - timedelta(seconds=1))
            )
            receipt = deliver_once()
            self.assertTrue(receipt["delivered"])
            self.assertIsNone(deliver_once())
        self.assertEqual(len(external), 1)
        self.assertEqual(len(posts), 2)
        self.assertEqual(posts[0], posts[1])
        row = (
            self.conn.execute(
                sa.select(store.outbox).where(store.outbox.c.id == identifier)
            )
            .mappings()
            .one()
        )
        self.assertEqual(row["state"], "delivered")
        self.assertEqual(row["attempts"], 2)
        self.assertEqual(
            row["receipt"]["acceptance_reference"], "synthetic-adapter-test-only"
        )

    def test_external_edit_conflicts_and_nonowned_delete_fails(self):
        identifier = self.enqueue("delete")
        real_client = httpx.Client
        with (
            patch.object(store, "engine", Engine(self.conn)),
            patch("packages.adapters.calendar.httpx.Client") as client,
        ):
            result = deliver_once()
            self.assertFalse(result["delivered"])
            self.assertEqual(result["failure_code"], "CALENDAR_EVENT_NOT_OWNED")
            client.assert_not_called()
        self.conn.execute(
            calendar_events.insert().values(
                tenant_id=self.tenant,
                connection_id=self.connection["id"],
                milestone_id="milestone_owned",
                provider_id=store.digest(
                    {
                        "tenant": self.tenant,
                        "connection": self.connection["id"],
                        "milestone": "milestone_owned",
                    }
                ),
                etag='"e1"',
                projection_hash="a" * 64,
                state="delivered",
                provider_data={},
            )
        )
        self.enqueue("update")

        def edited(request):
            if request.method == "PATCH":
                self.assertEqual(request.headers["if-match"], '"e1"')
                return httpx.Response(412)
            return httpx.Response(
                200, json={"summary": "Externally edited", "etag": '"e2"'}
            )

        with (
            patch.object(store, "engine", Engine(self.conn)),
            patch(
                "packages.adapters.calendar.httpx.Client",
                side_effect=lambda **kw: real_client(
                    transport=httpx.MockTransport(edited)
                ),
            ),
        ):
            self.assertFalse(deliver_once()["delivered"])
        self.assertEqual(
            self.conn.execute(
                sa.select(calendar_events.c.state).where(
                    calendar_events.c.tenant_id == self.tenant
                )
            ).scalar_one(),
            "conflict",
        )

    def test_provider_outage_stops_after_three_attempts_and_never_reports_delivery(
        self,
    ):
        identifier = self.enqueue()
        real_client = httpx.Client
        with (
            patch.object(store, "engine", Engine(self.conn)),
            patch(
                "packages.adapters.calendar.httpx.Client",
                side_effect=lambda **kw: real_client(
                    transport=httpx.MockTransport(lambda r: httpx.Response(503))
                ),
            ),
        ):
            for index in range(3):
                result = deliver_once()
                self.assertFalse(result["delivered"])
                self.conn.execute(
                    store.outbox.update()
                    .where(store.outbox.c.id == identifier)
                    .values(available_at=store.now() - timedelta(seconds=1))
                )
            self.assertEqual(result["status"], "failed")
            self.assertIsNone(deliver_once())

    def test_expired_tokens_refresh_once_and_remain_encrypted(self):
        from packages.adapters.calendar import access_token

        tokens = {
            "access_token": "expired-fixture-token",
            "refresh_token": "fixture-refresh-secret",
            "expires_at": "2000-01-01T00:00:00+00:00",
        }
        self.conn.execute(
            connector_credentials.update()
            .where(connector_credentials.c.connection_id == self.connection["id"])
            .values(ciphertext=cipher().encrypt(json.dumps(tokens).encode()).decode())
        )
        calls = []
        real_client = httpx.Client

        def handle(request):
            calls.append(request)
            self.assertEqual(request.url.host, "oauth2.googleapis.com")
            self.assertIn("grant_type=refresh_token", request.content.decode())
            return httpx.Response(
                200, json={"access_token": "new-fixture-token", "expires_in": 3600}
            )

        with (
            patch.dict(
                "os.environ",
                {
                    "GOOGLE_CLIENT_ID": "test-client",
                    "GOOGLE_CLIENT_SECRET": "test-client-secret",
                },
            ),
            patch(
                "packages.adapters.calendar.httpx.Client",
                side_effect=lambda **kw: real_client(
                    transport=httpx.MockTransport(handle)
                ),
            ),
        ):
            self.assertEqual(
                access_token(self.conn, self.tenant, self.connection["id"]),
                "new-fixture-token",
            )
            self.assertEqual(
                access_token(self.conn, self.tenant, self.connection["id"]),
                "new-fixture-token",
            )
        self.assertEqual(len(calls), 1)
        encrypted = self.conn.execute(
            sa.select(connector_credentials.c.ciphertext).where(
                connector_credentials.c.connection_id == self.connection["id"]
            )
        ).scalar_one()
        self.assertNotIn("fixture", encrypted)
        self.assertEqual(
            json.loads(cipher().decrypt(encrypted.encode()))["refresh_token"],
            "fixture-refresh-secret",
        )

    def test_remote_revocation_outage_still_removes_local_access(self):
        from packages.adapters.calendar import calendar_command
        from types import SimpleNamespace

        real_client = httpx.Client
        with patch(
            "packages.adapters.calendar.httpx.Client",
            side_effect=lambda **kw: real_client(
                transport=httpx.MockTransport(lambda request: httpx.Response(503))
            ),
        ):
            response = calendar_command(
                self.conn,
                {
                    "tenant": self.tenant,
                    "actor": self.actor,
                    "request_id": store.uid("request"),
                },
                "revokeCalendar",
                None,
                {},
                SimpleNamespace(path_params={"id": self.connection["id"]}),
            )
        self.assertEqual(response["result"]["status"], "revoked")
        self.assertEqual(
            response["warnings"][0]["code"], "REMOTE_REVOCATION_UNCONFIRMED"
        )
        self.assertIsNone(
            self.conn.execute(
                sa.select(connector_credentials.c.ciphertext).where(
                    connector_credentials.c.connection_id == self.connection["id"]
                )
            ).scalar_one_or_none()
        )
