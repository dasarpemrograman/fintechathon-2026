"""Provision a local account without committing or logging a default password."""

import argparse, getpass, sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from services.api.store import engine
from services.api.auth import bootstrap
from services.api.settings import settings
import sqlalchemy as sa

p = argparse.ArgumentParser()
p.add_argument("--email", required=True)
p.add_argument("--name", required=True)
p.add_argument("--organization", required=True)
args = p.parse_args()
if settings.demo:
    raise SystemExit("Account provisioning requires normal mode; start dev up --mode normal.")
if not sys.stdin.isatty() or not sys.stdout.isatty():
    raise SystemExit("Use an interactive terminal for the hidden password prompt. Password arguments and redirected input are unsupported.")
try:
    with engine.connect() as conn:
        from services.api.store import users
        if conn.scalar(sa.select(users.c.id).where(sa.func.lower(users.c.email) == args.email.lower())):
            raise SystemExit("Account already exists; credentials and memberships were not changed.")
    password = getpass.getpass("Local account password (12+ characters): ")
    with engine.begin() as conn:
        result = bootstrap(conn, args.email, password, args.name, args.organization)
    print("Created local account:", result["user_id"])
except sa.exc.IntegrityError:
    raise SystemExit("Account already exists or conflicts with existing data; no changes were committed.")
except sa.exc.OperationalError:
    raise SystemExit("Database unavailable. Start normal mode and run dev doctor.")
except Exception as error:
    from services.api.store import DomainError
    if isinstance(error, DomainError):
        raise SystemExit(error.reason)
    raise
