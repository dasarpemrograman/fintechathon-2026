"""Run Compose with the managed proxy DNS mapping and public CA trust secret."""

import os, socket, subprocess, sys
from urllib.parse import urlsplit
from pathlib import Path

root = Path(__file__).resolve().parents[1]
env = os.environ.copy()
proxy = urlsplit(env.get("HTTPS_PROXY", ""))
if proxy.hostname != "proxy":
    raise SystemExit(
        "This override requires the managed proxy hostname; use normal Compose for another host."
    )
addresses = sorted(
    {
        r[4][0]
        for r in socket.getaddrinfo(
            proxy.hostname,
            proxy.port or 8080,
            family=socket.AF_INET,
            type=socket.SOCK_STREAM,
        )
    }
)
if not addresses:
    raise SystemExit("Managed proxy address could not be resolved.")
env["FINCATHON_PROXY_IP"] = addresses[0]
env["DOCKER_CONFIG"] = str(root / ".local/docker-client")
Path(env["DOCKER_CONFIG"]).mkdir(parents=True, exist_ok=True)
command = [
    "docker",
    "--host=unix:///var/run/docker.sock",
    "compose",
    "-f",
    "compose.yaml",
    "-f",
    "compose.cloud.yaml",
]
if "--demo" in sys.argv:
    command += ["-f", "compose.demo.yaml"]
    sys.argv.remove("--demo")
raise SystemExit(subprocess.call(command + sys.argv[1:], cwd=root, env=env))
