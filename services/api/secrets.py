"""Local encrypted receipt/token storage. Keys are private and never returned."""

import os
from cryptography.fernet import Fernet
from services.api.settings import ROOT


def cipher():
    path = ROOT / ".local/encryption-key"
    path.parent.mkdir(exist_ok=True)
    if not path.exists():
        try:
            fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
            with os.fdopen(fd, "wb") as handle:
                handle.write(Fernet.generate_key())
        except FileExistsError:
            pass
    return Fernet(path.read_bytes())


def request_digest(value):
    import hashlib, hmac, json

    cipher()  # Ensure the private per-installation key exists.
    key = (ROOT / ".local/encryption-key").read_bytes()
    payload = json.dumps(
        value, sort_keys=True, separators=(",", ":"), ensure_ascii=False
    ).encode()
    return hmac.new(key, b"auth-request:" + payload, hashlib.sha256).hexdigest()
