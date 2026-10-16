"""Provision a local account without committing or logging a default password."""

import argparse, getpass, sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from services.api.store import engine
from services.api.auth import bootstrap

p = argparse.ArgumentParser()
p.add_argument("--email", required=True)
p.add_argument("--name", required=True)
p.add_argument("--organization", required=True)
args = p.parse_args()
password = getpass.getpass("Local account password (12+ characters): ")
with engine.begin() as conn:
    result = bootstrap(conn, args.email, password, args.name, args.organization)
print("Created local account:", result["user_id"])
