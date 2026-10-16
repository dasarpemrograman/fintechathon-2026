"""Check generated client types against a fresh canonical generation."""

from pathlib import Path
import subprocess
from tempfile import TemporaryDirectory

root = Path(__file__).resolve().parents[1]
with TemporaryDirectory() as temp:
    output = Path(temp) / "api.d.ts"
    subprocess.run(
        [
            str(root / "node_modules/.bin/openapi-typescript"),
            str(root / "api/openapi.yaml"),
            "-o",
            str(output),
        ],
        check=True,
    )
    if output.read_bytes() != (root / "packages/contracts/api.d.ts").read_bytes():
        raise SystemExit("Generated API types are stale: run npm run types")
print("Generated contract types match.")
