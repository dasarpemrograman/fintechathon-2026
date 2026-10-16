from copy import deepcopy
from unittest.mock import patch
import unittest
import sqlalchemy as sa
from services.api import auth, commands, store
from services.api.settings import settings
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
        self.assertNotIn("attendees", google_event(events[0], "id", "owner"))
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
