from copy import deepcopy
from unittest.mock import patch
import unittest
import sqlalchemy as sa
import httpx
import json
from urllib.parse import urlsplit, parse_qs
from services.api import auth, commands, store
from services.api.settings import settings
from services.api.secrets import cipher
from packages.adapters.calendar import (
    calendar_command,
    projection,
    google_event,
    deliver_once,
)
from migrations.schema_v3 import oauth_states, connector_credentials, calendar_events


class Request:
    def __init__(self, id):
        self.path_params = {"id": id}


class CalendarTests(unittest.TestCase):
    def test_provider_timezone_normalization_preserves_retry_identity(self):
        from packages.adapters.calendar import event_matches

        event = {
            "title": "Acceptance milestone",
            "date": {"instant": "2026-10-19T03:00:00Z", "timezone": "Asia/Jakarta"},
        }
        expected = google_event(event, "id", "owner")
        remote = deepcopy(expected)
        remote["start"]["dateTime"] = "2026-10-19T10:00:00+07:00"
        remote["end"]["dateTime"] = "2026-10-19T10:15:00+07:00"
        self.assertTrue(event_matches(remote, expected))
        changed = deepcopy(remote)
        changed["start"]["dateTime"] = "2026-10-19T11:00:00+07:00"
        self.assertFalse(event_matches(changed, expected))
        changed = deepcopy(remote)
        changed["reminders"] = {"useDefault": True}
        self.assertFalse(event_matches(changed, expected))
        all_day = google_event(
            {"title": "Acceptance milestone", "date": {"date": "2026-10-19", "timezone": "Asia/Jakarta"}},
            "id", "owner",
        )
        self.assertFalse(event_matches(remote, all_day))

    def setUp(self):
        self.conn = store.engine.connect()
        self.tx = self.conn.begin()
        identity = auth.bootstrap(
            self.conn,
            store.uid("cal") + "@example.test",
            "calendar-test-password",
            "Owner",
            "Calendar Test",
        )
        self.context = {
            "tenant": identity["organization_id"],
            "actor": identity["user_id"],
            "roles": ["owner"],
            "request_id": store.uid("request"),
            "scope": "demo",
            "dataset": None,
        }
        self.mode = patch.object(settings, "mode", "demo")
        self.mode.start()

    def tearDown(self):
        self.tx.rollback()
        self.conn.close()
        self.mode.stop()

    def connect(self):
        authorization = calendar_command(
            self.conn,
            self.context,
            "connectCalendar",
            None,
            {"redirect_uri": "http://localhost:3000/calendar/callback"},
        )["result"]
        row = calendar_command(
            self.conn,
            self.context,
            "calendarCallback",
            None,
            {"state": authorization["state"], "code": "offline-demo"},
        )["result"]
        calendar_command(
            self.conn,
            self.context,
            "selectCalendar",
            None,
            {"calendar_id": "synthetic-local"},
            Request(row["id"]),
        )
        return authorization, row

    def test_live_oauth_uses_exact_redirect_and_consumes_actor_bound_state(self):
        redirect = "http://127.0.0.1:3000/oauth/calendar/callback"
        variables = {
            "GOOGLE_CLIENT_ID": "test-client",
            "GOOGLE_CLIENT_SECRET": "test-secret",
            "GOOGLE_REDIRECT_URI": redirect,
        }
        real_client = httpx.Client
        exchanges = []

        def respond(request):
            exchanges.append(parse_qs(request.content.decode()))
            self.assertEqual(str(request.url), "https://oauth2.googleapis.com/token")
            return httpx.Response(
                200,
                json={
                    "access_token": "synthetic-live-test-token",
                    "refresh_token": "synthetic-refresh",
                    "expires_in": 3600,
                },
            )

        with (
            patch.object(settings, "mode", "normal"),
            patch.dict("os.environ", variables),
            patch(
                "packages.adapters.calendar.httpx.Client",
                side_effect=lambda **kw: real_client(
                    transport=httpx.MockTransport(respond)
                ),
            ),
        ):
            with self.assertRaises(store.DomainError):
                calendar_command(
                    self.conn,
                    self.context,
                    "connectCalendar",
                    None,
                    {"redirect_uri": redirect.replace("127.0.0.1", "localhost")},
                )
            authorization = calendar_command(
                self.conn,
                self.context,
                "connectCalendar",
                None,
                {"redirect_uri": redirect},
            )["result"]
            url = urlsplit(authorization["authorization_url"])
            self.assertEqual(url.netloc, "accounts.google.com")
            query = parse_qs(url.query)
            self.assertEqual(query["redirect_uri"], [redirect])
            self.assertEqual(
                query["scope"],
                ["https://www.googleapis.com/auth/calendar.events.owned"],
            )
            body = {"state": authorization["state"], "code": "synthetic-one-use-code"}
            for context in [
                {**self.context, "actor": "another-actor"},
                {**self.context, "tenant": "another-tenant"},
            ]:
                with self.assertRaises(store.DomainError) as error:
                    calendar_command(self.conn, context, "calendarCallback", None, body)
                self.assertEqual(error.exception.code, "OAUTH_STATE_INVALID")
            self.assertFalse(exchanges)
            connection = calendar_command(
                self.conn, self.context, "calendarCallback", None, body
            )["result"]
            self.assertEqual(connection["status"], "connected")
            self.assertEqual(connection["data_mode"], "live")
            self.assertIsNone(connection["calendar_id"])
            self.assertEqual(exchanges[0]["redirect_uri"], [redirect])
            with self.assertRaises(store.DomainError) as error:
                calendar_command(
                    self.conn, self.context, "calendarCallback", None, body
                )
            self.assertEqual(error.exception.code, "OAUTH_STATE_INVALID")
            self.assertEqual(len(exchanges), 1)
            encrypted = self.conn.execute(
                sa.select(connector_credentials.c.ciphertext).where(
                    connector_credentials.c.connection_id == connection["id"]
                )
            ).scalar_one()
            self.assertNotIn("synthetic-live-test-token", encrypted)
            self.assertIn(
                "expires_at", json.loads(cipher().decrypt(encrypted.encode()))
            )

    def test_offline_connection_single_use_state_encryption_selection_and_revoke(self):
        authorization, row = self.connect()
        with self.assertRaises(store.DomainError):
            calendar_command(
                self.conn,
                self.context,
                "calendarCallback",
                None,
                {"state": authorization["state"], "code": "offline-demo"},
            )
        encrypted = self.conn.execute(
            sa.select(connector_credentials.c.ciphertext).where(
                connector_credentials.c.connection_id == row["id"]
            )
        ).scalar_one()
        self.assertNotIn("fixture", encrypted)
        calendar_command(
            self.conn, self.context, "revokeCalendar", None, {}, Request(row["id"])
        )
        self.assertIsNone(
            self.conn.execute(
                sa.select(connector_credentials.c.ciphertext).where(
                    connector_credentials.c.connection_id == row["id"]
                )
            ).scalar_one_or_none()
        )

    def test_projection_hash_detects_date_selection_and_action_changes(self):
        _, connection = self.connect()
        tenant = self.context["tenant"]
        actor = self.context["actor"]
        parent = {
            **store.meta(tenant, actor, "deal"),
            "workspace_id": "workspace_test",
            "revision": 1,
            "execution_scope": "demo",
            "dataset_id": None,
            "reporting_currency": "EUR",
        }
        store.save(self.conn, tenant, "deal", parent)
        milestone = {
            **store.meta(tenant, actor, "milestone"),
            "kind": "arrival",
            "actual": None,
            "forecast": {"date": "2026-11-01", "timezone": "Asia/Jakarta"},
            "agreed": None,
            "proposed": None,
        }
        store.save(self.conn, tenant, "milestone", milestone, parent=parent["id"])
        body = {
            "connection_id": connection["id"],
            "milestone_ids": [milestone["id"]],
            "action": "insert",
        }
        events, first = projection(self.conn, self.context, parent, body)
        self.assertEqual(events[0]["date"]["date"], "2026-11-01")
        outgoing = google_event(events[0], "id", "owner")
        self.assertNotIn("attendees", outgoing)
        self.assertNotIn("conferenceData", outgoing)
        self.assertEqual(outgoing["visibility"], "private")
        self.assertEqual(outgoing["transparency"], "transparent")
        self.assertEqual(outgoing["reminders"], {"useDefault": False})
        _, second = projection(
            self.conn, self.context, parent, {**body, "action": "delete"}
        )
        self.assertNotEqual(first, second)
        milestone["forecast"]["date"] = "2026-11-02"
        store.save(self.conn, tenant, "milestone", milestone, parent=parent["id"])
        self.assertNotEqual(first, projection(self.conn, self.context, parent, body)[1])

    def test_disabled_connection_does_not_fake_success(self):
        with (
            patch.object(settings, "mode", "normal"),
            patch.dict("os.environ", {}, clear=True),
        ):
            with self.assertRaises(store.DomainError) as e:
                calendar_command(
                    self.conn,
                    self.context,
                    "connectCalendar",
                    None,
                    {"redirect_uri": "http://localhost:3000/callback"},
                )
            self.assertEqual(e.exception.code, "CALENDAR_DISABLED")

    def test_revocation_consumes_pending_authorization_states(self):
        authorization = calendar_command(
            self.conn,
            self.context,
            "connectCalendar",
            None,
            {"redirect_uri": "https://app.example.test/calendar/callback"},
        )["result"]
        pending = (
            self.conn.execute(
                sa.select(oauth_states).where(
                    oauth_states.c.state == authorization["state"]
                )
            )
            .mappings()
            .one()
        )
        calendar_command(
            self.conn,
            self.context,
            "revokeCalendar",
            None,
            {},
            Request(pending["connection_id"]),
        )
        with self.assertRaises(store.DomainError) as caught:
            calendar_command(
                self.conn,
                self.context,
                "calendarCallback",
                None,
                {"state": authorization["state"], "code": "offline-demo"},
            )
        self.assertEqual(caught.exception.code, "OAUTH_STATE_INVALID")

    def test_changed_milestone_cannot_reuse_preview_approval(self):
        from services.api.review_handlers import execute_review

        _, connection = self.connect()
        tenant = self.context["tenant"]
        actor = self.context["actor"]
        parent = {
            **store.meta(tenant, actor, "deal"),
            "workspace_id": "test_workspace",
            "revision": 1,
            "execution_scope": "demo",
            "dataset_id": None,
            "reporting_currency": "EUR",
            "product": {"description": "Private commercial description"},
        }
        store.save(self.conn, tenant, "deal", parent)
        milestone = {
            **store.meta(tenant, actor, "milestone"),
            "kind": "arrival",
            "actual": None,
            "forecast": {"date": "2026-11-01", "timezone": "Asia/Jakarta"},
            "agreed": None,
            "proposed": None,
        }
        store.save(self.conn, tenant, "milestone", milestone, parent=parent["id"])
        preview = calendar_command(
            self.conn,
            self.context,
            "previewCalendar",
            parent,
            {
                "connection_id": connection["id"],
                "milestone_ids": [milestone["id"]],
                "action": "insert",
            },
        )["result"]
        self.assertNotIn("Private commercial", str(preview["events"]))
        milestone["forecast"]["date"] = "2026-11-02"
        store.save(self.conn, tenant, "milestone", milestone, parent=parent["id"])
        with self.assertRaises(store.DomainError) as caught:
            execute_review(
                self.conn,
                self.context,
                "recordApproval",
                parent,
                {
                    "purpose": "calendar_write",
                    "analysis_hash": preview["projection_hash"],
                    "artifact_hash": None,
                    "evidence_digest": preview["projection_hash"],
                    "decision": "approved",
                },
            )
        self.assertEqual(caught.exception.code, "STALE_CALENDAR_APPROVAL")
