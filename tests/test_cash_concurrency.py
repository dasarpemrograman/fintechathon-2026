from concurrent.futures import ThreadPoolExecutor
from decimal import Decimal
import unittest
import sqlalchemy as sa
from services.api import store, auth
from services.api.review_handlers import execute_review


class CashConcurrencyTests(unittest.TestCase):
    def test_two_transactions_cannot_reserve_the_same_organizational_funds(self):
        with store.engine.begin() as conn:
            identity = auth.bootstrap(
                conn,
                store.uid("concurrent") + "@example.test",
                "concurrency-test-password",
                "Owner",
                "Cash Concurrency Test",
            )
            tenant = identity["organization_id"]
            actor = identity["user_id"]
            parents = []
            hash = "a" * 64
            for index in range(2):
                parent = {
                    **store.meta(tenant, actor, "deal"),
                    "revision": 1,
                    "execution_scope": "real",
                    "dataset_id": None,
                }
                store.save(conn, tenant, "deal", parent)
                parents.append(parent)
            conn.execute(
                store.cash.insert().values(
                    tenant_id=tenant,
                    currency="EUR",
                    available=Decimal("50"),
                    snapshot_hash=hash,
                )
            )
        try:

            def reserve(parent):
                try:
                    with store.engine.begin() as conn:
                        execute_review(
                            conn,
                            {
                                "tenant": tenant,
                                "actor": actor,
                                "request_id": store.uid("request"),
                            },
                            "reserveCash",
                            parent,
                            {
                                "action": "reserve",
                                "amount": {"amount": "40", "currency": "EUR"},
                                "cash_snapshot_hash": hash,
                                "reservation_id": None,
                            },
                        )
                    return "reserved"
                except store.DomainError as error:
                    return error.code

            with ThreadPoolExecutor(max_workers=2) as pool:
                results = list(pool.map(reserve, parents))
            self.assertCountEqual(results, ["reserved", "CASH_ALREADY_COMMITTED"])
            with store.engine.connect() as conn:
                self.assertEqual(
                    len(store.list_records(conn, tenant, "reservation")["items"]), 1
                )
        finally:
            with store.engine.begin() as conn:
                for table in [store.snapshots, store.references, store.cash]:
                    conn.execute(table.delete().where(table.c.tenant_id == tenant))
                for table in store.records.values():
                    conn.execute(table.delete().where(table.c.tenant_id == tenant))
                conn.execute(
                    store.registry.delete().where(store.registry.c.tenant_id == tenant)
                )
                conn.execute(
                    store.memberships.delete().where(
                        store.memberships.c.organization_id == tenant
                    )
                )
                conn.execute(
                    store.organizations.delete().where(
                        store.organizations.c.id == tenant
                    )
                )
                conn.execute(store.users.delete().where(store.users.c.id == actor))
