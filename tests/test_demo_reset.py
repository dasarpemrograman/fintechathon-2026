import unittest
from unittest.mock import patch
from packages.domain.demo_reset import reset_dataset
from packages.domain.demo import DATASET
from services.api import store, auth, commands
from services.api.settings import settings


class DemoResetTests(unittest.TestCase):
    def test_namespace_preflight_preserves_unrelated_and_blocks_mixed_ownership(self):
        conn = store.engine.connect()
        tx = conn.begin()
        try:
            identity = auth.bootstrap(
                conn,
                store.uid("reset") + "@example.test",
                "reset-test-only-password",
                "Owner",
                "Reset Test",
            )
            tenant = identity["organization_id"]
            actor = identity["user_id"]
            with patch.object(settings, "mode", "demo"):
                seed = {
                    **store.meta(tenant, actor, "workspace"),
                    "dataset_id": DATASET,
                    "revision": 1,
                }
                store.save(conn, tenant, "workspace", seed, dataset=DATASET)
                unrelated = store.meta(tenant, actor, "evidence")
                store.save(conn, tenant, "evidence", unrelated)
                count = reset_dataset(conn, DATASET)
                self.assertGreater(count, 0)
                nested = conn.begin_nested()
                self.assertEqual(reset_dataset(conn, DATASET, True), count)
                self.assertIsNone(
                    store.get(conn, tenant, "workspace", seed["id"], False)
                )
                self.assertEqual(
                    store.get(conn, tenant, "evidence", unrelated["id"]), unrelated
                )
                nested.rollback()
                mixed = {**store.meta(tenant, actor, "evidence"), "source": seed["id"]}
                store.save(conn, tenant, "evidence", mixed)
                with self.assertRaises(store.DomainError) as error:
                    reset_dataset(conn, DATASET, True)
                self.assertEqual(error.exception.code, "DEMO_MIXED_OWNERSHIP")
                self.assertEqual(
                    store.get(conn, tenant, "evidence", unrelated["id"]), unrelated
                )
                self.assertEqual(store.get(conn, tenant, "workspace", seed["id"]), seed)
        finally:
            tx.rollback()
            conn.close()

    def test_normal_mode_refuses_reset(self):
        with patch.object(settings, "mode", "normal"), store.engine.begin() as conn:
            with self.assertRaises(store.DomainError):
                reset_dataset(conn, DATASET, True)

    def test_reset_clears_only_synthetic_projection_and_blocks_live_calendar_dependency(
        self,
    ):
        import sqlalchemy as sa
        from migrations.schema_v3 import calendar_events

        with store.engine.connect() as conn:
            tx = conn.begin()
            try:
                identity = auth.bootstrap(
                    conn,
                    store.uid("projection") + "@example.test",
                    "projection-reset-password",
                    "Owner",
                    "Projection Reset",
                )
                tenant = identity["organization_id"]
                actor = identity["user_id"]
                milestone = store.meta(tenant, actor, "milestone")
                store.save(conn, tenant, "milestone", milestone, dataset=DATASET)
                connection = {
                    **store.meta(tenant, actor, "calendar_connection"),
                    "data_mode": "live",
                }
                store.save(conn, tenant, "calendar_connection", connection)
                conn.execute(
                    calendar_events.insert().values(
                        tenant_id=tenant,
                        connection_id=connection["id"],
                        milestone_id=milestone["id"],
                        provider_id="fixture-owned-event",
                        etag="fixture-etag",
                        projection_hash=None,
                        state="delivered",
                        provider_data={"data_mode": "synthetic_demo"},
                    )
                )
                with patch.object(settings, "mode", "demo"):
                    with self.assertRaises(store.DomainError) as error:
                        reset_dataset(conn, DATASET, True)
                    self.assertEqual(error.exception.code, "DEMO_CALENDAR_DEPENDENCY")
                    self.assertIsNotNone(
                        store.get(conn, tenant, "milestone", milestone["id"])
                    )
                    connection["data_mode"] = "synthetic_demo"
                    store.save(conn, tenant, "calendar_connection", connection)
                    reset_dataset(conn, DATASET, True)
                    self.assertIsNone(
                        store.get(conn, tenant, "milestone", milestone["id"], False)
                    )
                    self.assertEqual(
                        store.get(
                            conn, tenant, "calendar_connection", connection["id"]
                        ),
                        connection,
                    )
                    self.assertFalse(
                        conn.execute(
                            sa.select(calendar_events).where(
                                calendar_events.c.tenant_id == tenant
                            )
                        ).first()
                    )
            finally:
                tx.rollback()
