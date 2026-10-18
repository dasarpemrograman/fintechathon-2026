"""Explicit read-only live adapter probes; never substitutes for coverage acceptance."""

import json, os, sys
from pathlib import Path
from datetime import datetime, timezone

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from packages.adapters.providers import search, fx_rates
from packages.domain.model_tasks import explain
from services.api.store import DomainError, digest

checks = []


def probe(name, needed, action):
    missing = [key for key in needed if not os.environ.get(key)]
    if missing:
        checks.append(
            {"adapter": name, "status": "blocked", "missing_configuration": missing}
        )
        return
    try:
        result = action()
        # No source bodies, model text, tokens or provider error bodies in reports.
        checks.append(
            {
                "adapter": name,
                "status": "passed",
                "response_hash": digest(result),
                "retrieved_at": datetime.now(timezone.utc).isoformat(),
            }
        )
    except DomainError as error:
        entry = {"adapter": name, "status": "failed", "code": error.code}
        receipt = getattr(error, "provider_receipt", None)
        if receipt:
            entry["provider_receipt"] = {
                field: receipt.get(field)
                for field in [
                    "provider",
                    "status",
                    "fetched_at",
                    "response_hash",
                    "limitations",
                ]
            }
        checks.append(entry)
    except Exception as error:
        checks.append(
            {
                "adapter": name,
                "status": "failed",
                "exception_type": type(error).__name__,
            }
        )


probe(
    "brave",
    ["BRAVE_SEARCH_API_KEY"],
    lambda: search("site:wto.org export trade documentation", 2),
)
probe("frankfurter", [], lambda: fx_rates("USD", ["EUR"]))
probe(
    "configured-model",
    ["FINCATHON_MODEL_BASE_URL", "FINCATHON_MODEL_ID", "FINCATHON_MODEL_API_KEY"],
    lambda: explain({"completeness": "partial", "blockers": []}, [], live=True),
)
report = {
    "scope": "adapter_connectivity_only",
    "coverage_acceptance": False,
    "checks": checks,
    "calendar": "not_executed_requires_approved_test_account_and_event_lifecycle",
}
path = Path(".local/live-provider-probes.json")
path.parent.mkdir(exist_ok=True)
path.write_text(json.dumps(report, indent=2) + "\n")
path.chmod(0o600)
print(json.dumps(report, indent=2))
raise SystemExit(0 if all(c["status"] == "passed" for c in checks) else 2)
