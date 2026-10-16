"""Start, inspect or stop the loopback-only local runtime; files live in .local/."""

import argparse, json, os, signal, subprocess, sys, time, socket
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
LOCAL = ROOT / ".local"
STATE = LOCAL / "services.json"
parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument("command", choices=["start", "stop", "status"])
parser.add_argument("--demo", action="store_true")
args = parser.parse_args()
LOCAL.mkdir(exist_ok=True)


def process_identity(pid):
    try:
        # starttime (field 22) prevents signalling a reused PID; session/pgrp
        # must still be the process group this launcher created.
        fields = Path(f"/proc/{pid}/stat").read_text().rsplit(")", 1)[1].split()
        return {
            "start_ticks": fields[19],
            "pgrp": int(fields[2]),
            "session": int(fields[3]),
        }
    except (FileNotFoundError, PermissionError, ValueError, IndexError):
        return None


def owned(value):
    identity = process_identity(value["pid"])
    return bool(
        identity
        and value.get("identity") == identity
        and identity["pgrp"] == value["pid"]
        and identity["session"] == value["pid"]
    )


state = json.loads(STATE.read_text()) if STATE.exists() else {}
if args.command == "status":
    print(
        json.dumps(
            {
                name: {
                    "pid": value["pid"],
                    "running": owned(value),
                    "mode": value["mode"],
                }
                for name, value in state.items()
            }
        )
    )
    sys.exit()
if args.command == "stop":
    for name, value in state.items():
        if owned(value):
            os.killpg(value["pid"], signal.SIGTERM)
    STATE.unlink(missing_ok=True)
    print("Local processes stopped; database volume and uploaded files retained.")
    sys.exit()
if any(owned(v) for v in state.values()):
    raise SystemExit("Project services already running; use status or stop first.")
for port in [8000, 3000]:
    with socket.socket() as probe:
        try:
            probe.bind(("127.0.0.1", port))
        except OSError:
            raise SystemExit(
                "Loopback port "
                + str(port)
                + " is in use; stop its owning service first."
            )
subprocess.run([sys.executable, "scripts/local_prepare.py"], cwd=ROOT, check=True)
subprocess.run(
    [sys.executable, "-m", "alembic", "upgrade", "head"], cwd=ROOT, check=True
)
env = os.environ.copy()
env.update(
    APP_MODE="demo" if args.demo else "normal",
    HOSTNAME="127.0.0.1",
    PORT="3000",
    WEB_ORIGIN="http://127.0.0.1:3000",
    API_BASE_URL="http://127.0.0.1:8000",
)
if args.demo:
    subprocess.run(
        [sys.executable, "scripts/seed_demo.py"], cwd=ROOT, env=env, check=True
    )
commands = {
    "api": [
        sys.executable,
        "-m",
        "uvicorn",
        "services.api.app:app",
        "--host",
        "127.0.0.1",
        "--port",
        "8000",
    ],
    "worker": [sys.executable, "-m", "services.worker"],
    "web": ["node", "apps/web/.next/standalone/apps/web/server.js"],
}
for name, command in commands.items():
    with (LOCAL / (name + ".log")).open("ab") as log:
        p = subprocess.Popen(
            command, cwd=ROOT, env=env, stdout=log, stderr=log, start_new_session=True
        )
    state[name] = {
        "pid": p.pid,
        "mode": env["APP_MODE"],
        "identity": process_identity(p.pid),
    }
    STATE.write_text(json.dumps(state))
    STATE.chmod(0o600)
import urllib.request

for port, path in [(8000, "/health"), (3000, "/")]:
    deadline = time.monotonic() + 30
    while True:
        try:
            with urllib.request.urlopen(
                "http://127.0.0.1:" + str(port) + path, timeout=1
            ) as response:
                if response.status == 200:
                    break
        except (OSError, TimeoutError):
            pass
        if time.monotonic() > deadline:
            raise SystemExit(
                "Service readiness timed out; inspect .local/ logs and run dev.py stop."
            )
        time.sleep(0.25)
print(
    "Ready: http://127.0.0.1:3000 · mode="
    + env["APP_MODE"]
    + " · private logs in .local/."
)
