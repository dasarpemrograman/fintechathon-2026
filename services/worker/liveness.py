"""Private shared-volume liveness; no credentials or tenant data."""

import json, os, threading
from datetime import datetime, timezone
from services.api.settings import settings


def path():
    return settings.storage.parent / ("worker-" + settings.mode + ".json")


def pulse():
    target = path()
    target.parent.mkdir(parents=True, exist_ok=True)
    temp = target.with_suffix("." + str(os.getpid()) + ".tmp")
    temp.write_text(
        json.dumps(
            {"mode": settings.mode, "at": datetime.now(timezone.utc).isoformat()}
        )
    )
    temp.chmod(0o600)
    temp.replace(target)


def ready():
    try:
        value = json.loads(path().read_text())
        age = (
            datetime.now(timezone.utc) - datetime.fromisoformat(value["at"])
        ).total_seconds()
        return value["mode"] == settings.mode and 0 <= age < 20
    except (OSError, ValueError, KeyError, TypeError):
        return False


def start():
    pulse()

    def loop():
        while True:
            threading.Event().wait(5)
            pulse()

    threading.Thread(target=loop, name="allexport-worker-liveness", daemon=True).start()
