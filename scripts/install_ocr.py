"""Install language assets from the committed Git object allowlist."""

from pathlib import Path
import hashlib, json, subprocess, tempfile, shutil, os

ROOT = Path(__file__).resolve().parents[1]
lock = json.loads((ROOT / "fixtures/demo/ocr-assets.lock.json").read_text())
with tempfile.TemporaryDirectory(prefix="allexport-ocr-") as tmp:
    cache = Path(tmp) / "source"
    subprocess.run(
        [
            "git",
            "clone",
            "--quiet",
            "--filter=blob:none",
            "--no-checkout",
            lock["repository"],
            str(cache),
        ],
        check=True,
    )
    subprocess.run(
        ["git", "-C", str(cache), "fetch", "--quiet", "origin", lock["commit"]],
        check=True,
    )
    destination = Path(
        os.environ.get("ALLEXPORT_TESSDATA_PATH", str(ROOT / ".local/tessdata"))
    )
    destination.mkdir(parents=True, exist_ok=True)
    for name, expected in lock["git_blob_ids"].items():
        content = subprocess.check_output(
            ["git", "-C", str(cache), "show", lock["commit"] + ":" + name]
        )
        actual = hashlib.sha1(
            ("blob " + str(len(content)) + "\0").encode() + content
        ).hexdigest()
        if actual != expected:
            raise SystemExit("OCR asset integrity mismatch: " + name)
        (destination / name).write_bytes(content)
print("Verified OCR language assets installed in ignored .local/tessdata/.")
