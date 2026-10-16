"""Verify the committed synthetic source inventory before seeding."""

from pathlib import Path
import hashlib, json

ROOT = Path(__file__).resolve().parents[1] / "fixtures/demo"


def verify():
    lock = json.loads((ROOT / "assets.sha256.json").read_text())
    for relative, expected in lock.items():
        path = (ROOT / relative).resolve()
        if ROOT.resolve() not in path.parents:
            raise ValueError("Fixture path escapes namespace.")
        if hashlib.sha256(path.read_bytes()).hexdigest() != expected:
            raise ValueError("Fixture asset integrity mismatch: " + relative)
    return len(lock)


if __name__ == "__main__":
    print("Verified " + str(verify()) + " synthetic fixture assets.")
