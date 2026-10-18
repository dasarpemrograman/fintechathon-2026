"""Private, disposable normal-account setup for actual-service browser acceptance."""

import json
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from services.api import auth, store
from migrations.schema_v2 import auth_commands

request = json.load(sys.stdin)
with store.engine.begin() as conn:
    if request["action"] == "provision":
        identity = auth.bootstrap(
            conn,
            request["email"],
            request["password"],
            "Browser Owner",
            "Browser First Organization",
        )
        second = store.uid("org")
        conn.execute(
            store.organizations.insert().values(
                id=second,
                name="Browser Second Organization",
                policy={"plan": "free_sandbox", "active": True},
            )
        )
        conn.execute(
            store.memberships.insert().values(
                id=store.uid("membership"),
                organization_id=second,
                user_id=identity["user_id"],
                roles=["owner"],
            )
        )
        print(json.dumps({**identity, "second_organization_id": second}))
    elif request["action"] == "cleanup":
        for tenant in [request["organization_id"], request["second_organization_id"]]:
            for table in [
                store.commands,
                store.snapshots,
                store.references,
                store.jobs,
                store.outbox,
                store.cash,
                *store.records.values(),
                store.registry,
            ]:
                conn.execute(table.delete().where(table.c.tenant_id == tenant))
        user = request["user_id"]
        conn.execute(store.sessions.delete().where(store.sessions.c.user_id == user))
        conn.execute(
            store.memberships.delete().where(store.memberships.c.user_id == user)
        )
        conn.execute(auth_commands.delete().where(auth_commands.c.actor_id == user))
        for tenant in [request["organization_id"], request["second_organization_id"]]:
            conn.execute(
                store.organizations.delete().where(store.organizations.c.id == tenant)
            )
        conn.execute(store.users.delete().where(store.users.c.id == user))
