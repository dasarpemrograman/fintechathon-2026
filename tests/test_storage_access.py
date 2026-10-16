from datetime import timedelta
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest
import sqlalchemy as sa
from services.api import auth, storage
from services.api.settings import settings
from services.api.store import (
    engine,
    organizations,
    users,
    memberships,
    sessions,
    meta,
    save,
    get,
    now,
    uid,
    DomainError,
    records,
)


class StorageAccessTests(unittest.TestCase):
    def setUp(self):
        self.conn = engine.connect()
        self.tx = self.conn.begin()
        self.context = auth.bootstrap(
            self.conn,
            uid("test") + "@example.test",
            "synthetic-test-password-long",
            "Test Owner",
            "Test Organization",
        )

    def tearDown(self):
        self.tx.rollback()
        self.conn.close()

    def test_real_password_session_expiry_and_membership(self):
        user = (
            self.conn.execute(
                sa.select(users).where(users.c.id == self.context["user_id"])
            )
            .mappings()
            .one()
        )
        result = auth.login(self.conn, user["email"], "synthetic-test-password-long")
        context = auth.authenticate(self.conn, "Bearer " + result["access_token"])
        self.assertEqual(context["tenant"], self.context["organization_id"])
        self.assertEqual(context["roles"], ["owner"])
        with self.assertRaises(DomainError):
            auth.login(self.conn, user["email"], "wrong-password")
        self.conn.execute(
            sessions.update().values(expires_at=now() - timedelta(seconds=1))
        )
        with self.assertRaises(DomainError):
            auth.authenticate(self.conn, "Bearer " + result["access_token"])

    def test_demo_shortcut_disabled(self):
        mode = settings.mode
        settings.mode = "normal"
        try:
            with self.assertRaises(DomainError):
                auth.demo_login(self.conn, self.context["user_id"])
        finally:
            settings.mode = mode

    def test_tenant_lookup_and_registry_integrity(self):
        tenant = self.context["organization_id"]
        actor = self.context["user_id"]
        resource = meta(tenant, actor, "evidence")
        save(self.conn, tenant, "evidence", resource)
        self.assertEqual(get(self.conn, tenant, "evidence", resource["id"]), resource)
        with self.assertRaises(DomainError):
            get(self.conn, "another-tenant", "evidence", resource["id"])
        with self.assertRaises(DomainError):
            save(self.conn, "another-tenant", "evidence", resource)

    def test_storage_signature_path_and_integrity(self):
        with TemporaryDirectory() as directory:
            original = settings.storage
            settings.storage = Path(directory)
            try:
                content = "Synthetic 中文 invoice\nNet 30".encode()
                key = storage.store_bytes(content, "text/plain")
                self.assertEqual(storage.read_bytes(key), content)
                self.assertEqual(storage.store_bytes(content, "text/plain"), key)
                with self.assertRaises(DomainError):
                    storage.read_bytes("../../etc/passwd")
                with self.assertRaises(DomainError):
                    storage.store_bytes(b"not a pdf", "application/pdf")
                with self.assertRaises(DomainError):
                    storage.store_bytes(
                        b"x" * (settings.max_upload_bytes + 1), "text/plain"
                    )
                (settings.storage / key).write_bytes(b"corrupted")
                with self.assertRaises(DomainError):
                    storage.read_bytes(key)
            finally:
                settings.storage = original

    def test_numeric_columns_preserve_decimal_scale(self):
        tenant = self.context["organization_id"]
        row = {
            **meta(tenant, self.context["user_id"], "obligation"),
            "amount": {"amount": "123.123456789123456789", "currency": "EUR"},
        }
        save(self.conn, tenant, "obligation", row)
        amount = self.conn.execute(
            sa.select(records["obligation"].c.amount).where(
                records["obligation"].c.id == row["id"]
            )
        ).scalar_one()
        self.assertEqual(str(amount), "123.123456789123456789")
