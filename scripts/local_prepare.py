"""Create private local credentials and start the managed local PostgreSQL container."""

from pathlib import Path
import os, secrets, subprocess, time

root = Path(__file__).resolve().parents[1]
local = root / ".local"
local.mkdir(exist_ok=True)
password = local / "db-password"
if not password.exists():
    password.write_text(secrets.token_urlsafe(32))
    password.chmod(0o600)
env = local / "runtime.env"
if not env.exists():
    env.write_text(
        "DATABASE_URL=postgresql+psycopg://fincathon:"
        + password.read_text().strip()
        + "@127.0.0.1:15432/fincathon\n"
    )
    env.chmod(0o600)
args = ["docker", "--host=unix:///var/run/docker.sock"]
name = "fincathon-postgres"
exists = (
    subprocess.run(
        args + ["container", "inspect", name], capture_output=True
    ).returncode
    == 0
)
if not exists:
    subprocess.run(
        args
        + [
            "run",
            "-d",
            "--name",
            name,
            "-p",
            "127.0.0.1:15432:5432",
            "--mount",
            f"type=bind,src={password},dst=/run/secrets/db-password,readonly",
            "--mount",
            "type=volume,src=fincathon-postgres,dst=/var/lib/postgresql/data",
            "-e",
            "POSTGRES_USER=fincathon",
            "-e",
            "POSTGRES_DB=fincathon",
            "-e",
            "POSTGRES_PASSWORD_FILE=/run/secrets/db-password",
            "postgres:17-bookworm@sha256:3645570cccdfa447589da9f57dd740faa29b30938e861289a5574b6ca6b03826",
        ],
        check=True,
        stdout=subprocess.DEVNULL,
    )
else:
    subprocess.run(args + ["start", name], check=True, stdout=subprocess.DEVNULL)
deadline = time.monotonic() + 30
while subprocess.run(
    args + ["exec", name, "pg_isready", "-U", "fincathon"], capture_output=True
).returncode:
    if time.monotonic() > deadline:
        raise SystemExit("PostgreSQL readiness timed out; inspect the container log.")
    time.sleep(0.25)
print("Local PostgreSQL ready; private settings stored under ignored .local/.")
